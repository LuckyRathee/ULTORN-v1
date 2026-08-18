"""
Configuration management using pydantic-settings.

Loads from .env file and environment variables.
All settings are validated at startup.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Literal, Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Supabase
    supabase_url: str = Field(alias="SUPABASE_URL")
    supabase_service_key: str = Field(alias="SUPABASE_SERVICE_KEY")

    # STT
    stt_provider: Literal["groq", "local"] = Field(default="groq", alias="STT_PROVIDER")
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    whisper_model: str = Field(default="base", alias="WHISPER_MODEL")

    # LLM (Intent Extraction)
    llm_provider: Literal["groq", "anthropic"] = Field(default="groq", alias="LLM_PROVIDER")
    groq_api_key_llm: Optional[str] = Field(default=None, alias="GROQ_API_KEY")  # Same as STT key
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    intent_model: str = Field(default="llama-3.1-8b-instant", alias="INTENT_MODEL")

    # TTS (Optional for v1)
    tts_provider: Literal["elevenlabs", "azure", "none"] = Field(default="none", alias="TTS_PROVIDER")
    elevenlabs_api_key: Optional[str] = Field(default=None, alias="ELEVENLABS_API_KEY")
    elevenlabs_voice_id: Optional[str] = Field(default=None, alias="ELEVENLABS_VOICE_ID")
    azure_tts_key: Optional[str] = Field(default=None, alias="AZURE_TTS_KEY")
    azure_tts_region: Optional[str] = Field(default=None, alias="AZURE_TTS_REGION")

    # Weather API
    weather_api_key: str = Field(alias="WEATHER_API_KEY")
    weather_api_base: str = Field(default="https://api.weatherapi.com/v1", alias="WEATHER_API_BASE")

    # Calendar API (Google)
    google_client_id: Optional[str] = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(default=None, alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: Optional[str] = Field(default=None, alias="GOOGLE_REDIRECT_URI")

    # Task API (Notion)
    notion_api_key: Optional[str] = Field(default=None, alias="NOTION_API_KEY")
    notion_database_id: Optional[str] = Field(default=None, alias="NOTION_DATABASE_ID")


# Global settings instance
settings = Settings()