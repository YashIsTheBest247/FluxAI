from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class JobStage(str, Enum):
    QUEUED = "queued"
    SCRIPT = "script"
    IMAGE = "image"
    VOICE = "voice"
    SUBTITLES = "subtitles"
    ASSEMBLY = "assembly"
    UPLOAD = "upload"
    DONE = "done"
    FAILED = "failed"


class MediaType(str, Enum):
    VIDEO = "video"
    PODCAST = "podcast"


class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=120)
    duration: int = Field(30, ge=10, le=600)
    key_points: Optional[str] = Field(default=None, max_length=2000)
    auto_upload: bool = True
    privacy: str = "unlisted"
    media_type: MediaType = MediaType.VIDEO


class Scene(BaseModel):
    index: int
    narration: str
    image_prompt: str
    duration: float


class StageProgress(BaseModel):
    stage: JobStage
    label: str
    progress: float = 0.0
    detail: Optional[str] = None


class Video(BaseModel):
    id: str
    title: str
    topic: str
    duration: int
    created_at: datetime
    file_url: str
    audio_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    resolution: str = "1080p"
    scene_count: int = 0
    youtube_url: Optional[str] = None
    media_type: MediaType = MediaType.VIDEO


class Job(BaseModel):
    id: str
    topic: str
    duration: int
    key_points: Optional[str] = None
    stage: JobStage = JobStage.QUEUED
    stages: List[StageProgress] = []
    progress: float = 0.0
    error: Optional[str] = None
    video: Optional[Video] = None
    created_at: datetime
    updated_at: datetime
    auto_upload: bool = True
    privacy: str = "unlisted"
    youtube_url: Optional[str] = None
    media_type: MediaType = MediaType.VIDEO


class YouTubeUploadResult(BaseModel):
    video_id: str
    url: str
    title: str
