"""Final MP4 assembly using MoviePy. Static scenes + crossfades, audio mix, and burned subtitles."""
import logging
from pathlib import Path
from typing import List, Tuple

# --- Compatibility shim ---------------------------------------------------
# MoviePy 1.0.3 calls PIL.Image.ANTIALIAS, which was removed in Pillow 10.
# Without this patch the Assembly stage crashes on the first resize() call.
# https://github.com/Zulko/moviepy/issues/1882
import PIL.Image
if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS  # type: ignore[attr-defined]
# -------------------------------------------------------------------------

from ..config import settings
from ..models.schemas import Scene

logger = logging.getLogger(__name__)

VIDEO_W, VIDEO_H = 1280, 720
FPS = 24  # 24fps is cinematic and ~20% less to encode than 30


def _static_scene_clip(image_path: Path, duration: float):
    """Pre-sized static ImageClip — far cheaper than per-frame Ken Burns transforms."""
    from moviepy.editor import ImageClip
    return ImageClip(str(image_path)).set_duration(duration).resize(newsize=(VIDEO_W, VIDEO_H))


def _find_font(size: int):
    """Locate a usable TrueType font across Windows/Linux/macOS. Falls back to PIL default."""
    from PIL import ImageFont
    candidates = [
        # Windows
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\Arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        # macOS
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap_text(text: str, font, max_width: int):
    """Word-wrap to fit max_width pixels; respects existing newlines."""
    out = []
    for paragraph in text.splitlines() or [text]:
        words = paragraph.split()
        if not words:
            out.append("")
            continue
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


def _text_clip_safe(text: str, fontsize: int, size=(None, None), color="white", stroke=False):
    """Render `text` to a transparent RGBA bitmap via Pillow and return a MoviePy ImageClip.

    Bypasses MoviePy's ImageMagick-dependent TextClip entirely. Always succeeds.
    """
    from PIL import Image, ImageDraw
    from moviepy.editor import ImageClip
    import numpy as np

    width = size[0] if (size and size[0]) else 1100
    font = _find_font(fontsize)
    lines = _wrap_text(text, font, max(200, width - 40))

    line_height = int(fontsize * 1.25)
    pad = max(12, fontsize // 3)
    canvas_w = max(200, width)
    canvas_h = line_height * max(1, len(lines)) + pad * 2

    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    y = pad
    for line in lines:
        bbox = font.getbbox(line)
        line_w = bbox[2] - bbox[0]
        x = (canvas_w - line_w) // 2
        if stroke:
            draw.text((x, y), line, font=font, fill=color, stroke_width=3, stroke_fill="black")
        else:
            draw.text((x, y), line, font=font, fill=color)
        y += line_height

    return ImageClip(np.array(img), transparent=True)


def _intro_outro(text: str, duration: float = 1.6):
    from moviepy.editor import ColorClip, CompositeVideoClip
    bg = ColorClip(size=(VIDEO_W, VIDEO_H), color=(8, 8, 12)).set_duration(duration)
    txt = _text_clip_safe(text, fontsize=64, size=(VIDEO_W - 200, None))
    if txt is None:
        return bg
    txt = txt.set_duration(duration).set_position("center").crossfadein(0.4).crossfadeout(0.4)
    return CompositeVideoClip([bg, txt])


def _subtitle_clips(srt_path: Path):
    import pysrt
    subs = pysrt.open(str(srt_path), encoding="utf-8")
    clips = []
    for s in subs:
        start = s.start.ordinal / 1000.0
        end = s.end.ordinal / 1000.0
        tc = _text_clip_safe(s.text, fontsize=36, size=(VIDEO_W - 160, None), stroke=True)
        if tc is None:
            continue
        tc = tc.set_start(start).set_end(end).set_position(("center", VIDEO_H - 110))
        clips.append(tc)
    return clips


def _ensure_ffmpeg() -> str:
    """Locate a usable ffmpeg binary and tell imageio/moviepy to use it.

    Search order:
      1. System PATH (`ffmpeg` command)
      2. Bundled binary that ships with `imageio-ffmpeg` (moviepy's hard dependency)

    Returns the path it picked. Raises only if both fail.
    """
    import os, shutil, subprocess

    exe = shutil.which("ffmpeg")
    if not exe:
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception as e:
            raise RuntimeError(
                f"No ffmpeg on PATH and imageio-ffmpeg fallback failed ({e}). "
                "Install ffmpeg with `winget install --id Gyan.FFmpeg` (then restart your shell), "
                "or reinstall the backend deps to fetch the bundled binary."
            )

    # Pin it so MoviePy always uses this exact binary, even if PATH changes.
    os.environ["IMAGEIO_FFMPEG_EXE"] = exe
    os.environ["FFMPEG_BINARY"] = exe

    try:
        subprocess.run([exe, "-version"], capture_output=True, timeout=5, check=True)
    except Exception as e:
        raise RuntimeError(f"ffmpeg located at {exe} but unusable: {e}")
    return exe


def assemble_video(
    title: str,
    scenes: List[Scene],
    image_paths: List[Path],
    audio_paths: List[Tuple[Path, float]],
    srt_path: Path,
    out_path: Path,
) -> Path:
    _ensure_ffmpeg()

    from moviepy.editor import (
        AudioFileClip,
        CompositeVideoClip,
        concatenate_videoclips,
        concatenate_audioclips,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)

    scene_clips = []
    audio_clips = []
    for i, (scene, img_path, (audio_path, dur)) in enumerate(zip(scenes, image_paths, audio_paths)):
        clip = _static_scene_clip(img_path, dur).crossfadein(0.3)
        scene_clips.append(clip)
        audio_clips.append(AudioFileClip(str(audio_path)).set_duration(dur))

    body = concatenate_videoclips(scene_clips, method="compose")
    body_audio = concatenate_audioclips(audio_clips).set_duration(body.duration)
    body = body.set_audio(body_audio)

    # Only composite subtitles when there are any (TextClip needs ImageMagick).
    subs = _subtitle_clips(srt_path)
    if subs:
        body = CompositeVideoClip([body, *subs], size=(VIDEO_W, VIDEO_H)).set_audio(body_audio)

    # Intro / Outro
    intro = _intro_outro(title, 1.4)
    outro = _intro_outro("Flux", 1.0)
    final = concatenate_videoclips([intro, body, outro], method="compose")

    final.write_videofile(
        str(out_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate="1500k",
        preset="ultrafast",
        threads=4,
        verbose=True,
        logger="bar",  # show progress in the uvicorn terminal — no more silent hangs
        temp_audiofile=str(out_path.with_suffix(".audio.m4a")),
        remove_temp=True,
        ffmpeg_params=["-tune", "stillimage", "-movflags", "+faststart"],
    )
    return out_path


def make_thumbnail(image_path: Path, out: Path) -> Path:
    """Use the first scene image as the thumbnail."""
    from PIL import Image
    out.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(image_path).convert("RGB")
    img.thumbnail((640, 360))
    img.save(out, "JPEG", quality=88)
    return out
