"""The raw-store recovery path, run last because it empties the store.

``db reset-raw`` is the break-glass command for a database so full the ordinary
sweep cannot even record its own deletes: it lifts the foreign key, truncates
raw.raw_payload, nulls the dangling pointers and puts the constraint back. It
is destructive by design, so this module is named to sort after every other
test and leaves nothing behind it that still needs the raw payloads.

Evidence, verdicts and citations must survive it; only the stored HTTP goes.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text
from typer.testing import CliRunner

from revix_pipeline.cli import app

pytestmark = pytest.mark.db

runner = CliRunner()


def _count(engine: Engine, sql: str) -> int:
    # A short-lived connection that closes before the command runs. reset-raw
    # takes an ACCESS EXCLUSIVE lock to drop the foreign key, so holding any
    # open transaction on core.evidence_unit here would deadlock against it.
    with engine.connect() as conn:
        return int(conn.execute(text(sql)).scalar_one())


def test_reset_raw_requires_confirmation(engine: Engine) -> None:
    result = runner.invoke(app, ["db", "reset-raw"])
    assert result.exit_code == 1
    assert "--yes" in result.output


def test_reset_raw_empties_the_store_but_keeps_the_evidence(engine: Engine) -> None:
    evidence_before = _count(engine, "select count(*) from core.evidence_unit")

    result = runner.invoke(app, ["db", "reset-raw", "--yes"])
    assert result.exit_code == 0, result.output
    assert "emptied" in result.output

    assert _count(engine, "select count(*) from raw.raw_payload") == 0
    assert _count(engine, "select count(*) from core.evidence_unit") == evidence_before, (
        "the evidence is the product, not the receipt"
    )
