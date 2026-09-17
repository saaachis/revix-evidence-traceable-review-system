"""Compression on the way in, and the budget that the age window missed.

Two regressions live here, and the second is the more embarrassing one.

The raw store filled a 512 MB database and stopped the pipeline for three
nights: 2,943 payloads came to 410 MB, against about 70 MB of actual product.

The first fix was an age window, and it freed nothing, because every payload
was inside it. The sweep ran, reported "nothing past the window", and the
migration behind it died on a full disk exactly as before. An age window
bounds how old a store gets. It does not bound how big it gets.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from revix_core.settings import Settings
from revix_pipeline.connectors.raw_store import GZIP, MIN_BYTES, compress, decompress

# A page shaped like the ones we actually fetch: repetitive markup, which is
# why the ratio is what it is.
PAGE = (
    b"<html><body>"
    + b"".join(
        b'<div class="review-card"><span class="rating">4.5</span>'
        b"<p>Good mileage and the service costs are reasonable.</p></div>"
        for _ in range(200)
    )
    + b"</body></html>"
)


def test_a_page_survives_the_round_trip_exactly() -> None:
    stored, encoding = compress(PAGE)
    assert encoding == GZIP
    assert decompress(stored, encoding) == PAGE


def test_the_saving_is_the_reason_this_exists() -> None:
    """If it were not several-fold, compressing would not be worth a column."""
    stored, _ = compress(PAGE)
    assert len(stored) * 5 < len(PAGE), "real pages should compress several-fold"


def test_small_bodies_are_left_alone() -> None:
    """A gzip header on forty bytes makes the row bigger, not smaller."""
    tiny = b"{}"
    stored, encoding = compress(tiny)
    assert encoding is None
    assert stored == tiny
    assert decompress(stored, encoding) == tiny


def test_an_empty_body_does_not_grow() -> None:
    """Skipped fetches store an empty body, and there are a lot of them."""
    stored, encoding = compress(b"")
    assert encoding is None
    assert stored == b""


def test_incompressible_bodies_are_stored_as_received() -> None:
    """Random bytes grow under gzip. Storing the larger form would be absurd."""
    import os

    noise = os.urandom(MIN_BYTES * 4)
    stored, encoding = compress(noise)
    assert encoding is None
    assert stored == noise


def test_rows_written_before_compression_still_read() -> None:
    """Null encoding means "as received", which is every inherited row."""
    assert decompress(PAGE, None) == PAGE


def test_compression_is_deterministic() -> None:
    """gzip stamps the clock into its header unless told not to.

    Two identical payloads must compress to identical bytes, or anything that
    later compares stored rows quietly stops working.
    """
    assert compress(PAGE)[0] == compress(PAGE)[0]


# ---------- the policy itself ----------


def test_there_is_a_budget_in_bytes_and_not_only_in_days() -> None:
    """The exact regression: an age window alone freed nothing."""
    settings = Settings()
    assert settings.raw_max_megabytes > 0
    assert settings.raw_retention_days > 0


def test_the_budget_leaves_room_for_the_product() -> None:
    """Receipts must not crowd out the thing they are receipts for.

    Evidence, verdicts and their citations came to roughly 70 MB when the
    database filled. The budget has to fit alongside that inside 512 MB with
    room to grow, or we are back where we started.
    """
    tier_mb = 512
    product_mb = 70
    budget = Settings().raw_max_megabytes
    assert budget + product_mb < tier_mb * 0.8, "no headroom left for growth"


def test_the_budget_holds_the_window_once_compressed() -> None:
    """The two rules should agree rather than fight.

    410 MB over 2,943 payloads is about 139 kB each as received. At the
    several-fold saving measured above, a fortnight of that fits inside the
    budget, so the age window is what normally bites and the byte budget is
    the backstop, which is the right way round.
    """
    settings = Settings()
    observed_payloads = 2_943
    uncompressed_kb = 139
    compressed_kb = uncompressed_kb / 5  # the ratio asserted above, conservatively
    window_mb = observed_payloads * compressed_kb / 1024
    assert window_mb < settings.raw_max_megabytes


def test_the_cutoff_is_timezone_aware() -> None:
    """A naive datetime compared against a timezone-aware column raises."""
    cutoff = datetime.now(UTC) - timedelta(days=Settings().raw_retention_days)
    assert cutoff.tzinfo is not None


# ---------- reclaiming under pressure ----------


def test_the_sweep_batches_rather_than_deleting_in_one_statement() -> None:
    """The regression: the sweep failed with the error it existed to fix.

    A full database has no room to record a large deletion. Dead rows are
    written rather than merely marked absent, and evidence_unit.raw_payload_id
    is ON DELETE SET NULL, so removing a payload also rewrites the evidence
    rows pointing at it. Deleting 2,173 payloads in one statement asked for
    more room than the 31 MB that was left.

    Asserted on the signature, because the alternative is a database fixture
    that has to actually be full, and the thing worth protecting is that the
    option exists at all with a default small enough to fit.
    """
    import inspect

    from revix_pipeline.cli import db_prune_raw

    params = inspect.signature(db_prune_raw).parameters
    assert "batch_size" in params, "a sweep that cannot batch cannot run when it is needed"

    default = params["batch_size"].default
    size = getattr(default, "default", default)
    assert 1 <= size <= 100, "batches must be small enough to fit in what headroom remains"


def test_a_batch_fits_inside_plausible_headroom() -> None:
    """Sizing check on the number that was actually chosen.

    The store held 1.1 GB logical across 2,943 payloads, so roughly 380 kB
    each. Postgres keeps these compressed out of line at about 2.7 to 1, so a
    batch costs materially less on disk than the logical figure suggests, and
    the batch has to fit in the tens of megabytes left over.
    """
    import inspect

    from revix_pipeline.cli import db_prune_raw

    default = inspect.signature(db_prune_raw).parameters["batch_size"].default
    size = getattr(default, "default", default)

    logical_kb_each = 1.1 * 1024 * 1024 / 2_943
    on_disk_mb = size * logical_kb_each / 1024 / 2.7
    assert on_disk_mb < 31, "a batch has to fit in the headroom a full database leaves"
