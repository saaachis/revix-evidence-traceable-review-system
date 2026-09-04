"""Sources, runs, raw payloads and the Evidence Unit.

The Evidence Unit is the highest-leverage decision in the whole design. An
owner review, a forum post, a video transcript and a recall notice all become
one shape, so every stage downstream is written once rather than once per
source. Proposal section 12.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from revix_core.enums import Modality, RunStatus, SourceKind
from revix_core.models.base import (
    SCHEMA_CORE,
    SCHEMA_RAW,
    Base,
    TimestampMixin,
    uuid_pk,
)


class EvidenceSource(Base, TimestampMixin):
    """The connector registry. One row per source we read."""

    __tablename__ = "evidence_source"
    __table_args__ = {"schema": SCHEMA_CORE}

    id: Mapped[uuid.UUID] = uuid_pk()
    source_key: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[SourceKind] = mapped_column(
        Enum(SourceKind, name="source_kind", schema=SCHEMA_CORE), nullable=False
    )
    base_url: Mapped[str | None] = mapped_column(Text)

    # What the site's robots file and terms said, and when we read them. This
    # is recorded per source because the report needs it and because a claim
    # to have checked is worth nothing without a date.
    robots_policy: Mapped[str | None] = mapped_column(Text)
    terms_reviewed_on: Mapped[datetime | None] = mapped_column()

    rate_limit_rpm: Mapped[int] = mapped_column(SmallInteger, default=20, nullable=False)
    # Used by the source-weighted fusion strategy. Not used by S0 or S2.
    default_source_prior: Mapped[float] = mapped_column(Numeric(3, 2), default=0.5, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class IngestRun(Base):
    """One execution of one connector. Telemetry for the status page."""

    __tablename__ = "ingest_run"
    __table_args__ = (
        Index("ix_ingest_run_source_started", "source_id", "started_at"),
        {"schema": SCHEMA_CORE},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_CORE}.evidence_source.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status", schema=SCHEMA_CORE), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column()

    refs_discovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payloads_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    units_inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    units_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    checkpoint: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    source: Mapped[EvidenceSource] = relationship()


class RawPayload(Base):
    """Immutable, stored before parsing.

    This is what makes the pipeline replayable. When a parser improves,
    evidence is re-derived without contacting the source again. That is better
    engineering and it is also the polite thing to do.
    """

    __tablename__ = "raw_payload"
    __table_args__ = (
        UniqueConstraint("sha256"),
        Index("ix_raw_payload_source_fetched", "source_id", "fetched_at"),
        {"schema": SCHEMA_RAW},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_CORE}.evidence_source.id", ondelete="CASCADE"), nullable=False
    )
    ingest_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_CORE}.ingest_run.id", ondelete="SET NULL")
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(nullable=False)
    http_status: Mapped[int | None] = mapped_column(SmallInteger)
    content_type: Mapped[str | None] = mapped_column(String(120))
    body: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class SourceListing(Base, TimestampMixin):
    """What each source calls a vehicle, before we work out what it really is."""

    __tablename__ = "source_listing"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id"),
        Index("ix_source_listing_unresolved", "source_id", "variant_id"),
        {"schema": SCHEMA_CORE},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_CORE}.evidence_source.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    raw_title: Mapped[str] = mapped_column(Text, nullable=False)
    raw_specs: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Null until resolved. Anything still null after a run is either genuinely
    # new or sitting below the confidence floor waiting for a person.
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_CORE}.vehicle_variant.id", ondelete="SET NULL")
    )
    match_method: Mapped[str | None] = mapped_column(String(20))
    match_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    resolved_at: Mapped[datetime | None] = mapped_column()


class EvidenceUnit(Base, TimestampMixin):
    """One piece of evidence from one source about one vehicle."""

    __tablename__ = "evidence_unit"
    __table_args__ = (
        # Re-running any connector is safe because of these two. The first
        # stops the same external record being inserted twice; the second
        # catches the same text arriving under a different id.
        UniqueConstraint("source_id", "external_id"),
        UniqueConstraint("content_hash"),
        CheckConstraint(
            "rating_normalized IS NULL OR (rating_normalized >= 0 AND rating_normalized <= 1)",
            name="rating_normalized_range",
        ),
        CheckConstraint(
            "spam_probability IS NULL OR (spam_probability >= 0 AND spam_probability <= 1)",
            name="spam_probability_range",
        ),
        Index("ix_evidence_unit_variant_published", "variant_id", "published_at"),
        {"schema": SCHEMA_CORE},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_CORE}.evidence_source.id", ondelete="CASCADE"), nullable=False
    )
    ingest_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_CORE}.ingest_run.id", ondelete="SET NULL")
    )
    raw_payload_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_RAW}.raw_payload.id", ondelete="SET NULL")
    )

    # Resolved target. model_id is the fallback granularity when a review is
    # clearly about the model but not attributable to one variant.
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_CORE}.vehicle_variant.id", ondelete="SET NULL")
    )
    model_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_CORE}.vehicle_model.id", ondelete="SET NULL")
    )

    external_id: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)

    # A stable opaque key, never a name, an email or a profile URL. It exists
    # so we can spot one account posting in bursts, and for nothing else.
    author_ref: Mapped[str | None] = mapped_column(String(64))

    text: Mapped[str] = mapped_column(Text, nullable=False)
    lang: Mapped[str | None] = mapped_column(String(12))
    modality: Mapped[Modality] = mapped_column(
        Enum(Modality, name="modality", schema=SCHEMA_CORE), nullable=False
    )

    published_at: Mapped[datetime | None] = mapped_column()
    collected_at: Mapped[datetime] = mapped_column(nullable=False)

    rating_raw: Mapped[float | None] = mapped_column(Numeric(4, 2))
    # Mapped to 0..1 so a 5-star scale and a 10-point scale are comparable.
    rating_normalized: Mapped[float | None] = mapped_column(Numeric(4, 3))

    is_verified_owner: Mapped[bool | None] = mapped_column()
    helpful_votes: Mapped[int | None] = mapped_column(Integer)
    total_votes: Mapped[int | None] = mapped_column(Integer)

    # The two fields that make aspect-conditional credibility possible, and
    # which most review domains simply do not have.
    ownership_duration_months: Mapped[int | None] = mapped_column(SmallInteger)
    km_driven: Mapped[int | None] = mapped_column(Integer)

    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Filled by enrichment, nullable until then.
    spam_probability: Mapped[float | None] = mapped_column(Numeric(4, 3))
    credibility_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    source: Mapped[EvidenceSource] = relationship()
