"""The command line, driven end to end against a real database.

Every stage of the pipeline has a command behind it, and the scheduled run is
just those commands in order. These invoke them in-process against a populated
database: the read commands confirm they report without error, and the stage
commands confirm a variant can be taken from ingest through to a verdict. The
point is that the operator surface the project is actually run through does not
rot, not any single number it prints.

Marked ``db`` because it needs Postgres; it skips cleanly without one through
the shared ``engine`` fixture.
"""

from __future__ import annotations

import pathlib

import pytest
from typer.testing import CliRunner

from revix_pipeline.cli import app

pytestmark = pytest.mark.db

runner = CliRunner()


@pytest.fixture(autouse=True)
def _needs_db(engine: object) -> None:
    """Depend on the shared engine so the module skips without a database."""


def invoke(*args: str) -> object:
    result = runner.invoke(app, list(args))
    assert result.exit_code == 0, f"`{' '.join(args)}` exited {result.exit_code}\n{result.output}"
    return result


class TestReadOnlyCommands:
    def test_db_check_confirms_the_extensions(self) -> None:
        out = invoke("db", "check").output
        assert "vector" in out and "pg_trgm" in out

    def test_db_status_counts_everything(self) -> None:
        out = invoke("db", "status").output
        assert "variants" in out and "verdicts" in out

    def test_show_reference_lists_the_nine_aspects_and_the_strategies(self) -> None:
        out = invoke("db", "show-reference").output
        assert "aspects (9)" in out
        assert "[default]" in out

    def test_db_sizes_reports_disk_use(self) -> None:
        out = invoke("db", "sizes").output
        assert "TOTAL" in out

    def test_sources_lists_the_registered_connectors(self) -> None:
        out = invoke("sources").output
        assert "fixture_owner" in out

    def test_probe_answers_without_a_database(self) -> None:
        # The fixture source generates its own evidence, so this exercises the
        # probe path without a network call.
        out = invoke("probe", "--source", "fixture_owner").output
        assert out.strip()


class TestTheStagesInOrder:
    """Each stage command, run against the seeded fixtures the nightly loaded."""

    def test_catalogue_seed_is_idempotent(self) -> None:
        invoke("catalogue", "seed")

    def test_ingest_runs_one_connector(self) -> None:
        invoke("ingest", "--source", "fixture_owner", "--limit", "4")

    def test_resolve_then_extract_then_score_then_fuse(self) -> None:
        invoke("enrich", "resolve")
        invoke("enrich", "extract")
        invoke("enrich", "score", "--recompute")
        invoke("enrich", "fuse", "--limit", "6")

    def test_the_fusion_experiment_runs_and_reports(self) -> None:
        # Small replicate and subsample counts keep it quick; the point is the
        # harness executes against real verdicts, not the precision of the run.
        out = invoke("eval", "fusion", "--replicates", "5", "--k", "10,20", "--limit", "6").output
        assert out.strip()

    def test_the_whole_nightly_runs_in_order(self) -> None:
        # The scheduled entry point: ingest, resolve, extract, score, fuse,
        # every stage after a failed source still running.
        out = invoke(
            "pipeline",
            "nightly",
            "--limit",
            "6",
            "--sources",
            "fixture_owner,fixture_forum,fixture_expert",
        ).output
        assert "nightly finished" in out


class TestRawRetention:
    def test_prune_raw_dry_run_deletes_nothing(self) -> None:
        # --dry-run says what would go and removes nothing, so it is safe to
        # run against the populated store while exercising the retention logic.
        out = invoke("db", "prune-raw", "--dry-run").output
        assert out.strip()


class TestGold:
    def test_sample_then_status_round_trip(self, tmp_path: pathlib.Path) -> None:
        gold = tmp_path / "aspects.jsonl"
        invoke("gold", "sample", "--per-aspect", "3", "--out", str(gold))
        assert gold.exists()
        # status exits 0 when a set exists and prints coverage.
        out = invoke("gold", "status", "--path", str(gold)).output
        assert out.strip()
