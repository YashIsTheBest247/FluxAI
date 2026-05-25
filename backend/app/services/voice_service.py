"""Voice synthesis service.

Provider chain (tried in order):
  1. Microsoft Edge Neural TTS  — free, no key, high quality, the default
  2. Kokoro TTS (local)         — only if installed + KOKORO_VOICE set
  3. Silent MP3 fallback        — always succeeds, lets the pipeline finish

All paths write `.mp3` so downstream concat (podcast) and MoviePy audio mixing
(video) stay format-consistent.
"""
import asyncio
import logging
import math
import subprocess
from pathlib import Path
from typing import List, Tuple

from ..config import settings
from ..models.schemas import Scene

logger = logging.getLogger(__name__)

SAMPLE_RATE = 24000


def _estimate_duration(text: str, wpm: int = 160) -> float:
    words = max(1, len(text.split()))
    return max(1.5, (words / wpm) * 60.0)


def _ffmpeg_bin() -> str:
    """Lazily resolve the ffmpeg binary (apt-installed on Render, bundled elsewhere)."""
    from . import assembly_service
    return assembly_service._ensure_ffmpeg()


def _silent_mp3(out: Path, seconds: float) -> Tuple[Path, float]:
    """Generate a silent MP3 of the given duration via ffmpeg's lavfi.
    Used when no real TTS provider is available — keeps timing intact so
    subtitles still sync, but the user hears nothing.
    """
    out_mp3 = out.with_suffix(".mp3")
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            _ffmpeg_bin(), "-y",
            "-f", "lavfi", "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono",
            "-t", f"{seconds:.3f}",
            "-c:a", "libmp3lame", "-b:a", "64k",
            str(out_mp3),
        ],
        check=True,
        capture_output=True,
    )
    return out_mp3, seconds


async def _edge_tts_synthesize(text: str, out: Path) -> Tuple[Path, float]:
    """Microsoft Edge Neural TTS — free, no key, high quality.

    Streams audio bytes + WordBoundary events from Microsoft's TTS WebSocket
    endpoint (the same one Edge browser uses). We track the latest word boundary
    to get an accurate end-of-audio timestamp without re-probing the file.
    """
    import edge_tts

    out_mp3 = out.with_suffix(".mp3")
    out_mp3.parent.mkdir(parents=True, exist_ok=True)

    voice = settings.edge_tts_voice or "en-US-AriaNeural"
    communicate = edge_tts.Communicate(text, voice)

    # WordBoundary offsets are in 100-ns ticks (Windows FILETIME units).
    end_ticks = 0
    with open(out_mp3, "wb") as f:
        async for chunk in communicate.stream():
            ctype = chunk.get("type")
            if ctype == "audio":
                f.write(chunk["data"])
            elif ctype == "WordBoundary":
                end_ticks = max(end_ticks, chunk["offset"] + chunk["duration"])

    if out_mp3.stat().st_size < 200:
        raise RuntimeError(f"edge-tts wrote a near-empty file ({out_mp3.stat().st_size} bytes)")

    duration = end_ticks / 10_000_000.0  # ticks -> seconds
    if duration <= 0.1:
        # WordBoundary events didn't fire — probe the file as a fallback.
        duration = _probe_audio_duration(out_mp3)
    return out_mp3, duration


def _probe_audio_duration(path: Path) -> float:
    try:
        out = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            timeout=10,
        ).decode().strip()
        return float(out)
    except Exception as e:
        logger.warning("voice_service: ffprobe duration failed for %s: %s", path, e)
        return _estimate_duration("a" * 100)


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

    # Kokoro outputs 24kHz float32; write as MP3 via ffmpeg to match other paths.
    import soundfile as sf  # type: ignore
    wav_tmp = out.with_suffix(".tmp.wav")
    out_mp3 = out.with_suffix(".mp3")
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    sf.write(wav_tmp, audio, SAMPLE_RATE)
    try:
        subprocess.run(
            [
                _ffmpeg_bin(), "-y", "-i", str(wav_tmp),
                "-c:a", "libmp3lame", "-b:a", "96k",
                str(out_mp3),
            ],
            check=True,
            capture_output=True,
        )
    finally:
        wav_tmp.unlink(missing_ok=True)
    return out_mp3, len(audio) / SAMPLE_RATE


async def synthesize_scene(text: str, out: Path, fallback_seconds: float) -> Tuple[Path, float]:
    if settings.use_mock:
        return _silent_mp3(out, max(fallback_seconds, _estimate_duration(text)))

    # 1. Edge Neural TTS — free, high quality, the default.
    try:
        return await _edge_tts_synthesize(text, out)
    except Exception as e:
        logger.warning("voice_service: edge-tts failed (%s), trying Kokoro", e)

    # 2. Kokoro — only if the operator installed it.
    if settings.kokoro_voice:
        try:
            return await _kokoro_synthesize(text, out)
        except Exception as e:
            logger.warning("voice_service: Kokoro unavailable (%s), using silent fallback", e)

    # 3. Silent placeholder — keeps timing intact so subtitles still sync.
    return _silent_mp3(out, max(fallback_seconds, _estimate_duration(text)))


async def synthesize_scenes(scenes: List[Scene], out_dir: Path, on_progress=None) -> List[Tuple[Path, float]]:
    """Synthesise narration for all scenes in parallel. edge-tts is network-bound,
    so we can run more concurrently than CPU-bound Kokoro — but the upstream
    WebSocket throttles aggressive bursts. 4 is a tested-stable concurrency.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(scenes)
    done = 0
    sem = asyncio.Semaphore(4)
    lock = asyncio.Lock()

    async def one(i: int, scene: Scene) -> Tuple[int, Tuple[Path, float]]:
        nonlocal done
        async with sem:
            res = await synthesize_scene(
                scene.narration,
                out_dir / f"scene_{i:02d}.mp3",
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
