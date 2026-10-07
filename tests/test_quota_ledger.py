"""The API quota ledger, persisted so a budget survives the process that spent it.

test_quota covers the day boundary and the in-memory budget. This covers the
database side: a spend is recorded against the provider's quota day and read
back, which is what stops a second run of the night from spending a budget the
first already used up.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from revix_pipeline.connectors.quota import record_spend, spent_today

pytestmark = pytest.mark.db


def test_a_fresh_source_has_spent_nothing(session: Session) -> None:
    assert spent_today(session, "youtube") == 0


def test_spends_accumulate_within_a_day(session: Session) -> None:
    assert record_spend(session, "youtube", 100) == 100
    assert record_spend(session, "youtube", 50) == 150
    assert spent_today(session, "youtube") == 150


def test_a_non_positive_spend_is_a_no_op_read(session: Session) -> None:
    record_spend(session, "youtube", 100)
    # Zero units must not create or move the tally, only report it.
    assert record_spend(session, "youtube", 0) == 100
