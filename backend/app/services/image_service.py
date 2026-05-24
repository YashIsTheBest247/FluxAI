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


async def _pollinations_image(prompt: str, out: Path) -> Path:
    """Pollinations.ai — no auth required. GET an image URL and download the bytes."""
    encoded = urllib.parse.quote(prompt, safe="")
    seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16) % 1_000_000
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1024&height=1024&model={settings.pollinations_model}"
        f"&seed={seed}&nologo=true&enhance=true&nofeed=true"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        if not r.content or len(r.content) < 1000:
            raise RuntimeError(f"Pollinations returned empty/small payload ({len(r.content)} bytes)")
        out.write_bytes(r.content)
    return out


async def generate_image(prompt: str, out: Path) -> Path:
    if settings.use_mock:
        return _placeholder_image(prompt, out)

    provider = settings.provider_normalized
    try:
        if provider == "gemini":
            return await _pollinations_image(prompt, out)
        return await _openai_image(prompt, out)
    except Exception as e:
        logger.exception("image_service: %s failed (%s), falling back to placeholder", provider, e)
    return _placeholder_image(prompt, out)


async def generate_images(scenes: List[Scene], out_dir: Path, on_progress=None) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    for i, scene in enumerate(scenes):
        p = await generate_image(scene.image_prompt, out_dir / f"scene_{i:02d}.png")
        paths.append(p)
        if on_progress:
            await on_progress((i + 1) / len(scenes))
    return paths
