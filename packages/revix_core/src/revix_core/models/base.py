"""Declarative base and column conventions.

Four schemas, split by lifecycle rather than by feature, per proposal
section 13:

    raw       immutable fetched payloads          append only
    core      canonical entities and evidence     slowly changing
    analysis  derived opinion and credibility     recomputable
    serving   materialised verdicts for the API   fully derived

The rule that makes this work: every table in analysis and serving must be
recomputable from raw and core alone. Nothing important is allowed to exist
only in a derived table.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SCHEMA_RAW = "raw"
SCHEMA_CORE = "core"
SCHEMA_ANALYSIS = "analysis"
SCHEMA_SERVING = "serving"

ALL_SCHEMAS = (SCHEMA_RAW, SCHEMA_CORE, SCHEMA_ANALYSIS, SCHEMA_SERVING)

# Predictable constraint names. Without this, Alembic autogenerate produces
# unnamed constraints that cannot be dropped in a downgrade.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_N_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    type_annotation_map = {
        dict[str, Any]: JSONB,
        list[str]: JSONB,
        datetime: DateTime(timezone=True),
    }


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def utcnow() -> datetime:
    """Timezone-aware now. Naive datetimes are a bug we do not want to debug later."""
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
