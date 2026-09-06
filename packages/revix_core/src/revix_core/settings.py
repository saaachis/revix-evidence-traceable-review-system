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
    # Which communities to read, comma separated and without the "r/". Kept in
    # configuration rather than in code because the right list is an editorial
    # judgement that changes faster than a release, and a subreddit that is
    # renamed, private or misspelled should be a line in .env to fix rather
    # than a patch. The connector skips one it cannot read.
    reddit_subreddits_car: str = "CarsIndia"
    reddit_subreddits_two_wheeler: str = "indianbikes"
    youtube_api_key: str = ""

    # ---------- learned components ----------
    # Off until the classifier is shown to beat the lexicon on the
    # hand-labelled set. Loading it merely because a trained file exists would
    # let somebody's local experiment silently downgrade the pipeline, and the
    # first measured comparison had the classifier LOSING to the rules it was
    # trained from by 0.34 macro F1. A model has to earn its place.
    #
    #   uv run revix model evaluate --gold data/gold/aspects.jsonl
    #
    # Flip this only when that says the classifier wins.
    aspect_classifier_enabled: bool = False

    # ---------- model-level evidence ----------
    # A review of "the Creta" is real evidence about a Creta SX(O) Turbo DCT,
    # but weaker evidence than a review of that exact trim. This is the
    # discount applied to it.
    #
    # 0.6 is a judgement, not a measurement, and it is here rather than inside
    # the fusion code so that it is visible, tunable, and obviously a choice
    # somebody made. It applies identically to every strategy, so it cannot
    # flatter one of them in the section 18.1 comparison. Setting it to 0
    # restores the old behaviour of ignoring model-level evidence entirely.
    model_level_evidence_weight: float = 0.6

    # ---------- evidence floor ----------
    # A verdict is suppressed below these thresholds rather than published badly.
    min_evidence_units: int = 40
    # Two, not three. Three was chosen before we knew what the Indian review
    # landscape actually permits, and it turned out to be a number about a
    # market we had not surveyed yet. For two-wheelers there are only two
    # publishers that allow us at all: ZigWheels forbids review paths,
    # 91wheels is Disallow: / outright, BikeWale exposes one review per model.
    # Holding out for a third meant every one of the fifteen bikes in the
    # catalogue published nothing.
    #
    # Two genuinely independent platforms is a real guard against one
    # platform's culture dominating a verdict, which is what this floor is
    # for. One is not. And the verdict page prints the source count, so a
    # reader can weigh a two-source verdict for themselves rather than taking
    # our word for it. See ADR 0009.
    min_distinct_sources: int = 2

    @field_validator("cors_allowed_origins")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    def subreddits_for(self, vehicle_class: str) -> list[str]:
        raw = (
            self.reddit_subreddits_two_wheeler
            if vehicle_class == "two_wheeler"
            else self.reddit_subreddits_car
        )
        return [s.strip().removeprefix("r/") for s in raw.split(",") if s.strip()]

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
