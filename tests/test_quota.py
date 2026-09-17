"""The quota day, and the budget that has to survive a process ending.

These are the rules that were wrong in production: a budget that reset every
run, and a day boundary drawn in the wrong timezone. Both are cheap to assert
and neither is visible from the outside until a provider starts refusing.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from revix_pipeline.connectors.quota import DEFAULT_QUOTA_TIMEZONE, quota_day
from revix_pipeline.connectors.youtube import YouTubeConnector


def test_the_nightly_falls_on_the_previous_pacific_day() -> None:
    """The exact case that made the ledger necessary.

    The nightly runs at 00:13 UTC, which is the previous afternoon in
    California. Counting it against the UTC date would put two consecutive
    nightlies on the same quota day when Google puts them on different ones.
    """
    nightly = datetime(2026, 9, 7, 0, 13, tzinfo=UTC)
    assert quota_day("youtube", nightly) == date(2026, 9, 6)


def test_hand_triggered_runs_share_a_day_with_the_nightly() -> None:
    """Six runs on one Google day is what actually exhausted the quota."""
    same_day = [
        datetime(2026, 9, 6, 7, 46, tzinfo=UTC),
        datetime(2026, 9, 6, 17, 28, tzinfo=UTC),
        datetime(2026, 9, 7, 0, 13, tzinfo=UTC),
    ]
    assert {quota_day("youtube", t) for t in same_day} == {date(2026, 9, 6)}


def test_the_pacific_day_turns_over_at_local_midnight() -> None:
    # 06:59 UTC is 23:59 the previous day in California; 07:01 is 00:01.
    assert quota_day("youtube", datetime(2026, 9, 7, 6, 59, tzinfo=UTC)) == date(2026, 9, 6)
    assert quota_day("youtube", datetime(2026, 9, 7, 7, 1, tzinfo=UTC)) == date(2026, 9, 7)


def test_an_unmapped_source_falls_back_to_utc() -> None:
    """A guess, but a stated one, and wrong by at most an offset."""
    assert DEFAULT_QUOTA_TIMEZONE is not None
    moment = datetime(2026, 9, 7, 23, 30, tzinfo=UTC)
    assert quota_day("some-other-api", moment) == date(2026, 9, 7)


def test_the_budget_refuses_once_it_is_seeded_as_spent() -> None:
    """The whole point: a run that starts already spent must not spend again."""
    connector = YouTubeConnector(daily_quota=10_000)
    connector.quota_spent = 9_950  # as the runner would seed it

    assert connector._spend(100) is False, "a search we cannot afford"
    assert connector._spend(1) is True, "a comment page we can"
    assert connector.quota_spent == 9_951


def test_a_fresh_process_still_has_the_whole_budget() -> None:
    connector = YouTubeConnector(daily_quota=10_000)
    assert connector.quota_spent == 0
    assert connector._spend(100) is True
    assert connector.quota_spent == 100


def test_the_budget_warns_once_rather_than_per_call(caplog) -> None:  # type: ignore[no-untyped-def]
    """Silence here is how a spent budget gets mistaken for a broken source."""
    connector = YouTubeConnector(daily_quota=100)
    connector.quota_spent = 100

    with caplog.at_level("WARNING"):
        for _ in range(5):
            connector._spend(100)

    warnings = [r for r in caplog.records if "quota budget reached" in r.message]
    assert len(warnings) == 1, "said once a run, not once a call"


def test_the_catalogue_now_costs_more_than_one_run_of_headroom() -> None:
    """Why this broke when it did, pinned as arithmetic.

    Searches are per model and cost 100; each video's comment page costs 1.
    At 42 models and 16 videos that is 4,872 units a run, so two runs fit
    inside the 10,000 a day and the third does not. The connector comment
    claiming 2,784 was written when the catalogue held 24 models, and
    expanding the catalogue to 42 is what quietly ate the headroom that used
    to leave room for three runs.
    """
    models, videos, daily = 42, 16, 10_000
    per_run = models * 100 + models * videos * 1

    assert per_run == 4_872
    assert per_run * 2 < daily, "two runs still fit"
    assert per_run * 3 > daily, "the third does not, which is why the ledger exists"
    # Six ran on 6 September, which is where the 403s came from.
    assert per_run * 6 > daily * 2.9
