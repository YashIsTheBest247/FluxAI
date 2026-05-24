"""Pipeline orchestrator. Walks each job through script -> image -> voice -> subtitles -> assembly -> upload."""
import asyncio
import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from .config import settings
from .models.schemas import GenerateRequest, Job, JobStage, StageProgress, Video
from .services import (
    assembly_service,
    image_service,
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
    )


def _set_stage(job: Job, stage: JobStage, progress: float = 0.0, detail: str | None = None) -> None:
    job.stage = stage
    order = list(STAGE_WEIGHTS)
    current_idx = order.index(stage) if stage in order else -1
    for s in job.stages:
        s_idx = order.index(s.stage) if s.stage in order else -1
        if s.stage == stage:
            s.progress = progress
            s.detail = detail
        elif current_idx >= 0 and s_idx >= 0 and s_idx < current_idx:
            s.progress = 1.0
    # Recompute total
    total = 0.0
    for s in job.stages:
        total += STAGE_WEIGHTS.get(s.stage, 0) * s.progress
    job.progress = round(total, 4)
    job.updated_at = datetime.utcnow()
    save_job(job)


async def _make_stage_progress(job: Job, stage: JobStage):
    async def cb(pct: float):
        _set_stage(job, stage, pct)
    return cb


async def run_pipeline(job: Job) -> None:
    work_dir = settings.storage_path / "temp" / job.id
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        # 1. Script
        _set_stage(job, JobStage.SCRIPT, 0.2, "Outlining scenes")
        title, scenes = await script_service.generate_scenes(job.topic, job.duration, job.key_points)
        _set_stage(job, JobStage.SCRIPT, 1.0, f"{len(scenes)} scenes")

        # 2 + 3. Images and voice run concurrently — they're independent and both
        # only depend on the script. Each one also runs its own scenes in parallel.
        _set_stage(job, JobStage.IMAGE, 0.0, "Rendering visuals")
        _set_stage(job, JobStage.VOICE, 0.0, "Synthesising narration")
        img_cb = await _make_stage_progress(job, JobStage.IMAGE)
        v_cb = await _make_stage_progress(job, JobStage.VOICE)
        image_paths, audio_results = await asyncio.gather(
            image_service.generate_images(scenes, work_dir / "images", on_progress=img_cb),
            voice_service.synthesize_scenes(scenes, work_dir / "audio", on_progress=v_cb),
        )
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
            title,
            scenes,
            image_paths,
            audio_results,
            srt_path,
            video_path,
        )
        thumb_path = settings.storage_path / "thumbnails" / f"{job.id}.jpg"
        assembly_service.make_thumbnail(image_paths[0], thumb_path)
        _set_stage(job, JobStage.ASSEMBLY, 1.0)

        # 6. YouTube upload
        youtube_url = None
        if job.auto_upload:
            _set_stage(job, JobStage.UPLOAD, 0.2, "Uploading to YouTube")
            try:
                yt = await asyncio.to_thread(
                    youtube_service.upload,
                    video_path,
                    title,
                    job.topic,
                    job.key_points,
                    thumb_path,
                    job.privacy,
                )
                youtube_url = yt.url
                job.youtube_url = yt.url
            except Exception as e:
                logger.exception("upload failed: %s", e)
                _set_stage(job, JobStage.UPLOAD, 1.0, f"Upload skipped: {e}")
            else:
                _set_stage(job, JobStage.UPLOAD, 1.0, "Uploaded")
        else:
            _set_stage(job, JobStage.UPLOAD, 1.0, "Skipped")

        # Register the video
        rel_video = video_path.relative_to(settings.storage_path).as_posix()
        rel_thumb = thumb_path.relative_to(settings.storage_path).as_posix()
        video = Video(
            id=job.id,
            title=title,
            topic=job.topic,
            duration=job.duration,
            created_at=datetime.utcnow(),
            file_url=f"/media/{rel_video}",
            thumbnail_url=f"/media/{rel_thumb}",
            resolution=f"{assembly_service.VIDEO_W}x{assembly_service.VIDEO_H}",
            scene_count=len(scenes),
            youtube_url=youtube_url,
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
        # Clean temp working files but keep final outputs
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


def submit(req: GenerateRequest) -> Job:
    job = _new_job(req)
    save_job(job)
    # Fire-and-forget on the running event loop (we're inside a FastAPI request).
    asyncio.create_task(run_pipeline(job))
    return job
