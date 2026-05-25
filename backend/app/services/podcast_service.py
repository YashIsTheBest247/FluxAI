"""Podcast assembly. Concatenates narrated scenes into one MP3 and produces
a static-cover MP4 (cover image + same audio + burned-in subtitles) so the
result plays in the browser and uploads to YouTube cleanly.
"""
import logging
import subprocess
from pathlib import Path
from typing import List, Tuple

from . import assembly_service  # _ensure_ffmpeg, _ensure_decodable, VIDEO_W/H
from ..models.schemas import Scene

logger = logging.getLogger(__name__)


def _concat_audio_to_mp3(audio_paths: List[Path], out_mp3: Path) -> Path:
    """Concat the per-scene MP3s into one MP3 via ffmpeg's concat demuxer.
    All inputs are already MP3 at the same sample rate (voice_service writes
    them this way), so re-encoding is cheap and avoids codec-mismatch issues.
    """
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
                "-c:a", "libmp3lame", "-b:a", "128k",
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


def _escape_subtitles_path(path: Path) -> str:
    """ffmpeg's `subtitles=` filter parses its argument as a filter string and
    treats `:` and `\\` as syntax — Windows drive letters and any backslashes
    must be escaped. POSIX paths only need single-quote escaping.
    """
    s = path.as_posix()
    s = s.replace("\\", "\\\\").replace(":", r"\:").replace("'", r"\'")
    return s


def _static_cover_mp4(
    cover_image: Path,
    audio_mp3: Path,
    out_mp4: Path,
    srt_path: Path | None = None,
) -> Path:
    """Mux a single still image + the MP3 into an MP4. If `srt_path` is
    provided and ffmpeg has libass support (which the apt-installed binary
    on Debian does), subtitles are burned into the picture.
    """
    ffmpeg = assembly_service._ensure_ffmpeg()
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    safe_cover = assembly_service._ensure_decodable(cover_image)

    vf_parts = [
        f"scale={assembly_service.VIDEO_W}:{assembly_service.VIDEO_H}:"
        "force_original_aspect_ratio=decrease",
        f"pad={assembly_service.VIDEO_W}:{assembly_service.VIDEO_H}:"
        "(ow-iw)/2:(oh-ih)/2:color=black",
    ]
    if srt_path and srt_path.exists():
        srt_arg = _escape_subtitles_path(srt_path)
        # ASS-style force_style — Alignment=2 = bottom-center, MarginV=60 lifts
        # captions above the player chrome. Outline+BorderStyle gives the same
        # legibility-on-any-background trick MoviePy's text clips use.
        style = (
            "Fontname=DejaVu Sans,Fontsize=22,"
            "PrimaryColour=&Hffffff,OutlineColour=&H000000,BackColour=&H80000000,"
            "BorderStyle=1,Outline=2,Shadow=0,"
            "Alignment=2,MarginV=60"
        )
        vf_parts.append(f"subtitles={srt_arg}:force_style='{style}'")

    vf = ",".join(vf_parts)

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
        # Captions can fail if libass isn't compiled in. Retry once without subs
        # so the user still gets the audio+cover, then log loudly.
        err = e.stderr.decode("utf-8", errors="replace")
        if srt_path and "subtitles" in vf:
            logger.warning(
                "podcast_service: subtitle burn failed (%s) — re-encoding without subs",
                err[:200],
            )
            return _static_cover_mp4(cover_image, audio_mp3, out_mp4, srt_path=None)
        raise RuntimeError(f"ffmpeg static-cover mux failed: {err[:400]}")
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
    """Returns (mp3_path, mp4_path). The MP4 has the audio + burned subtitles
    overlaid on the cover so it can be played anywhere (browser, YouTube)
    while the MP3 stays as the lightweight download for podcast platforms.
    """
    audio_paths = [p for p, _ in audio_results]
    _concat_audio_to_mp3(audio_paths, out_mp3)
    _static_cover_mp4(cover_image, out_mp3, out_mp4, srt_path=srt_path)
    return out_mp3, out_mp4
