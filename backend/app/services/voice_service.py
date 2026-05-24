"""Voice synthesis service. Tries Kokoro TTS, falls back to a silent track with measured length."""
import asyncio
import logging
import math
import struct
import wave
from pathlib import Path
from typing import List, Tuple

from ..config import settings
from ..models.schemas import Scene

logger = logging.getLogger(__name__)

SAMPLE_RATE = 24000


def _estimate_duration(text: str, wpm: int = 160) -> float:
    words = max(1, len(text.split()))
    return max(1.5, (words / wpm) * 60.0)


def _write_silence_wav(path: Path, seconds: float, sample_rate: int = SAMPLE_RATE) -> None:
    """Write a faint low-frequency tone so audio tracks behave normally in MoviePy."""
    n = int(sample_rate * seconds)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # Very low-amplitude pink-ish hum so codecs don't strip the track
        frames = bytearray()
        for i in range(n):
            sample = int(800 * math.sin(2 * math.pi * 60 * i / sample_rate))
            frames += struct.pack("<h", sample)
        wf.writeframes(bytes(frames))


async def _kokoro_synthesize(text: str, out: Path) -> Tuple[Path, float]:
    """Try to use a locally installed Kokoro TTS. Returns (path, duration)."""
    try:
        from kokoro import KPipeline  # type: ignore
    except Exception:
        raise RuntimeError("kokoro not installed")
    pipeline = KPipeline(lang_code="a")
    audio_chunks = []
    for _, _, audio in pipeline(text, voice=settings.kokoro_voice or "af_bella"):
        audio_chunks.append(audio)
    import numpy as np
    audio = np.concatenate(audio_chunks) if audio_chunks else np.zeros(SAMPLE_RATE, dtype="float32")
    # Save as wav (kokoro uses 24kHz)
    import soundfile as sf  # type: ignore
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(out, audio, SAMPLE_RATE)
    return out, len(audio) / SAMPLE_RATE


async def synthesize_scene(text: str, out: Path, fallback_seconds: float) -> Tuple[Path, float]:
    if not settings.use_mock and settings.kokoro_voice:
        try:
            return await _kokoro_synthesize(text, out)
        except Exception as e:
            logger.warning("voice_service: Kokoro unavailable (%s), using silent fallback", e)
    seconds = max(fallback_seconds, _estimate_duration(text))
    _write_silence_wav(out, seconds)
    return out, seconds


async def synthesize_scenes(scenes: List[Scene], out_dir: Path, on_progress=None) -> List[Tuple[Path, float]]:
    """Synthesise narration for all scenes in parallel.
    Kokoro is CPU/GPU-bound so we cap concurrency at 2 to avoid OOM."""
    import asyncio
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(scenes)
    done = 0
    sem = asyncio.Semaphore(2)
    lock = asyncio.Lock()

    async def one(i: int, scene: Scene) -> Tuple[int, Tuple[Path, float]]:
        nonlocal done
        async with sem:
            res = await synthesize_scene(
                scene.narration,
                out_dir / f"scene_{i:02d}.wav",
                fallback_seconds=scene.duration,
            )
        async with lock:
            done += 1
            if on_progress:
                await on_progress(done / total)
        return i, res

    results = await asyncio.gather(*[one(i, s) for i, s in enumerate(scenes)])
    results.sort(key=lambda x: x[0])
    return [r for _, r in results]
