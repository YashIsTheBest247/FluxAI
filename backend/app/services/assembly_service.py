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


def _text_clip_safe(text: str, fontsize: int, size=(None, None), color="white", stroke=False):
    """Try several TextClip configurations; return None if ImageMagick isn't available."""
    from moviepy.editor import TextClip
    attempts = [
        dict(fontsize=fontsize, color=color, font="Arial-Bold", method="caption", size=size,
             stroke_color="black" if stroke else None, stroke_width=2 if stroke else 0),
        dict(fontsize=fontsize, color=color, method="caption", size=size),
        dict(fontsize=fontsize, color=color),
    ]
    for kwargs in attempts:
        try:
            kwargs = {k: v for k, v in kwargs.items() if v is not None or k == "size"}
            return TextClip(text, **kwargs)
        except Exception as e:
            logger.debug("TextClip attempt failed (%s): %s", kwargs, e)
    logger.warning("All TextClip attempts failed — ImageMagick likely not installed. Skipping text overlay.")
    return None


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


def assemble_video(
    title: str,
    scenes: List[Scene],
    image_paths: List[Path],
    audio_paths: List[Tuple[Path, float]],
    srt_path: Path,
    out_path: Path,
) -> Path:
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
        preset="ultrafast",   # ~10x faster than 'medium', file is bigger but quality is fine for 720p
        threads=8,
        verbose=False,
        logger=None,
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
