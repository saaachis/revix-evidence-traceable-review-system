"""How many times each stage talks to the database.

Against a local Postgres a round trip is free and none of this matters.
Against Neon it is most of a second per hundred, and it was the whole of a
22 minute nightly: entity resolution alone spent nine minutes issuing 704
lazy loads of the same sixteen vehicle models, one per variant per listing.

So these tests count statements rather than measuring time. The count is what
predicts the deployed behaviour, and unlike a timing assertion it does not
turn a slow morning into a red build.

The bounds are deliberately loose. They are here to catch an N+1 creeping
back, not to freeze the query plan.
"""

from __future__ import annotations

import re
from collections import Counter

import pytest
from sqlalchemy import event, update
from sqlalchemy.orm import Session

from revix_core.db import get_engine
from revix_core.models import EvidenceUnit, SourceListing
from revix_pipeline.enrichment.fuse import fuse_all
from revix_pipeline.enrichment.resolve import resolve_listings

pytestmark = pytest.mark.db


class StatementCounter:
    """Every statement the engine sends while this is active."""

    def __init__(self) -> None:
        self.by_kind: Counter[str] = Counter()

    def __enter__(self) -> StatementCounter:
        event.listen(get_engine(), "before_cursor_execute", self._record)
        return self

    def __exit__(self, *exc: object) -> None:
        event.remove(get_engine(), "before_cursor_execute", self._record)

    def _record(
        self, conn: object, cursor: object, statement: str, *args: object, **kwargs: object
    ) -> None:
        verb = statement.strip().split()[0].upper()
        table = (
            m.group(1) if (m := re.search(r"(?:FROM|INTO|UPDATE)\s+([\w.]+)", statement)) else ""
        )
        self.by_kind[f"{verb} {table}"] += 1

    @property
    def total(self) -> int:
        return sum(self.by_kind.values())


def test_resolution_reads_the_catalogue_once_not_once_per_listing(session: Session) -> None:
    """The N+1 that cost nine minutes: variant.model, lazily, in a loop."""
    session.execute(
        update(SourceListing).values(
            variant_id=None, model_id=None, match_method=None, match_confidence=None
        )
    )
    session.execute(update(EvidenceUnit).values(variant_id=None, model_id=None))
    session.flush()

    with StatementCounter() as counter:
        resolve_listings(session)

    models_read = counter.by_kind.get("SELECT core.vehicle_model", 0)
    variants_read = counter.by_kind.get("SELECT core.vehicle_variant", 0)
    assert models_read <= 2, f"the catalogue is being reread per listing: {counter.by_kind}"
    assert variants_read <= 2, f"the catalogue is being reread per listing: {counter.by_kind}"


def test_resolution_propagates_in_bulk_rather_than_row_by_row(session: Session) -> None:
    """One UPDATE per evidence unit was 3,696 round trips on a real run."""
    session.execute(
        update(SourceListing).values(
            variant_id=None, model_id=None, match_method=None, match_confidence=None
        )
    )
    session.execute(update(EvidenceUnit).values(variant_id=None, model_id=None))
    session.flush()

    with StatementCounter() as counter:
        resolve_listings(session)

    updates = counter.by_kind.get("UPDATE core.evidence_unit", 0)
    assert updates <= 4, f"units are being updated one at a time: {updates}"


def test_a_variant_is_read_once_and_weighted_per_strategy(session: Session) -> None:
    """The query does not depend on the strategy, so it should not repeat."""
    with StatementCounter() as counter:
        stats = fuse_all(session)

    reads = counter.by_kind.get("SELECT analysis.aspect_opinion", 0)
    assert reads <= stats["variants"], (
        f"{reads} reads for {stats['variants']} variants: the evidence is being "
        "fetched once per strategy instead of once per variant"
    )
