"""Remembering what a metered API has already been asked for today.

A connector's own quota counter lives for the length of one process, which is
exactly as long as it is useful and no longer. Run the pipeline twice on the
same day and the second run starts from zero, spends the allowance again, and
the provider, who has been counting properly the whole time, starts refusing.

So the counter is kept here instead, keyed to the provider's reset day rather
than ours.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from revix_core.models import ApiQuotaLedger

#: Where each provider's quota day turns over. Google resets YouTube Data API
#: quota at midnight Pacific, and our nightly runs at 00:13 UTC, which is the
#: previous afternoon in California. Two consecutive nightlies therefore fall
#: on the same Google day roughly never, and on the same UTC day always, so
#: using a UTC date would draw the boundary in the wrong place.
QUOTA_TIMEZONES = {
    "youtube": ZoneInfo("America/Los_Angeles"),
}

#: For a source we have not mapped, UTC is a defensible guess and is at worst
#: off by the length of one timezone offset.
DEFAULT_QUOTA_TIMEZONE = ZoneInfo("UTC")


def quota_day(source_key: str, now: datetime | None = None) -> date:
    """The provider's current quota day, in the provider's own timezone."""
    tz = QUOTA_TIMEZONES.get(source_key, DEFAULT_QUOTA_TIMEZONE)
    moment = now.astimezone(tz) if now else datetime.now(tz)
    return moment.date()


def spent_today(session: Session, source_key: str, *, now: datetime | None = None) -> int:
    """How many units this source has already spent on the current quota day."""
    row = session.scalar(
        select(ApiQuotaLedger).where(
            ApiQuotaLedger.source_key == source_key,
            ApiQuotaLedger.quota_date == quota_day(source_key, now),
        )
    )
    return row.units_spent if row else 0


def record_spend(
    session: Session, source_key: str, units: int, *, now: datetime | None = None
) -> int:
    """Add to today's tally and return the new total.

    Called after a run rather than per request. A crash mid-run therefore
    loses that run's accounting, which is the safe direction to be wrong in
    only because the provider is still counting: the next run under-estimates
    what is left, spends less than it could, and nothing is refused. Charging
    up front would have the opposite failure, where a crash makes us think we
    spent quota we never did.
    """
    if units <= 0:
        return spent_today(session, source_key, now=now)

    today = quota_day(source_key, now)
    row = session.scalar(
        select(ApiQuotaLedger).where(
            ApiQuotaLedger.source_key == source_key,
            ApiQuotaLedger.quota_date == today,
        )
    )
    if row is None:
        row = ApiQuotaLedger(source_key=source_key, quota_date=today, units_spent=0)
        session.add(row)
    row.units_spent += units
    session.flush()
    return row.units_spent
