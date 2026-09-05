"""The connector contract.

Every source implements three methods and nothing else. Everything a
connector would otherwise have to get right on its own, rate limiting,
backoff, robots checking, deduplication, checkpointing and telemetry, is
supplied by the framework. A connector that reimplements any of it is a
connector that will get one of them wrong.

    discover(seed) -> refs        what is there to fetch
    fetch(ref)     -> payload     get the bytes, politely
    parse(payload) -> drafts      turn bytes into Evidence Units

The resilience contract, from proposal section 14: a connector never fails
the pipeline. It fails itself, marks its source stale, and reports.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from revix_core.enums import Modality, SourceKind


@dataclass(frozen=True, slots=True)
class CatalogSeed:
    """What a connector is being asked to look for."""

    variant_id: str
    manufacturer: str
    model: str
    variant_name: str
    vehicle_class: str


@dataclass(frozen=True, slots=True)
class ExternalRef:
    """One thing worth fetching, as the source identifies it."""

    external_id: str
    url: str
    seed: CatalogSeed | None = None
    hint: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RawPayload:
    """Bytes exactly as received, before anyone tries to interpret them."""

    ref: ExternalRef
    body: bytes
    fetched_at: datetime
    http_status: int | None = None
    content_type: str | None = None

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.body).hexdigest()


@dataclass(slots=True)
class EvidenceUnitDraft:
    """A parsed piece of evidence, before it is given an identity in the database."""

    external_id: str
    text: str
    modality: Modality = Modality.TEXT
    url: str | None = None
    author_ref: str | None = None
    lang: str | None = None
    published_at: datetime | None = None
    rating_raw: float | None = None
    rating_scale_max: float | None = None
    is_verified_owner: bool | None = None
    helpful_votes: int | None = None
    total_votes: int | None = None
    ownership_duration_months: int | None = None
    km_driven: int | None = None
    # Which vehicle the source says this is about, in the source's own words.
    listing_title: str | None = None
    variant_hint: str | None = None
    model_hint: str | None = None

    @property
    def rating_normalized(self) -> float | None:
        """Map any rating scale onto 0..1 so a 5-star and a 10-point compare."""
        if self.rating_raw is None or not self.rating_scale_max:
            return None
        return round(max(0.0, min(1.0, self.rating_raw / self.rating_scale_max)), 3)

    def content_hash(self, source_key: str) -> str:
        """Identity by content, so the same text under a new id is not a new row.

        The source key is included because the same sentence appearing on two
        different platforms is two genuine observations, not a duplicate.
        """
        basis = f"{source_key}|{self.text.strip().casefold()}|{self.author_ref or ''}"
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()


@runtime_checkable
class Connector(Protocol):
    """What every source must implement."""

    source_key: str
    display_name: str
    kind: SourceKind
    base_url: str | None
    robots_policy: str | None
    rate_limit_rpm: int
    default_source_prior: float

    def discover(self, seed: CatalogSeed) -> Iterable[ExternalRef]: ...

    def fetch(self, ref: ExternalRef) -> RawPayload: ...

    def parse(self, raw: RawPayload) -> list[EvidenceUnitDraft]: ...


class ConnectorRegistry:
    """Every connector, by source key.

    A registry rather than imports scattered through the CLI, so that
    `revix ingest --source x` fails with a list of what does exist rather
    than an ImportError.
    """

    def __init__(self) -> None:
        self._connectors: dict[str, Connector] = {}

    def register(self, connector: Connector) -> Connector:
        if connector.source_key in self._connectors:
            raise ValueError(f"duplicate source_key: {connector.source_key}")
        self._connectors[connector.source_key] = connector
        return connector

    def get(self, source_key: str) -> Connector:
        try:
            return self._connectors[source_key]
        except KeyError:
            known = ", ".join(sorted(self._connectors)) or "none registered"
            raise KeyError(f"unknown source '{source_key}'. Known sources: {known}") from None

    def all(self) -> list[Connector]:
        return [self._connectors[k] for k in sorted(self._connectors)]

    def __contains__(self, source_key: object) -> bool:
        return source_key in self._connectors

    def __len__(self) -> int:
        return len(self._connectors)


registry = ConnectorRegistry()
