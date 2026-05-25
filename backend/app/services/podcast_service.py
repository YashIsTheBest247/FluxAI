"""Podcast assembly. Concatenates narrated scenes into one MP3 and produces
a static-cover MP4 (cover image + same audio + subtitles) so the result plays
in the browser and uploads to YouTube cleanly.

Subtitle path is platform-aware:
  * Debian/Linux ffmpeg (Render): libass is compiled in → use ffmpeg's
    `subtitles=` filter, which is fast and renders ASS-styled captions.
  * Windows ffmpeg (imageio-ffmpeg bundle): libass is usually absent →
    fall through to MoviePy + PIL text clips (the same path the video
    pipeline uses), which works everywhere but is slower.
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
    # Paths in the concat listfile are resolved RELATIVE TO the listfile's
    # directory, not cwd — so we always write absolute paths. POSIX-style
    # slashes work on Windows too and avoid backslash-escaping inside the quotes.
    listfile.write_text(
        "\n".join(f"file '{p.resolve().as_posix()}'" for p in audio_paths),
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
        err = e.stderr.decode("utf-8", errors="replace") if e.stderr else "(no stderr)"
        tail = err.strip().split("\n")[-12:]
        raise RuntimeError("ffmpeg mp3 concat failed:\n" + "\n".join(tail))
    finally:
        listfile.unlink(missing_ok=True)
    return out_mp3


# ---------------------------------------------------------------------------
# libass availability probe
# ---------------------------------------------------------------------------

_LIBASS_OK: bool | None = None


def _ffmpeg_has_subtitles_filter() -> bool:
    """Probe whether this ffmpeg build supports the `subtitles=` filter.
    Cached per-process; safe to call from any thread."""
    global _LIBASS_OK
    if _LIBASS_OK is not None:
        return _LIBASS_OK
    try:
        ffmpeg = assembly_service._ensure_ffmpeg()
        out = subprocess.check_output([ffmpeg, "-hide_banner", "-filters"], stderr=subprocess.STDOUT, timeout=8)
        text = out.decode("utf-8", errors="replace")
        # The filters list has lines like " ... subtitles            VS->V       ..."
        # Match "subtitles " surrounded by whitespace to avoid hitting "subtitles" inside descriptions.
        _LIBASS_OK = any(
            line.split() and line.split()[1] == "subtitles"
            for line in text.splitlines()
            if "subtitles" in line
        )
    except Exception as e:
        logger.warning("podcast_service: ffmpeg filter probe failed (%s) — assuming no libass", e)
        _LIBASS_OK = False
    logger.info("podcast_service: ffmpeg subtitles filter available = %s", _LIBASS_OK)
    return _LIBASS_OK


def _escape_subtitles_path(path: Path) -> str:
    """ffmpeg's `subtitles=` filter parses its argument as a filter string and
    treats `:` and `\\` as syntax — Windows drive letters and any backslashes
    must be escaped.
    """
    s = path.as_posix()
    s = s.replace("\\", "\\\\").replace(":", r"\:").replace("'", r"\'")
    return s


# ---------------------------------------------------------------------------
# Output paths: fast (ffmpeg + libass) and portable (MoviePy + PIL)
# ---------------------------------------------------------------------------


def _ffmpeg_cover_mp4(
    cover_image: Path,
    audio_mp3: Path,
    out_mp4: Path,
    srt_path: Path | None = None,
) -> Path:
    """Fast path: pure ffmpeg. Burns subtitles via libass when an SRT is given."""
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
        # Don't pin Fontname: libass aborts on Windows when it can't find a
        # specific font file (DejaVu Sans isn't installed there by default).
        # Letting libass pick its own default falls back gracefully on every
        # platform — the Outline/Border styling does the legibility work.
        style = (
            "Fontsize=22,"
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
        # ffmpeg dumps its build banner FIRST and the actual error LAST — show the tail.
        err = e.stderr.decode("utf-8", errors="replace") if e.stderr else "(no stderr)"
        tail = err.strip().split("\n")[-12:]  # last 12 lines is usually enough
        raise RuntimeError("ffmpeg static-cover mux failed:\n" + "\n".join(tail))
    return out_mp4


def _moviepy_cover_mp4(
    cover_image: Path,
    audio_mp3: Path,
    out_mp4: Path,
    srt_path: Path | None = None,
) -> Path:
    """Portable path: MoviePy + PIL text clips. Used when ffmpeg lacks libass
    (typical on Windows with the imageio-ffmpeg bundled binary). Slower than
    raw ffmpeg but renders subtitles correctly anywhere PIL has a font.
    """
    # Reuse the patched MoviePy import from assembly_service (PIL.ANTIALIAS shim).
    _ = assembly_service.VIDEO_W
    from moviepy.editor import AudioFileClip, CompositeVideoClip, ImageClip

    safe_cover = assembly_service._ensure_decodable(cover_image)
    audio = AudioFileClip(str(audio_mp3))
    duration = audio.duration

    cover = (
        ImageClip(str(safe_cover))
        .set_duration(duration)
        .resize(newsize=(assembly_service.VIDEO_W, assembly_service.VIDEO_H))
    )

    clips = [cover]
    if srt_path and srt_path.exists():
        # _subtitle_clips already handles wrapping + stroke + bottom-safe position.
        clips.extend(assembly_service._subtitle_clips(srt_path))

    final = CompositeVideoClip(
        clips, size=(assembly_service.VIDEO_W, assembly_service.VIDEO_H)
    ).set_audio(audio)

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(
        str(out_mp4),
        fps=12,  # static cover: 12fps is plenty and 2× faster than 24
        codec="libx264",
        audio_codec="aac",
        bitrate="1500k",
        audio_bitrate="128k",
        preset="ultrafast",
        threads=2,
        verbose=False,
        logger=None,  # MoviePy's bar logger flickers in dev terminals
        temp_audiofile=str(out_mp4.with_suffix(".audio.m4a")),
        remove_temp=True,
        ffmpeg_params=["-tune", "stillimage", "-movflags", "+faststart"],
    )
    return out_mp4


def _static_cover_mp4(
    cover_image: Path,
    audio_mp3: Path,
    out_mp4: Path,
    srt_path: Path | None = None,
) -> Path:
    """Pick the appropriate render strategy based on what this ffmpeg supports."""
    if srt_path and srt_path.exists() and not _ffmpeg_has_subtitles_filter():
        logger.info("podcast_service: no libass — rendering subtitles via MoviePy")
        return _moviepy_cover_mp4(cover_image, audio_mp3, out_mp4, srt_path)
    try:
        return _ffmpeg_cover_mp4(cover_image, audio_mp3, out_mp4, srt_path)
    except RuntimeError as e:
        # libass detection said yes but the actual filter pass still failed.
        # Fall through to MoviePy so the user at least gets subs.
        if srt_path and "subtitles" in str(e).lower():
            logger.warning("podcast_service: ffmpeg subtitle burn failed (%s) — retrying via MoviePy", e)
            return _moviepy_cover_mp4(cover_image, audio_mp3, out_mp4, srt_path)
        raise


def assemble_podcast(
    title: str,
    scenes: List[Scene],
    cover_image: Path,
    audio_results: List[Tuple[Path, float]],
    srt_path: Path,
    out_mp3: Path,
    out_mp4: Path,
) -> Tuple[Path, Path]:
    """Returns (mp3_path, mp4_path). The MP4 has the audio + subtitles overlaid
    on the cover (burned via libass or MoviePy depending on host); the MP3 stays
    as the lightweight download for podcast platforms.
    """
    audio_paths = [p for p, _ in audio_results]
    _concat_audio_to_mp3(audio_paths, out_mp3)
    _static_cover_mp4(cover_image, out_mp3, out_mp4, srt_path=srt_path)
    return out_mp3, out_mp4
