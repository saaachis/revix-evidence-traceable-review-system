"""Materialised verdicts. The only schema the API is allowed to read.

verdict_claim_evidence is the table the whole traceability argument rests on.
It is written by the fusion stage BEFORE any prose is generated, and the score
is computed from those rows. That ordering is what makes a citation impossible
to get wrong: it is not an annotation added afterwards, and no language model
is ever asked to produce one.
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
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from revix_core.enums import AspectKey
from revix_core.models.base import (
    SCHEMA_ANALYSIS,
    SCHEMA_CORE,
    SCHEMA_SERVING,
    Base,
    uuid_pk,
)


class Verdict(Base):
    __tablename__ = "verdict"
    __table_args__ = (
        # One verdict per variant per weighting strategy. The switch in the
        # interface moves between rows that already exist.
        UniqueConstraint("variant_id", "fusion_config_id"),
        CheckConstraint(
            "overall_score IS NULL OR (overall_score >= 0 AND overall_score <= 10)",
            name="overall_score_range",
        ),
        CheckConstraint(
            "confidence_low IS NULL OR confidence_high IS NULL "
            "OR confidence_low <= overall_score AND overall_score <= confidence_high",
            name="score_inside_interval",
        ),
        Index("ix_verdict_lookup", "variant_id", "fusion_config_id"),
        {"schema": SCHEMA_SERVING},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_CORE}.vehicle_variant.id", ondelete="CASCADE"), nullable=False
    )
    fusion_config_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_ANALYSIS}.fusion_config.id", ondelete="CASCADE"), nullable=False
    )
    computed_at: Mapped[datetime] = mapped_column(nullable=False)

    # Null when suppressed. A variant below the evidence floor gets a row that
    # records why, rather than no row at all, so the interface can explain.
    overall_score: Mapped[float | None] = mapped_column(Numeric(4, 2))
    confidence_low: Mapped[float | None] = mapped_column(Numeric(4, 2))
    confidence_high: Mapped[float | None] = mapped_column(Numeric(4, 2))

    is_suppressed: Mapped[bool] = mapped_column(default=False, nullable=False)
    suppression_reason: Mapped[str | None] = mapped_column(Text)

    evidence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Kish: (sum w)^2 / sum w^2. Two hundred low-weight reviews can carry a
    # smaller effective sample than thirty high-weight ones, which is why
    # weighting properly makes the interval wider rather than narrower.
    effective_sample_size: Mapped[float | None] = mapped_column(Numeric(8, 2))
    sources_used: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    aspects: Mapped[list[VerdictAspect]] = relationship(
        back_populates="verdict", cascade="all, delete-orphan"
    )
    claims: Mapped[list[VerdictClaim]] = relationship(
        back_populates="verdict", cascade="all, delete-orphan"
    )


class VerdictAspect(Base):
    __tablename__ = "verdict_aspect"
    __table_args__ = (
        UniqueConstraint("verdict_id", "aspect_key"),
        CheckConstraint(
            "divergence_index IS NULL OR (divergence_index >= 0 AND divergence_index <= 1)",
            name="divergence_range",
        ),
        {"schema": SCHEMA_SERVING},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    verdict_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_SERVING}.verdict.id", ondelete="CASCADE"), nullable=False
    )
    aspect_key: Mapped[AspectKey] = mapped_column(
        Enum(AspectKey, name="aspect_key", schema=SCHEMA_CORE, create_type=False), nullable=False
    )

    score: Mapped[float | None] = mapped_column(Numeric(4, 2))
    ci_low: Mapped[float | None] = mapped_column(Numeric(4, 2))
    ci_high: Mapped[float | None] = mapped_column(Numeric(4, 2))
    support_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # The weighted share of evidence disagreeing with the majority sign. This
    # is what the interface sorts on, rather than sorting by score.
    divergence_index: Mapped[float | None] = mapped_column(Numeric(4, 3))
    # Which characteristic best explains the disagreement, and the numbers
    # behind it: "71% explained by transmission, automatic 6.2, manual 8.8".
    top_covariate: Mapped[str | None] = mapped_column(String(40))
    covariate_explanation: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    verdict: Mapped[Verdict] = relationship(back_populates="aspects")


class VerdictClaim(Base):
    """Every assertable statement, as structured values rather than prose.

    The language model receives only these, with opaque identifiers, and never
    sees raw review text. Anything it writes is then checked against
    computed_values before it is allowed near a user.
    """

    __tablename__ = "verdict_claim"
    __table_args__ = {"schema": SCHEMA_SERVING}

    id: Mapped[uuid.UUID] = uuid_pk()
    verdict_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_SERVING}.verdict.id", ondelete="CASCADE"), nullable=False
    )
    claim_type: Mapped[str] = mapped_column(String(40), nullable=False)
    claim_template: Mapped[str] = mapped_column(String(60), nullable=False)
    computed_values: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    display_order: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)

    verdict: Mapped[Verdict] = relationship(back_populates="claims")
    evidence_links: Mapped[list[VerdictClaimEvidence]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )


class VerdictClaimEvidence(Base):
    """THE traceability table.

    One row per (claim, evidence unit) pair, carrying how much that unit
    contributed. The evidence drawer in the interface is a read of this table
    ordered by contribution_weight. Nothing else.
    """

    __tablename__ = "verdict_claim_evidence"
    __table_args__ = (
        UniqueConstraint("verdict_claim_id", "evidence_unit_id"),
        Index("ix_vce_claim_rank", "verdict_claim_id", "rank"),
        {"schema": SCHEMA_SERVING},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    verdict_claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_SERVING}.verdict_claim.id", ondelete="CASCADE"), nullable=False
    )
    evidence_unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA_CORE}.evidence_unit.id", ondelete="CASCADE"), nullable=False
    )
    contribution_weight: Mapped[float] = mapped_column(Numeric(6, 5), nullable=False)
    rank: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    claim: Mapped[VerdictClaim] = relationship(back_populates="evidence_links")
