"""Podcast assembly. Concatenates narrated scenes into one MP3 and produces
a static-cover MP4 (cover image + same audio) so the result can still be
played in the browser and uploaded to YouTube.
"""
import logging
import subprocess
from pathlib import Path
from typing import List, Tuple

from . import assembly_service  # _ensure_ffmpeg, _ensure_decodable, VIDEO_W/H
from ..models.schemas import Scene

logger = logging.getLogger(__name__)


def _concat_audio_to_mp3(audio_paths: List[Path], out_mp3: Path) -> Path:
    """Concat WAV/AAC inputs into one MP3 via ffmpeg's concat demuxer."""
    ffmpeg = assembly_service._ensure_ffmpeg()
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    listfile = out_mp3.with_suffix(".concat.txt")
    listfile.write_text(
        "\n".join(f"file '{p.as_posix()}'" for p in audio_paths),
        encoding="utf-8",
    )
    try:
        subprocess.run(
            [
                ffmpeg, "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(listfile),
                "-codec:a", "libmp3lame", "-b:a", "128k",
                str(out_mp3),
            ],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg mp3 concat failed: {e.stderr.decode('utf-8', errors='replace')[:400]}")
    finally:
        listfile.unlink(missing_ok=True)
    return out_mp3


def _static_cover_mp4(cover_image: Path, audio_mp3: Path, out_mp4: Path, srt_path: Path | None = None) -> Path:
    """Burn a single still image + the MP3 into an MP4 — required for YouTube.
    Audio length drives video length; -shortest stops at audio end.
    """
    ffmpeg = assembly_service._ensure_ffmpeg()
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    safe_cover = assembly_service._ensure_decodable(cover_image)

    # Pad/scale cover to 1280x720 so encoders accept it.
    vf = (
        f"scale={assembly_service.VIDEO_W}:{assembly_service.VIDEO_H}:"
        "force_original_aspect_ratio=decrease,"
        f"pad={assembly_service.VIDEO_W}:{assembly_service.VIDEO_H}:(ow-iw)/2:(oh-ih)/2:color=black"
    )

    cmd = [
        ffmpeg, "-y",
        "-loop", "1", "-i", str(safe_cover),
        "-i", str(audio_mp3),
        "-vf", vf,
        "-c:v", "libx264", "-tune", "stillimage", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        str(out_mp4),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg static-cover mux failed: {e.stderr.decode('utf-8', errors='replace')[:400]}")
    return out_mp4


def assemble_podcast(
    title: str,
    scenes: List[Scene],
    cover_image: Path,
    audio_results: List[Tuple[Path, float]],
    srt_path: Path,
    out_mp3: Path,
    out_mp4: Path,
) -> Tuple[Path, Path]:
    """Returns (mp3_path, mp4_path). The MP4 is a still-image YouTube-friendly
    rendering of the same audio.
    """
    audio_paths = [p for p, _ in audio_results]
    _concat_audio_to_mp3(audio_paths, out_mp3)
    _static_cover_mp4(cover_image, out_mp3, out_mp4, srt_path=srt_path)
    return out_mp3, out_mp4
