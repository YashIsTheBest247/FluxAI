from fastapi import APIRouter, HTTPException, Query

from ..models.schemas import Video
from ..storage import delete_video, list_videos

router = APIRouter(prefix="/api/videos", tags=["library"])


@router.get("", response_model=list[Video])
async def get_videos(q: str | None = Query(default=None)):
    return list_videos(query=q)


@router.delete("/{video_id}")
async def remove_video(video_id: str):
    if not delete_video(video_id):
        raise HTTPException(404, "video not found")
    return {"ok": True}
