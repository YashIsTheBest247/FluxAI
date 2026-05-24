from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings
from ..services import youtube_service
from ..storage import list_videos

router = APIRouter(prefix="/api/youtube", tags=["youtube"])


class ManualUploadRequest(BaseModel):
    video_id: str
    privacy: str = "unlisted"


@router.post("/upload")
async def upload_existing(req: ManualUploadRequest):
    videos = [v for v in list_videos() if v.id == req.video_id]
    if not videos:
        raise HTTPException(404, "video not found")
    video = videos[0]
    video_path = settings.storage_path / "videos" / f"{video.id}.mp4"
    thumb_path = settings.storage_path / "thumbnails" / f"{video.id}.jpg"
    if not video_path.exists():
        raise HTTPException(404, "video file missing")
    result = youtube_service.upload(
        video_path,
        video.title,
        video.topic,
        None,
        thumb_path if thumb_path.exists() else None,
        req.privacy,
    )
    return result
