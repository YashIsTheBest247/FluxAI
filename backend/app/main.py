import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers import generation, library, youtube

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _hydrate_youtube_secrets() -> None:
    """Materialise YouTube OAuth credentials from env vars to disk.

    Required on hosts with no persistent storage (Render free tier): the
    operator generates secrets/youtube_token.json locally via setup_youtube.py,
    then pastes the file contents into Render env vars. At boot, this writes
    them back to the paths google-auth-oauthlib expects to find them.

    No-op on hosts where the files already exist on disk (local dev, Fly with
    a volume) — we don't clobber an existing file.
    """
    for env_value, target in (
        (settings.youtube_client_secret_json, settings.youtube_client_secrets),
        (settings.youtube_token_json, settings.youtube_token_file),
    ):
        if not env_value:
            continue
        p = Path(target)
        if p.exists() and p.stat().st_size > 0:
            continue  # don't trample a locally-managed file
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(env_value, encoding="utf-8")
            logger.info("hydrated YouTube secret from env -> %s", target)
        except Exception as e:
            logger.warning("failed to hydrate YouTube secret to %s: %s", target, e)


_hydrate_youtube_secrets()

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
        "provider": settings.provider_normalized,
        "version": "1.0.0",
        "channel_url": settings.flux_channel_url or None,
    }
