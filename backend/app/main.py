import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers import generation, library, youtube

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(
    title="Flux",
    description="AI-powered educational video generation pipeline.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=str(settings.storage_path)), name="media")

app.include_router(generation.router)
app.include_router(library.router)
app.include_router(youtube.router)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "mock_mode": settings.use_mock,
        "version": "1.0.0",
        "channel_url": settings.flux_channel_url or None,
    }
