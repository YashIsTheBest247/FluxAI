from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    gpt_model: str = "gpt-4o"
    image_model: str = "dall-e-3"
    image_size: str = "1024x1024"

    kokoro_voice: str = "af_bella"
    kokoro_model_path: str = ""

    youtube_client_secrets: str = "secrets/youtube_client_secret.json"
    youtube_token_file: str = "secrets/youtube_token.json"
    youtube_auto_upload: bool = True
    youtube_privacy: str = "unlisted"
    youtube_category_id: str = "27"
    flux_channel_url: str = ""  # operator's public YouTube channel URL (shown in the nav + hero card)

    storage_dir: str = "storage"
    mock_mode: bool = True

    allowed_origins: str = "http://localhost:3000"

    @property
    def origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def storage_path(self) -> Path:
        p = Path(self.storage_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        (p / "videos").mkdir(exist_ok=True)
        (p / "temp").mkdir(exist_ok=True)
        (p / "thumbnails").mkdir(exist_ok=True)
        return p

    @property
    def use_mock(self) -> bool:
        return self.mock_mode or not self.openai_api_key


settings = Settings()
