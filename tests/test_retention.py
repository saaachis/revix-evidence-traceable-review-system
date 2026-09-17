"""The retention window, and the arithmetic that should have warned us.

The raw store grew without a ceiling until it filled a 512 MB database and
stopped the pipeline for three nights. Nothing in the codebase was wrong in
the sense of a bug; there was simply no policy, and no number anywhere that
would have gone red before the database did.

These are cheap assertions about the size of the thing, which is the class of
check that was missing rather than the class that failed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from revix_core.settings import Settings


def test_a_retention_window_exists_at_all() -> None:
    """The regression is "nobody set one", so assert one is set."""
    assert Settings().raw_retention_days > 0


def test_the_window_covers_the_loop_it_exists_for() -> None:
    """Notice a parser is wrong, fix it, replay.

    That round trip is days, not hours, so a window shorter than a week would
    make the raw store useless for the one job it has. Longer than a month and
    we are back to storing everything forever with extra steps.
    """
    days = Settings().raw_retention_days
    assert 7 <= days <= 31


def test_the_cutoff_is_in_the_past_and_timezone_aware() -> None:
    """A naive datetime compared against a timezone-aware column raises."""
    days = Settings().raw_retention_days
    cutoff = datetime.now(UTC) - timedelta(days=days)
    assert cutoff.tzinfo is not None
    assert cutoff < datetime.now(UTC)


def test_unbounded_growth_would_have_exhausted_the_tier() -> None:
    """Why this broke when it did, pinned as arithmetic.

    A YouTube comment-thread response runs to tens of kilobytes and there are
    hundreds of videos a night; review-site HTML is heavier still. Content
    that is byte-identical deduplicates on its hash, but a page that gained a
    single comment is a new payload, so a nightly run adds rather than
    replaces. At a conservative 30 MB a night, a 512 MB tier is gone inside
    three weeks, which is roughly what happened.
    """
    nightly_mb = 30
    tier_mb = 512
    assert nightly_mb * 30 > tier_mb, "a month of unbounded growth overruns the tier"

    # With the window, the store holds at most the window's worth.
    held_mb = nightly_mb * Settings().raw_retention_days
    assert held_mb < tier_mb, "the retained window has to fit, with room for the real data"


def test_the_window_leaves_room_for_everything_else() -> None:
    """The raw store is the receipt. The evidence is the product.

    Whatever the window is, it must not be sized so that raw payloads crowd
    out the tables the site actually serves from.
    """
    nightly_mb = 30
    tier_mb = 512
    raw_share = nightly_mb * Settings().raw_retention_days / tier_mb
    assert raw_share < 0.9, "raw payloads must not own the whole database"
