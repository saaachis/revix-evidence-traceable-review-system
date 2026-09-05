"""Running a connector, and writing down what happened.

The runner owns everything a connector must not: the raw store, deduplication,
the ingest_run record and failure isolation. A connector raising is a failed
run for that source and nothing more. Nothing it can do brings down the
pipeline.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from revix_core.enums import RunStatus
from revix_core.models import (
    EvidenceSource,
    EvidenceUnit,
    IngestRun,
    RawPayload,
    SourceListing,
    VehicleVariant,
    utcnow,
)
from revix_pipeline.connectors.base import (
    CatalogSeed,
    Connector,
    EvidenceUnitDraft,
)
from revix_pipeline.connectors.base import (
    RawPayload as RawPayloadDraft,
)
from revix_pipeline.connectors.politeness import CircuitOpenError, RobotsDisallowedError

log = logging.getLogger(__name__)


@dataclass(slots=True)
class RunResult:
    source_key: str
    status: RunStatus
    refs_discovered: int = 0
    payloads_fetched: int = 0
    units_inserted: int = 0
    units_skipped: int = 0
    error_count: int = 0
    last_error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status is RunStatus.SUCCEEDED


def ensure_source(session: Session, connector: Connector) -> EvidenceSource:
    """Register the connector in the database, or update its metadata."""
    source = session.scalar(
        select(EvidenceSource).where(EvidenceSource.source_key == connector.source_key)
    )
    if source is None:
        source = EvidenceSource(
            source_key=connector.source_key,
            display_name=connector.display_name,
            kind=connector.kind,
            base_url=connector.base_url,
            robots_policy=connector.robots_policy,
            rate_limit_rpm=connector.rate_limit_rpm,
            default_source_prior=connector.default_source_prior,
        )
        session.add(source)
        session.flush()
    else:
        source.display_name = connector.display_name
        source.robots_policy = connector.robots_policy
        source.rate_limit_rpm = connector.rate_limit_rpm
    return source


def seeds_for(session: Session, limit: int | None = None) -> list[CatalogSeed]:
    """Every variant in the catalogue, as something a connector can look for."""
    stmt = select(VehicleVariant).join(VehicleVariant.model).order_by(VehicleVariant.trim_code)
    if limit:
        stmt = stmt.limit(limit)
    seeds = []
    for variant in session.scalars(stmt):
        model = variant.model
        seeds.append(
            CatalogSeed(
                variant_id=str(variant.id),
                manufacturer=model.manufacturer.name,
                model=model.name,
                variant_name=variant.variant_name,
                vehicle_class=model.vehicle_class.value,
            )
        )
    return seeds


def run_connector(
    session: Session,
    connector: Connector,
    *,
    limit_variants: int | None = None,
    store_raw: bool = True,
) -> RunResult:
    """Discover, fetch, parse and persist. Never raises for source failures."""
    source = ensure_source(session, connector)
    run = IngestRun(source_id=source.id, status=RunStatus.RUNNING, started_at=utcnow())
    session.add(run)
    session.flush()

    result = RunResult(source_key=connector.source_key, status=RunStatus.RUNNING)

    # Existing identities, loaded once. Cheaper than a query per draft, and it
    # makes the dedupe decision explicit rather than relying on catching
    # IntegrityError halfway through a batch.
    seen_external = {
        row[0]
        for row in session.execute(
            select(EvidenceUnit.external_id).where(EvidenceUnit.source_id == source.id)
        )
    }
    seen_hashes = {row[0] for row in session.execute(select(EvidenceUnit.content_hash))}
    listings: dict[str, SourceListing] = {
        listing.external_id: listing
        for listing in session.scalars(
            select(SourceListing).where(SourceListing.source_id == source.id)
        )
    }

    try:
        for seed in seeds_for(session, limit=limit_variants):
            for ref in connector.discover(seed):
                result.refs_discovered += 1
                try:
                    payload = connector.fetch(ref)
                except (CircuitOpenError, RobotsDisallowedError) as exc:
                    # Both are the framework working as intended, not a bug.
                    result.error_count += 1
                    result.last_error = f"{type(exc).__name__}: {exc}"
                    if isinstance(exc, CircuitOpenError):
                        raise
                    continue
                except Exception as exc:
                    result.error_count += 1
                    result.last_error = f"{type(exc).__name__}: {exc}"
                    log.warning("fetch failed for %s: %s", ref.url, exc)
                    continue

                result.payloads_fetched += 1
                raw_id = None
                if store_raw:
                    raw_id = _store_raw(session, source.id, run.id, payload)

                for draft in connector.parse(payload):
                    listing = _ensure_listing(session, source.id, listings, draft)
                    digest = draft.content_hash(connector.source_key)
                    if draft.external_id in seen_external or digest in seen_hashes:
                        result.units_skipped += 1
                        continue
                    session.add(
                        EvidenceUnit(
                            source_id=source.id,
                            ingest_run_id=run.id,
                            raw_payload_id=raw_id,
                            external_id=draft.external_id,
                            url=draft.url,
                            author_ref=draft.author_ref,
                            text=draft.text,
                            lang=draft.lang,
                            modality=draft.modality,
                            published_at=draft.published_at,
                            collected_at=utcnow(),
                            rating_raw=draft.rating_raw,
                            rating_normalized=draft.rating_normalized,
                            is_verified_owner=draft.is_verified_owner,
                            helpful_votes=draft.helpful_votes,
                            total_votes=draft.total_votes,
                            ownership_duration_months=draft.ownership_duration_months,
                            km_driven=draft.km_driven,
                            content_hash=digest,
                            source_listing_id=listing.id if listing else None,
                            # variant_id stays null here on purpose. Deciding
                            # which vehicle this is about is the resolver's
                            # job, not the connector's, even when the source
                            # appears to tell us.
                            model_id=None,
                        )
                    )
                    seen_external.add(draft.external_id)
                    seen_hashes.add(digest)
                    result.units_inserted += 1

        result.status = RunStatus.SUCCEEDED

    except CircuitOpenError as exc:
        result.status = RunStatus.CIRCUIT_OPEN
        result.last_error = str(exc)
        log.warning("circuit open for %s, stopping this source", connector.source_key)
    except Exception as exc:
        result.status = RunStatus.FAILED
        result.error_count += 1
        result.last_error = f"{type(exc).__name__}: {exc}"
        log.exception("connector %s failed", connector.source_key)

    run.status = result.status
    run.finished_at = utcnow()
    run.refs_discovered = result.refs_discovered
    run.payloads_fetched = result.payloads_fetched
    run.units_inserted = result.units_inserted
    run.units_skipped = result.units_skipped
    run.error_count = result.error_count
    run.last_error = result.last_error
    session.flush()
    return result


def _store_raw(
    session: Session,
    source_id: uuid.UUID,
    run_id: uuid.UUID,
    payload: RawPayloadDraft,
) -> uuid.UUID:
    """Persist the payload before anything tries to interpret it.

    Deduplicated by sha256, so re-fetching an unchanged page costs one row
    lookup rather than another copy of the bytes.
    """
    digest = payload.sha256
    existing = session.scalar(select(RawPayload).where(RawPayload.sha256 == digest))
    if existing is not None:
        return existing.id
    row = RawPayload(
        source_id=source_id,
        ingest_run_id=run_id,
        url=payload.ref.url,
        fetched_at=payload.fetched_at,
        http_status=payload.http_status,
        content_type=payload.content_type,
        body=payload.body,
        sha256=digest,
    )
    session.add(row)
    session.flush()
    return row.id


def _ensure_listing(
    session: Session,
    source_id: uuid.UUID,
    cache: dict[str, SourceListing],
    draft: EvidenceUnitDraft,
) -> SourceListing | None:
    """One listing row per distinct title a source uses for a vehicle."""
    if not draft.listing_title:
        return None
    key = draft.listing_title.strip().casefold()
    listing = cache.get(key)
    if listing is None:
        listing = SourceListing(
            source_id=source_id,
            external_id=key,
            raw_title=draft.listing_title,
            raw_specs={"variant_hint": draft.variant_hint, "model_hint": draft.model_hint},
        )
        session.add(listing)
        session.flush()
        cache[key] = listing
    return listing
