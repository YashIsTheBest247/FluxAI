"""Pipeline orchestrator. Walks each job through script -> image -> voice -> subtitles -> assembly -> upload.

Two modes:
  * video   — every scene gets its own AI image; final cut is a montage MP4
  * podcast — one cover image; final output is an MP3 plus a static-cover MP4 for YouTube
"""
import asyncio
import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from .config import settings
from .models.schemas import GenerateRequest, Job, JobStage, MediaType, StageProgress, Video
from .services import (
    assembly_service,
    image_service,
    podcast_service,
    script_service,
    subtitle_service,
    voice_service,
    youtube_service,
)
from .storage import add_video, save_job

logger = logging.getLogger(__name__)

STAGE_LABELS = {
    JobStage.SCRIPT: "Script",
    JobStage.IMAGE: "Image",
    JobStage.VOICE: "Voice",
    JobStage.SUBTITLES: "Subtitles",
    JobStage.ASSEMBLY: "Assembly",
    JobStage.UPLOAD: "Upload",
}

STAGE_WEIGHTS = {
    JobStage.SCRIPT: 0.10,
    JobStage.IMAGE: 0.40,
    JobStage.VOICE: 0.20,
    JobStage.SUBTITLES: 0.05,
    JobStage.ASSEMBLY: 0.20,
    JobStage.UPLOAD: 0.05,
}


def _init_stages() -> list[StageProgress]:
    return [StageProgress(stage=s, label=STAGE_LABELS[s]) for s in STAGE_WEIGHTS]


def _new_job(req: GenerateRequest) -> Job:
    now = datetime.utcnow()
    return Job(
        id=uuid.uuid4().hex[:12],
        topic=req.topic.strip(),
        duration=req.duration,
        key_points=req.key_points,
        stage=JobStage.QUEUED,
        stages=_init_stages(),
        progress=0.0,
        created_at=now,
        updated_at=now,
        auto_upload=req.auto_upload,
        privacy=req.privacy,
        media_type=req.media_type,
    )


def _set_stage(job: Job, stage: JobStage, progress: float = 0.0, detail: str | None = None) -> None:
    job.stage = stage
    for s in job.stages:
        if s.stage == stage:
            s.progress = progress
            s.detail = detail
            break
    total = sum(STAGE_WEIGHTS.get(s.stage, 0) * s.progress for s in job.stages)
    job.progress = round(total, 4)
    job.updated_at = datetime.utcnow()
    save_job(job)


async def _make_stage_progress(job: Job, stage: JobStage):
    async def cb(pct: float):
        _set_stage(job, stage, pct)
    return cb


def _cover_prompt(title: str, topic: str) -> str:
    """Single evocative cover image for a podcast — uniform across all scenes."""
    return (
        f"Podcast cover art for '{title}'. Subject: {topic}. "
        "Cinematic, moody lighting, painterly editorial illustration, "
        "centered composition, no text, no logos."
    )


async def _run_video(job: Job, work_dir: Path) -> tuple[str, list, list, list, Path, Path]:
    """Returns (title, scenes, audio_results, image_paths, video_path, thumb_path)."""
    # 1. Script
    _set_stage(job, JobStage.SCRIPT, 0.2, "Outlining scenes")
    title, scenes = await script_service.generate_scenes(job.topic, job.duration, job.key_points)
    _set_stage(job, JobStage.SCRIPT, 1.0, f"{len(scenes)} scenes")

    # 2 + 3. Images + voice in parallel
    _set_stage(job, JobStage.IMAGE, 0.0, "Rendering visuals")
    _set_stage(job, JobStage.VOICE, 0.0, "Synthesising narration")
    img_cb = await _make_stage_progress(job, JobStage.IMAGE)
    v_cb = await _make_stage_progress(job, JobStage.VOICE)
    image_paths, audio_results = await asyncio.gather(
        image_service.generate_images(scenes, work_dir / "images", on_progress=img_cb),
        voice_service.synthesize_scenes(scenes, work_dir / "audio", on_progress=v_cb),
    )
    _set_stage(job, JobStage.IMAGE, 1.0, f"{len(image_paths)} scenes")
    _set_stage(job, JobStage.VOICE, 1.0, f"{len(audio_results)} tracks")
    audio_lengths = [d for _, d in audio_results]

    # 4. Subtitles
    _set_stage(job, JobStage.SUBTITLES, 0.4, "Timing captions")
    srt_path = subtitle_service.build_srt(scenes, audio_lengths, work_dir / "captions.srt")
    _set_stage(job, JobStage.SUBTITLES, 1.0)

    # 5. Assembly
    _set_stage(job, JobStage.ASSEMBLY, 0.2, "Compositing video")
    video_path = settings.storage_path / "videos" / f"{job.id}.mp4"
    await asyncio.to_thread(
        assembly_service.assemble_video,
        title, scenes, image_paths, audio_results, srt_path, video_path,
    )
    thumb_path = settings.storage_path / "thumbnails" / f"{job.id}.jpg"
    assembly_service.make_thumbnail(image_paths[0], thumb_path)
    _set_stage(job, JobStage.ASSEMBLY, 1.0)
    return title, scenes, audio_results, image_paths, video_path, thumb_path


async def _run_podcast(job: Job, work_dir: Path) -> tuple[str, list, list, Path, Path, Path]:
    """Returns (title, scenes, audio_results, mp3_path, mp4_path, thumb_path)."""
    # 1. Script
    _set_stage(job, JobStage.SCRIPT, 0.2, "Outlining episode")
    title, scenes = await script_service.generate_scenes(job.topic, job.duration, job.key_points)
    _set_stage(job, JobStage.SCRIPT, 1.0, f"{len(scenes)} segments")

    # 2 + 3. Cover image (single) + voice — much faster than per-scene rendering.
    _set_stage(job, JobStage.IMAGE, 0.0, "Painting cover art")
    _set_stage(job, JobStage.VOICE, 0.0, "Recording narration")
    v_cb = await _make_stage_progress(job, JobStage.VOICE)
    cover_path = work_dir / "cover.png"
    cover_task = image_service.generate_image(_cover_prompt(title, job.topic), cover_path)
    voice_task = voice_service.synthesize_scenes(scenes, work_dir / "audio", on_progress=v_cb)
    cover_path, audio_results = await asyncio.gather(cover_task, voice_task)
    _set_stage(job, JobStage.IMAGE, 1.0, "Cover ready")
    _set_stage(job, JobStage.VOICE, 1.0, f"{len(audio_results)} tracks")
    audio_lengths = [d for _, d in audio_results]

    # 4. Subtitles (also used as chapter markers in future iterations)
    _set_stage(job, JobStage.SUBTITLES, 0.4, "Timing captions")
    srt_path = subtitle_service.build_srt(scenes, audio_lengths, work_dir / "captions.srt")
    _set_stage(job, JobStage.SUBTITLES, 1.0)

    # 5. Assembly: MP3 + static-cover MP4
    _set_stage(job, JobStage.ASSEMBLY, 0.2, "Mastering audio")
    mp3_path = settings.storage_path / "podcasts" / f"{job.id}.mp3"
    mp4_path = settings.storage_path / "videos" / f"{job.id}.mp4"
    await asyncio.to_thread(
        podcast_service.assemble_podcast,
        title, scenes, cover_path, audio_results, srt_path, mp3_path, mp4_path,
    )
    thumb_path = settings.storage_path / "thumbnails" / f"{job.id}.jpg"
    assembly_service.make_thumbnail(cover_path, thumb_path)
    _set_stage(job, JobStage.ASSEMBLY, 1.0)
    return title, scenes, audio_results, mp3_path, mp4_path, thumb_path


async def run_pipeline(job: Job) -> None:
    work_dir = settings.storage_path / "temp" / job.id
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        if job.media_type == MediaType.PODCAST:
            title, scenes, audio_results, mp3_path, video_path, thumb_path = await _run_podcast(job, work_dir)
            audio_url = f"/media/podcasts/{mp3_path.name}"
        else:
            title, scenes, audio_results, _imgs, video_path, thumb_path = await _run_video(job, work_dir)
            audio_url = None

        # 6. YouTube upload — both modes upload an MP4 (podcasts use a static-cover MP4).
        srt_path = work_dir / "captions.srt"
        youtube_url = None
        if job.auto_upload:
            _set_stage(job, JobStage.UPLOAD, 0.2, "Uploading to YouTube")
            try:
                yt = await asyncio.to_thread(
                    youtube_service.upload,
                    video_path, title, job.topic, job.key_points, thumb_path, job.privacy,
                )
                youtube_url = yt.url
                job.youtube_url = yt.url
                _set_stage(job, JobStage.UPLOAD, 0.7, "Attaching captions")
                if srt_path.exists():
                    await asyncio.to_thread(youtube_service.upload_captions, yt.video_id, srt_path)
            except Exception as e:
                logger.exception("upload failed: %s", e)
                _set_stage(job, JobStage.UPLOAD, 1.0, f"Upload skipped: {e}")
            else:
                _set_stage(job, JobStage.UPLOAD, 1.0, "Uploaded + captioned")
        else:
            _set_stage(job, JobStage.UPLOAD, 1.0, "Skipped")

        rel_video = video_path.relative_to(settings.storage_path).as_posix()
        rel_thumb = thumb_path.relative_to(settings.storage_path).as_posix()
        video = Video(
            id=job.id,
            title=title,
            topic=job.topic,
            duration=job.duration,
            created_at=datetime.utcnow(),
            file_url=f"/media/{rel_video}",
            audio_url=audio_url,
            thumbnail_url=f"/media/{rel_thumb}",
            resolution=f"{assembly_service.VIDEO_W}x{assembly_service.VIDEO_H}",
            scene_count=len(scenes),
            youtube_url=youtube_url,
            media_type=job.media_type,
        )
        add_video(video)
        job.video = video
        job.stage = JobStage.DONE
        job.progress = 1.0
        job.updated_at = datetime.utcnow()
        save_job(job)

    except Exception as e:
        logger.exception("pipeline failed for job %s", job.id)
        job.stage = JobStage.FAILED
        job.error = str(e)
        job.updated_at = datetime.utcnow()
        save_job(job)
    finally:
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


def submit(req: GenerateRequest) -> Job:
    job = _new_job(req)
    save_job(job)
    asyncio.create_task(run_pipeline(job))
    return job
