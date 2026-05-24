"""YouTube auto-upload service.

Uses OAuth installed-app flow. Token file is persisted after first auth.
Returns the public/unlisted/private video URL after upload.
Standard landscape video upload with thumbnail + captions track.
"""
import logging
from pathlib import Path
from typing import Optional

from ..config import settings
from ..models.schemas import YouTubeUploadResult

logger = logging.getLogger(__name__)

# 'youtube' (broad) instead of 'youtube.upload' (narrow) because we also need
# captions().insert() and thumbnails().set() which the narrow scope blocks.
SCOPES = ["https://www.googleapis.com/auth/youtube"]


class TokenMissing(RuntimeError):
    """Raised when the operator's YouTube token isn't set up yet. Run setup_youtube.py once."""


def _get_service(*, allow_interactive: bool = False):
    """Load the persisted operator token. Refresh if needed.

    The operator runs `python -m app.setup_youtube` once to generate the token; from then on
    every render auto-publishes to the same channel. The web server itself never opens
    a browser tab — `allow_interactive=False` is enforced for request-time callers.
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    token_path = Path(settings.youtube_token_file)
    secrets_path = Path(settings.youtube_client_secrets)

    creds: Optional[Credentials] = None
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception as e:
            # Old tokens issued under the narrower 'youtube.upload' scope will fail
            # to load against the broader scope list. Treat as expired so the
            # interactive flow re-issues with the correct scopes.
            logger.warning("youtube_service: token file unreadable for scopes (%s); will re-auth", e)
            creds = None
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                token_path.write_text(creds.to_json(), encoding="utf-8")
            except Exception as e:
                logger.warning("youtube_service: token refresh failed: %s", e)
                creds = None

    if (not creds or not creds.valid) and allow_interactive:
        if not secrets_path.exists():
            raise TokenMissing(
                f"OAuth client secrets not found at {secrets_path}. "
                "Download a 'Desktop app' OAuth client JSON from Google Cloud Console and save it there."
            )
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
        creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    if not creds or not creds.valid:
        raise TokenMissing(
            "YouTube token missing or expired. Run `python -m app.setup_youtube` from the backend folder."
        )
    return build("youtube", "v3", credentials=creds)


def build_metadata(title: str, topic: str, key_points: Optional[str] = None) -> dict:
    """Standard landscape video metadata."""
    description_lines = [
        title,
        "",
        f"Topic: {topic}",
    ]
    if key_points:
        description_lines += ["", "Key points:", key_points.strip()]
    description_lines += [
        "",
        "Generated automatically by Flux — an AI-driven educational video pipeline.",
    ]
    return {
        "snippet": {
            "title": title[:99],
            "description": "\n".join(description_lines)[:4900],
            "tags": ["education", "explained", "ai", "flux", topic.lower()],
            "categoryId": settings.youtube_category_id,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": settings.youtube_privacy,
            "selfDeclaredMadeForKids": False,
        },
    }


def upload(
    video_path: Path,
    title: str,
    topic: str,
    key_points: Optional[str] = None,
    thumbnail_path: Optional[Path] = None,
    privacy: Optional[str] = None,
) -> YouTubeUploadResult:
    if settings.use_mock:
        fake_id = f"mock_{abs(hash(title)) % (10**11):011d}"
        logger.info("youtube_service: MOCK_MODE -> skipping real upload (id=%s)", fake_id)
        return YouTubeUploadResult(
            video_id=fake_id,
            url=f"https://www.youtube.com/watch?v={fake_id}",
            title=title,
        )

    from googleapiclient.http import MediaFileUpload

    if privacy:
        settings.youtube_privacy = privacy

    service = _get_service()
    body = build_metadata(title, topic, key_points)
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = service.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info("youtube_service: upload progress %.0f%%", status.progress() * 100)
    vid = response["id"]

    # Custom thumbnail (vertical 720x1280 generated by assembly_service.make_thumbnail).
    if thumbnail_path and thumbnail_path.exists():
        try:
            service.thumbnails().set(
                videoId=vid,
                media_body=MediaFileUpload(str(thumbnail_path)),
            ).execute()
            logger.info("youtube_service: thumbnail uploaded for %s", vid)
        except Exception as e:
            logger.warning("youtube_service: thumbnail upload failed: %s", e)

    return YouTubeUploadResult(
        video_id=vid,
        url=f"https://www.youtube.com/watch?v={vid}",
        title=title,
    )


def upload_captions(video_id: str, srt_path: Path, language: str = "en", name: str = "English") -> Optional[str]:
    """Upload an SRT caption track and attach it to an already-uploaded video.

    Returns the caption resource id on success, None on failure.
    Captions appear in the YouTube player's CC button and feed YouTube's transcript.
    """
    if settings.use_mock:
        logger.info("youtube_service: MOCK_MODE -> skipping caption upload for %s", video_id)
        return None
    if not srt_path.exists():
        logger.warning("youtube_service: caption file missing %s", srt_path)
        return None

    from googleapiclient.http import MediaFileUpload

    try:
        service = _get_service()
        body = {
            "snippet": {
                "videoId": video_id,
                "language": language,
                "name": name,
                "isDraft": False,
            }
        }
        media = MediaFileUpload(str(srt_path), mimetype="application/octet-stream", resumable=False)
        resp = service.captions().insert(part="snippet", body=body, media_body=media).execute()
        cap_id = resp.get("id")
        logger.info("youtube_service: captions uploaded (%s) for video %s", cap_id, video_id)
        return cap_id
    except Exception as e:
        logger.warning("youtube_service: caption upload failed for %s: %s", video_id, e)
        return None
