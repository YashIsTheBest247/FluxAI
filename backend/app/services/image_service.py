"""Image generation service.

Supports two providers:
  * "openai"  — DALL-E 3 (paid)
  * "gemini"  — Pollinations.ai (free, no key needed)

Falls back to a deterministic gradient placeholder when no provider succeeds.
"""
import asyncio
import base64
import hashlib
import logging
import urllib.parse
from pathlib import Path
from typing import List

import httpx
from PIL import Image, ImageDraw, ImageFilter

from ..config import settings
from ..models.schemas import Scene

logger = logging.getLogger(__name__)


def _placeholder_image(prompt: str, out: Path) -> Path:
    seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
    # Pick two cinematic colors from a palette deterministically
    palettes = [
        ((220, 38, 38), (15, 23, 42)),    # red -> slate
        ((59, 130, 246), (15, 23, 42)),   # blue -> slate
        ((168, 85, 247), (15, 23, 42)),   # purple
        ((16, 185, 129), (15, 23, 42)),   # emerald
        ((234, 179, 8), (15, 23, 42)),    # amber
        ((236, 72, 153), (15, 23, 42)),   # pink
    ]
    a, b = palettes[seed % len(palettes)]
    w, h = 1024, 1024
    img = Image.new("RGB", (w, h), b)
    draw = ImageDraw.Draw(img)
    # vertical gradient
    for y in range(h):
        t = y / h
        r = int(b[0] * (1 - t) + a[0] * t * 0.4)
        g = int(b[1] * (1 - t) + a[1] * t * 0.4)
        bl = int(b[2] * (1 - t) + a[2] * t * 0.4)
        draw.line([(0, y), (w, y)], fill=(r, g, bl))
    # noise circles
    rng = seed
    for _ in range(80):
        rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
        cx = rng % w
        rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
        cy = rng % h
        rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
        rad = 40 + (rng % 200)
        rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
        alpha = 8 + (rng % 30)
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=(a[0], a[1], a[2], alpha))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    img = img.filter(ImageFilter.GaussianBlur(radius=2))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, format="PNG", quality=92)
    return out


async def _download(url: str, dest: Path) -> Path:
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.get(url)
        r.raise_for_status()
        dest.write_bytes(r.content)
    return dest


async def _openai_image(prompt: str, out: Path) -> Path:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.images.generate(
        model=settings.image_model,
        prompt=prompt,
        size=settings.image_size,
        quality="standard",
        n=1,
    )
    item = resp.data[0]
    if getattr(item, "url", None):
        return await _download(item.url, out)
    if getattr(item, "b64_json", None):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(base64.b64decode(item.b64_json))
        return out
    raise RuntimeError("DALL-E returned neither url nor b64_json")


def _looks_like_image(data: bytes) -> bool:
    """Magic-byte sniff for JPEG / PNG / WEBP / GIF. Cheap, no PIL involvement."""
    return (
        data.startswith(b"\xff\xd8\xff")            # JPEG
        or data.startswith(b"\x89PNG\r\n\x1a\n")    # PNG
        or (data[:4] == b"RIFF" and data[8:12] == b"WEBP")
        or data.startswith(b"GIF87a") or data.startswith(b"GIF89a")
    )


async def _pollinations_image(prompt: str, out: Path) -> Path:
    """Pollinations.ai — no auth required. GET an image URL and download the bytes.

    Pollinations sometimes returns a 200 OK with an HTML error page or empty body
    when under load. We validate the response is an actual image (magic bytes +
    PIL decode round-trip) before accepting it.
    """
    encoded = urllib.parse.quote(prompt, safe="")
    seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16) % 1_000_000
    # Square 768 — Pollinations is faster at smaller sizes; MoviePy crops to 16:9.
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=768&height=768&model={settings.pollinations_model}"
        f"&seed={seed}&nologo=true&nofeed=true"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.content
        ctype = r.headers.get("content-type", "")
        if not data or len(data) < 1000:
            raise RuntimeError(f"Pollinations returned tiny payload ({len(data)} bytes, type={ctype!r})")
        if not _looks_like_image(data):
            preview = data[:80].decode("utf-8", errors="replace")
            raise RuntimeError(f"Pollinations response is not an image (type={ctype!r}, head={preview!r})")
        out.write_bytes(data)

    # Round-trip through PIL to confirm the file is decodable. Catches truncated
    # downloads, mid-stream corruption, and exotic codecs MoviePy can't handle.
    try:
        from PIL import Image
        with Image.open(out) as im:
            im.verify()
    except Exception as e:
        out.unlink(missing_ok=True)
        raise RuntimeError(f"Pollinations bytes failed PIL verify: {e}")
    return out


async def generate_image(prompt: str, out: Path) -> Path:
    if settings.use_mock:
        return _placeholder_image(prompt, out)

    provider = settings.provider_normalized
    # One retry on failure — Pollinations is flaky under load; second attempt
    # almost always succeeds because the LB has moved to a healthier worker.
    for attempt in (1, 2):
        try:
            if provider == "gemini":
                return await _pollinations_image(prompt, out)
            return await _openai_image(prompt, out)
        except Exception as e:
            logger.warning(
                "image_service: %s attempt %d failed (%s)%s",
                provider, attempt, e, "; retrying" if attempt == 1 else "; falling back to placeholder",
            )
            if attempt == 1:
                await asyncio.sleep(1.0)
    return _placeholder_image(prompt, out)


async def generate_images(scenes: List[Scene], out_dir: Path, on_progress=None) -> List[Path]:
    """Generate all scene images concurrently. Concurrency is capped at 3 — much
    higher and Pollinations starts dropping requests on the floor (their LB
    rate-limits per-IP burst). 3 is the sweet spot: fast enough to keep total
    image time near max(individual_time), reliable enough that every scene lands.
    """
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
