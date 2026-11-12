"""Application settings, validated once at startup from environment / .env."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    llm_provider: Literal["gemini", "groq"] = "gemini"
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.5-flash"
    groq_api_key: SecretStr = SecretStr("")
    groq_model: str = "llama-3.3-70b-versatile"
    database_path: Path = REPO_ROOT / "data" / "ecommerce.db"
    max_rows: int = Field(default=200, ge=1, le=10_000)
    query_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    max_question_length: int = Field(default=500, ge=1, le=5_000)
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    """Cached settings; used as a FastAPI dependency so tests can override it."""
    return Settings()
