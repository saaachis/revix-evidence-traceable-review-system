"""Derived opinion, embeddings and weighting configurations.

Everything in this schema is recomputable from raw and core. If it were
dropped entirely, one full enrichment pass would rebuild it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from revix_core.enums import AspectKey
from revix_core.models.base import SCHEMA_ANALYSIS, SCHEMA_CORE, Base, TimestampMixin, uuid_pk

#: paraphrase-multilingual-MiniLM-L12-v2. Multilingual rather than English
#: only, because Indian owner reviews are heavily code-mixed.
EMBEDDING_DIM = 384


class EvidenceChunk(Base):
    __tablename__ = "evidence_chunk"
    __table_args__ = (
        UniqueConstraint("evidence_unit_id", "chunk_index"),
        # Approximate nearest neighbour. Built after the first bulk load, since
        # ivfflat wants data present before it can choose sensible lists.
        Index(
            "ix_evidence_chunk_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        {"schema": SCHEMA_ANALYSIS},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    evidence_unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_CORE}.evidence_unit.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Any] = mapped_column(Vector(EMBEDDING_DIM))


class AspectOpinion(Base):
    """One opinion, about one topic, extracted from one piece of evidence."""

    __tablename__ = "aspect_opinion"
    __table_args__ = (
        CheckConstraint("polarity >= -1 AND polarity <= 1", name="polarity_range"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        Index("ix_aspect_opinion_unit_aspect", "evidence_unit_id", "aspect_key"),
        {"schema": SCHEMA_ANALYSIS},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    evidence_unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_CORE}.evidence_unit.id", ondelete="CASCADE"), nullable=False
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA_ANALYSIS}.evidence_chunk.id", ondelete="SET NULL")
    )
    aspect_key: Mapped[AspectKey] = mapped_column(
        Enum(AspectKey, name="aspect_key", schema=SCHEMA_CORE, create_type=False), nullable=False
    )
    polarity: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    extracted_span: Mapped[str | None] = mapped_column(Text)


class EvalRun(Base, TimestampMixin):
    """One measurement of one component, kept so it can be plotted over time.

    Proposal section 18.4 asks for every metric to be written here and
    rendered publicly, including trend. A score that exists only in the log of
    the run that produced it cannot be compared with last week's, and
    "accuracy improved" is a claim rather than a fact until it can be.
    """

    __tablename__ = "eval_run"
    __table_args__ = (
        Index("ix_eval_run_component_time", "component", "created_at"),
        {"schema": SCHEMA_ANALYSIS},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    #: "aspect_extraction", "entity_resolution", "fusion", and so on.
    component: Mapped[str] = mapped_column(String(40), nullable=False)
    #: Which system produced it: "lexicon", "classifier", a fusion strategy.
    system: Mapped[str] = mapped_column(String(40), nullable=False)
    #: The commit, so a number on the metrics page can be traced to the code
    #: that produced it rather than to a date.
    git_sha: Mapped[str | None] = mapped_column(String(40))
    n_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: The headline figure, whatever that means for this component.
    primary_metric: Mapped[str] = mapped_column(String(40), nullable=False)
    primary_value: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    #: Everything else, including the per-aspect breakdown. JSONB because the
    #: shape genuinely differs per component and inventing a common one would
    #: be a schema fighting its own data.
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class FusionConfig(Base):
    """A named, versioned, hashable set of weighting parameters.

    Verdicts are keyed by this, which is the only reason the weighting switch
    in the interface is affordable: changing it is a lookup by
    (variant_id, fusion_config_id), never a recomputation.
    """

    __tablename__ = "fusion_config"
    __table_args__ = (
        UniqueConstraint("config_hash"),
        {"schema": SCHEMA_ANALYSIS},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # sha256 of the canonical JSON of params. Two configs with identical
    # parameters cannot both exist, which stops silent duplicates.
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column()
