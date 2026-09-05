"""Application settings, read once from the environment.

Everything configurable lives here so that no module reaches into os.environ
on its own. The defaults are the local Docker Compose values, so a fresh clone
runs without a .env file at all.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DSN = "postgresql+psycopg://revix:revix@localhost:5433/revix"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------- database ----------
    database_url: PostgresDsn = Field(default=LOCAL_DSN)  # type: ignore[assignment]
    db_echo: bool = False
    db_pool_size: int = 5

    # ---------- api ----------
    api_env: Literal["development", "production"] = "development"
    # Both loopback spellings, because a browser treats "localhost" and
    # "127.0.0.1" as separate origins and the dev stack uses them
    # interchangeably. Missing one blocks the type-ahead in the browser while
    # the server still logs a healthy 200, which is a miserable thing to debug.
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ---------- language model ----------
    # Batch narration only. Section 16 of the proposal requires that a complete
    # verdict renders with this off, so nothing on the read path may depend on it.
    llm_enabled: bool = False
    llm_provider: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    # ---------- collection politeness ----------
    default_rate_limit_rpm: int = 20
    default_request_timeout_s: float = 30.0
    user_agent: str = (
        "revix/0.1 (+https://github.com/saaachis/revix-evidence-traceable-review-system)"
    )

    # ---------- source credentials ----------
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = ""
    youtube_api_key: str = ""

    # ---------- evidence floor ----------
    # A verdict is suppressed below these thresholds rather than published badly.
    min_evidence_units: int = 40
    min_distinct_sources: int = 3

    @field_validator("cors_allowed_origins")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def sync_database_url(self) -> str:
        """psycopg3 speaks both sync and async, so one DSN covers Alembic too."""
        return str(self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
