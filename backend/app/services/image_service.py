"""Image generation service.

Provider chain (tried in order, with provider-down memoisation):
  1. OpenAI gpt-image-1            — paid, requires OPENAI_API_KEY
  2. Pollinations.ai               — free, no key; rotates through model candidates
  3. Gemini 2.5 Flash Image        — paid fallback via GEMINI_API_KEY
  4. Poster-style placeholder      — always succeeds

Provider-down memoisation
-------------------------
Once a provider returns a structural failure (402 Payment Required, 429 quota,
400 invalid model), we mark it down for the rest of this process. This prevents
wasting time and quota on a provider that is clearly closed for the session —
without it, every scene would re-trigger the same 3-4 outbound HTTP failures.
"""
import asyncio
import base64
import hashlib
import logging
import math
import urllib.parse
from pathlib import Path
from typing import Awaitable, Callable, List

import httpx
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..config import settings
from ..models.schemas import Scene

logger = logging.getLogger(__name__)

# Pollinations models that have historically worked without auth. The catalogue
# shifts often; we rotate through these in order and skip any that 4xx out.
POLLINATIONS_FREE_MODELS = ["sana", "turbo"]

# Per-process provider-down memo. When a provider is in this set, the
# corresponding _<provider>_image function raises immediately without making
# any network calls. Cleared only on process restart — intentional, because
# 402/429 typically don't recover within a single render session.
_PROVIDER_DOWN: set[str] = set()


def _mark_down(name: str, reason: str) -> None:
    if name not in _PROVIDER_DOWN:
        logger.warning("image_service: marking %s DOWN for this run (%s)", name, reason)
        _PROVIDER_DOWN.add(name)


# ---------------------------------------------------------------------------
# Poster-style placeholder — used when every external provider has failed.
# Renders a cinematic gradient + film grain + the scene's prompt as a poster
# headline, so the resulting video looks intentional rather than broken.
# ---------------------------------------------------------------------------

_PLACEHOLDER_PALETTES = [
    ((220, 38,  38),  (15, 23, 42)),    # red / slate
    ((59,  130, 246), (15, 23, 42)),    # azure / slate
    ((168, 85,  247), (20, 14, 40)),    # violet / deep
    ((16,  185, 129), (8,  22, 28)),    # emerald / deep
    ((234, 179, 8),   (28, 18, 8)),     # amber / espresso
    ((236, 72,  153), (28, 10, 22)),    # rose / wine
    ((34,  211, 238), (8,  20, 30)),    # cyan / deep
    ((251, 113, 133), (24, 10, 18)),    # coral / wine
]


def _find_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Return a usable TrueType font for poster typography."""
    bold_candidates = [
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\impact.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ]
    regular_candidates = [
        r"C:\Windows\Fonts\Arial.ttf",
        r"C:\Windows\Fonts\consola.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in (bold_candidates if bold else regular_candidates):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    out: List[str] = []
    for paragraph in text.splitlines() or [text]:
        words = paragraph.split()
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            bbox = font.getbbox(test)
            if (bbox[2] - bbox[0]) > max_width and cur:
                out.append(cur)
                cur = w
            else:
                cur = test
        if cur:
            out.append(cur)
    return out


def _extract_headline(prompt: str) -> tuple[str, str]:
    """Pull a short headline from the image prompt. The rest becomes the caption.

    Strips boilerplate cinematic adjectives ("a wide shot of…") so the headline
    lands on the actual subject of the scene.
    """
    text = prompt.strip()
    lowered = text.lower()
    for prefix in (
        "a wide shot of ", "a cinematic shot of ", "cinematic shot of ",
        "a close-up of ", "a close up of ", "close-up of ",
        "wide shot, ", "wide cinematic shot, ", "macro photography, ",
        "shot of ", "view of ",
    ):
        if lowered.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    head = text.split(",")[0].split(".")[0].strip()
    words = head.split()
    headline = " ".join(words[:7])
    return headline, text


def _placeholder_image(prompt: str, out: Path) -> Path:
    """Generate a poster-style scene card.

    Deterministic from the prompt — same prompt always yields the same image,
    so re-runs of the same script produce stable output.
    """
    seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)

    accent, deep = _PLACEHOLDER_PALETTES[seed % len(_PLACEHOLDER_PALETTES)]
    W, H = 1024, 1024

    # Radial-ish gradient with an off-center hot spot — cinematic without being noisy.
    cx = W * (0.20 + float(rng.random()) * 0.45)
    cy = H * (0.18 + float(rng.random()) * 0.45)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / math.hypot(W, H)
    t = np.clip(1.0 - d * 1.35, 0, 1) ** 1.4

    accent_arr = np.array(accent, dtype=np.float32)
    deep_arr = np.array(deep, dtype=np.float32)
    grad = deep_arr * (1 - t)[..., None] + accent_arr * 0.55 * t[..., None]

    # Subtle film grain so the card doesn't look flat.
    grain = (rng.random((H, W)).astype(np.float32) - 0.5) * 18.0
    grad = grad + grain[..., None]
    arr = np.clip(grad, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, mode="RGB")

    # Vignette: darken the edges slightly using a radial mask.
    edge_d = np.sqrt((xx - W / 2) ** 2 + (yy - H / 2) ** 2) / math.hypot(W / 2, H / 2)
    vignette = np.clip(edge_d * 0.55, 0, 0.55).astype(np.float32)
    arr2 = np.array(img).astype(np.float32) * (1.0 - vignette[..., None] * 0.6)
    img = Image.fromarray(np.clip(arr2, 0, 255).astype(np.uint8), mode="RGB")
    img = img.filter(ImageFilter.GaussianBlur(radius=0.6))

    draw = ImageDraw.Draw(img)

    # Editorial accent bar (matches the brand red bar pattern).
    bar_h = 6
    bar_y = int(H * 0.62)
    draw.rectangle((int(W * 0.10), bar_y, int(W * 0.32), bar_y + bar_h), fill=accent)

    # Poster headline (uppercase, heavy display type, white with black stroke).
    headline, caption = _extract_headline(prompt)
    headline_text = headline.upper()
    big = _find_font(int(W * 0.085), bold=True)
    small = _find_font(int(W * 0.022), bold=False)

    head_lines = _wrap(headline_text, big, int(W * 0.78))
    head_lines = head_lines[:3]  # never overflow vertically
    line_h = int(W * 0.095)
    head_block_top = bar_y + bar_h + int(H * 0.025)

    y = head_block_top
    for line in head_lines:
        bbox = big.getbbox(line)
        line_w = bbox[2] - bbox[0]
        x = int(W * 0.10)
        # Heavy stroke for legibility on any gradient.
        for dx in (-3, -2, 0, 2, 3):
            for dy in (-3, -2, 0, 2, 3):
                draw.text((x + dx, y + dy), line, font=big, fill=(0, 0, 0))
        draw.text((x, y), line, font=big, fill=(245, 245, 250))
        y += line_h

    # Tiny mono caption beneath the headline (full prompt, truncated).
    cap_lines = _wrap(caption, small, int(W * 0.78))[:3]
    y += int(H * 0.015)
    for line in cap_lines:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                draw.text((int(W * 0.10) + dx, y + dy), line, font=small, fill=(0, 0, 0))
        draw.text((int(W * 0.10), y), line, font=small, fill=(220, 220, 230))
        y += int(W * 0.028)

    # Corner ticks — magazine-grid feel.
    tick = int(W * 0.025)
    pad = int(W * 0.05)
    for (px, py, dx, dy) in [
        (pad, pad, 1, 1), (W - pad, pad, -1, 1),
        (pad, H - pad, 1, -1), (W - pad, H - pad, -1, -1),
    ]:
        draw.line((px, py, px + dx * tick, py), fill=(255, 255, 255), width=2)
        draw.line((px, py, px, py + dy * tick), fill=(255, 255, 255), width=2)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, format="PNG", quality=92)
    return out


# ---------------------------------------------------------------------------
# Real providers
# ---------------------------------------------------------------------------

async def _download(url: str, dest: Path) -> Path:
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.get(url)
        r.raise_for_status()
        dest.write_bytes(r.content)
    return dest


def _looks_like_image(data: bytes) -> bool:
    return (
        data.startswith(b"\xff\xd8\xff")
        or data.startswith(b"\x89PNG\r\n\x1a\n")
        or (data[:4] == b"RIFF" and data[8:12] == b"WEBP")
        or data.startswith(b"GIF87a") or data.startswith(b"GIF89a")
    )


def _verify_image_file(path: Path) -> None:
    with Image.open(path) as im:
        im.verify()


async def _openai_image(prompt: str, out: Path) -> Path:
    if "openai" in _PROVIDER_DOWN:
        raise RuntimeError("openai provider marked down for this run")
    if not settings.openai_api_key:
        _mark_down("openai", "OPENAI_API_KEY missing")
        raise RuntimeError("OPENAI_API_KEY not set")

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    try:
        resp = await client.images.generate(
            model=settings.image_model,
            prompt=prompt,
            size=settings.image_size,
            n=1,
        )
    except Exception as e:
        # 400 invalid model / 401 auth / 403 — won't recover this session.
        msg = str(e).lower()
        if any(s in msg for s in ("does not exist", "invalid_value", "401", "403", "model_not_found")):
            _mark_down("openai", f"non-retryable: {e}")
        raise

    item = resp.data[0]
    if getattr(item, "url", None):
        return await _download(item.url, out)
    if getattr(item, "b64_json", None):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(base64.b64decode(item.b64_json))
        return out
    raise RuntimeError("OpenAI returned neither url nor b64_json")


async def _pollinations_try_one(prompt: str, out: Path, model: str) -> Path:
    encoded = urllib.parse.quote(prompt, safe="")
    seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16) % 1_000_000
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=768&height=768&model={model}"
        f"&seed={seed}&nologo=true&nofeed=true"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.content
        ctype = r.headers.get("content-type", "")
        if not data or len(data) < 1000:
            raise RuntimeError(f"tiny payload ({len(data)} bytes, type={ctype!r})")
        if not _looks_like_image(data):
            preview = data[:80].decode("utf-8", errors="replace")
            raise RuntimeError(f"non-image response (type={ctype!r}, head={preview!r})")
        out.write_bytes(data)
    try:
        _verify_image_file(out)
    except Exception as e:
        out.unlink(missing_ok=True)
        raise RuntimeError(f"bytes failed PIL verify: {e}")
    return out


async def _pollinations_image(prompt: str, out: Path) -> Path:
    """Try the configured model first, then known free fallbacks.

    If every candidate returns 401/402/403 the entire anonymous tier is
    closed for us — mark Pollinations down so we stop wasting requests.
    """
    if "pollinations" in _PROVIDER_DOWN:
        raise RuntimeError("pollinations provider marked down for this run")

    candidates: List[str] = []
    for m in [settings.pollinations_model, *POLLINATIONS_FREE_MODELS]:
        m = (m or "").strip()
        if m and m not in candidates:
            candidates.append(m)

    all_gated = True
    last_err: Exception | None = None
    for model in candidates:
        try:
            return await _pollinations_try_one(prompt, out, model)
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            if code in (401, 402, 403, 404, 429):
                logger.info("pollinations: model %r gated (%s) — trying next", model, code)
                last_err = e
                continue
            all_gated = False
            raise
        except Exception as e:
            all_gated = False
            last_err = e
            logger.info("pollinations: model %r failed (%s) — trying next", model, e)
            continue

    if all_gated:
        _mark_down("pollinations", f"every model returned 4xx ({last_err})")
    raise RuntimeError(f"all Pollinations models exhausted: {last_err}")


async def _gemini_image(prompt: str, out: Path) -> Path:
    if "gemini" in _PROVIDER_DOWN:
        raise RuntimeError("gemini provider marked down for this run")
    if not settings.gemini_api_key:
        _mark_down("gemini", "GEMINI_API_KEY missing")
        raise RuntimeError("GEMINI_API_KEY not set")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_image_model}:generateContent?key={settings.gemini_api_key}"
    )
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }
    async with httpx.AsyncClient(timeout=90) as client:
        try:
            r = await client.post(url, json=body)
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            # 429 = daily quota; 401/403 = bad key — won't recover this session.
            if code in (401, 403, 429):
                _mark_down("gemini", f"{code} from generateContent")
            raise
        data = r.json()

    for cand in data.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(base64.b64decode(inline["data"]))
                _verify_image_file(out)
                return out
    raise RuntimeError(f"Gemini image: no inlineData in response (keys={list(data.keys())})")


def _provider_chain() -> List[Callable[[str, Path], Awaitable[Path]]]:
    primary = settings.provider_normalized
    if primary == "openai":
        return [_openai_image, _pollinations_image, _gemini_image]
    return [_pollinations_image, _gemini_image, _openai_image]


async def generate_image(prompt: str, out: Path) -> Path:
    if settings.use_mock:
        return _placeholder_image(prompt, out)

    errors: List[str] = []
    for fn in _provider_chain():
        try:
            return await fn(prompt, out)
        except Exception as e:
            errors.append(f"{fn.__name__}={e}")
            # Only log full failures the first time per provider — once it's
            # in _PROVIDER_DOWN, the raise is instantaneous and we don't need
            # to repeat the WARNING for every scene.
            level = logging.INFO if any(p in _PROVIDER_DOWN for p in ("openai", "pollinations", "gemini")) else logging.WARNING
            logger.log(level, "image_service: %s failed (%s) — trying next provider", fn.__name__, e)

    logger.info("image_service: all providers exhausted — using poster placeholder")
    return _placeholder_image(prompt, out)


async def generate_images(scenes: List[Scene], out_dir: Path, on_progress=None) -> List[Path]:
    """Generate all scene images concurrently. Concurrency is capped at 3."""
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(scenes)
    done = 0
    lock = asyncio.Lock()
    sem = asyncio.Semaphore(3)

    async def one(i: int, scene: Scene) -> tuple[int, Path]:
        nonlocal done
        out = out_dir / f"scene_{i:02d}.png"
        async with sem:
            try:
                p = await generate_image(scene.image_prompt, out)
            except Exception as e:
                logger.exception("generate_images: scene %d crashed (%s)", i, e)
                p = _placeholder_image(scene.image_prompt, out)
        async with lock:
            done += 1
            if on_progress:
                await on_progress(done / total)
        return i, p

    results = await asyncio.gather(*[one(i, s) for i, s in enumerate(scenes)])
    results.sort(key=lambda x: x[0])
    return [p for _, p in results]
