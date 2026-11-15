"""Application settings, validated once at startup from environment / .env."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: Literal["development", "production"] = "development"
    llm_provider: Literal["gemini", "groq"] = "gemini"
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.5-flash"
    # Gemini 3.x is a reasoning model; lower effort trades depth for much lower latency.
    gemini_reasoning_effort: Literal["low", "medium", "high"] = "low"
    # Caps the reply (includes reasoning tokens, so keep generous headroom over the SQL itself).
    llm_max_tokens: int = Field(default=1024, ge=64, le=8192)
    answer_cache_size: int = Field(default=128, ge=0, le=10_000)  # 0 disables the cache
    groq_api_key: SecretStr = SecretStr("")
    groq_model: str = "llama-3.3-70b-versatile"
    database_path: Path = REPO_ROOT / "data" / "ecommerce.db"
    max_rows: int = Field(default=200, ge=1, le=10_000)
    query_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    max_question_length: int = Field(default=500, ge=1, le=5_000)
    # Per-client requests/minute on /api/ask (each one can cost an LLM call); 0 disables.
    rate_limit_per_minute: int = Field(default=20, ge=0, le=10_000)
    # Global cap on LLM calls per UTC day (cache hits are free); 0 disables.
    daily_llm_call_limit: int = Field(default=500, ge=0, le=1_000_000)
    # Built frontend to serve at "/" (set in the Docker image); unset = API only.
    static_dir: Path | None = None
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]

    @model_validator(mode="after")
    def _require_key_in_production(self) -> "Settings":
        """Fail fast at startup rather than on the first user's question."""
        key = self.gemini_api_key if self.llm_provider == "gemini" else self.groq_api_key
        if self.environment == "production" and not key.get_secret_value():
            raise ValueError(f"{self.llm_provider.upper()}_API_KEY must be set in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings; used as a FastAPI dependency so tests can override it."""
    return Settings()
