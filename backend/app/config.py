from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # === Provider selection ===
    # "openai"  — uses GPT-4 + DALL-E 3 (paid)
    # "gemini"  — uses Google Gemini + Pollinations.ai (free)
    provider: str = "openai"

    # === OpenAI ===
    openai_api_key: str = ""
    gpt_model: str = "gpt-4o"
    # gpt-image-1 is OpenAI's current image model (dall-e-3 was rolled off
    # for many orgs in late 2025 and now returns 400 invalid_value).
    image_model: str = "gpt-image-1"
    image_size: str = "1024x1024"

    # === Google Gemini (free tier) ===
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"   # gemini-1.5-* was deprecated; 2.5 supports JSON mode
    gemini_image_model: str = "gemini-2.5-flash-image"   # "Nano Banana" image generator — paid fallback

    # === Pollinations.ai (free, no key needed) ===
    # `flux` and other premium models were moved behind auth in early 2026 and
    # now return 402. `sana` is the current anonymous-tier default; the service
    # rotates through known-free fallbacks if this one stops working.
    pollinations_model: str = "sana"

    kokoro_voice: str = "af_bella"
    kokoro_model_path: str = ""

    youtube_client_secrets: str = "secrets/youtube_client_secret.json"
    youtube_token_file: str = "secrets/youtube_token.json"
    youtube_auto_upload: bool = True
    youtube_privacy: str = "unlisted"
    youtube_category_id: str = "27"
    flux_channel_url: str = ""

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
        (p / "podcasts").mkdir(exist_ok=True)
        (p / "temp").mkdir(exist_ok=True)
        (p / "thumbnails").mkdir(exist_ok=True)
        return p

    @property
    def provider_normalized(self) -> str:
        p = (self.provider or "openai").strip().lower()
        return p if p in ("openai", "gemini") else "openai"

    @property
    def use_mock(self) -> bool:
        """True when we have no usable credentials and should fall back to placeholders."""
        if self.mock_mode:
            return True
        if self.provider_normalized == "openai":
            return not self.openai_api_key
        if self.provider_normalized == "gemini":
            # Pollinations doesn't need a key, so Gemini key alone is enough for real output.
            return not self.gemini_api_key
        return True


settings = Settings()
