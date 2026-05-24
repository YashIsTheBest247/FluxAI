"""Lightweight on-disk storage for jobs and a videos index."""
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .config import settings
from .models.schemas import Job, Video

_LOCK = threading.Lock()


def _jobs_dir() -> Path:
    p = settings.storage_path / "jobs"
    p.mkdir(exist_ok=True)
    return p


def _videos_index() -> Path:
    return settings.storage_path / "videos_index.json"


def save_job(job: Job) -> None:
    with _LOCK:
        path = _jobs_dir() / f"{job.id}.json"
        path.write_text(job.model_dump_json(indent=2), encoding="utf-8")


def load_job(job_id: str) -> Optional[Job]:
    path = _jobs_dir() / f"{job_id}.json"
    if not path.exists():
        return None
    return Job.model_validate_json(path.read_text(encoding="utf-8"))


def list_jobs(limit: int = 50) -> List[Job]:
    items: List[Job] = []
    for p in sorted(_jobs_dir().glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
        try:
            items.append(Job.model_validate_json(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    return items


def clear_pending_jobs() -> int:
    """Delete every job file that hasn't completed (queued, in-progress, failed).
    Returns the number of jobs cleared. Used on page refresh so stale renders
    don't clutter the UI."""
    with _LOCK:
        cleared = 0
        for p in _jobs_dir().glob("*.json"):
            try:
                job = Job.model_validate_json(p.read_text(encoding="utf-8"))
                if job.stage.value != "done":
                    p.unlink()
                    cleared += 1
            except Exception:
                try:
                    p.unlink()
                    cleared += 1
                except Exception:
                    pass
        return cleared


def _load_videos_raw() -> List[dict]:
    p = _videos_index()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_videos_raw(items: List[dict]) -> None:
    _videos_index().write_text(json.dumps(items, indent=2, default=str), encoding="utf-8")


def add_video(video: Video) -> None:
    with _LOCK:
        items = _load_videos_raw()
        items = [v for v in items if v.get("id") != video.id]
        items.insert(0, json.loads(video.model_dump_json()))
        _save_videos_raw(items)


def list_videos(query: Optional[str] = None) -> List[Video]:
    with _LOCK:
        items = _load_videos_raw()
    videos = [Video.model_validate(v) for v in items]
    if query:
        q = query.lower().strip()
        videos = [v for v in videos if q in v.title.lower() or q in v.topic.lower()]
    return videos


def delete_video(video_id: str) -> bool:
    with _LOCK:
        items = _load_videos_raw()
        new_items = [v for v in items if v.get("id") != video_id]
        removed = len(new_items) != len(items)
        if removed:
            _save_videos_raw(new_items)
        # Remove associated files
        for sub in ("videos", "thumbnails"):
            for ext in (".mp4", ".jpg", ".png"):
                p = settings.storage_path / sub / f"{video_id}{ext}"
                if p.exists():
                    try:
                        p.unlink()
                    except Exception:
                        pass
    return removed
