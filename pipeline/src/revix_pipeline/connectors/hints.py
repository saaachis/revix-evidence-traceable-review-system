"""Reading ownership signals out of free text.

A review site hands you a "verified owner" flag and a distance field. Reddit
and YouTube hand you a paragraph. Section 12 of the proposal leans on
`ownership_duration_months` and `km_driven` heavily, and section 18.1 defines
the held-out gold set in terms of them, so on a platform that has no such
fields the only place they exist is in the sentence a person wrote.

Deliberately conservative. A hint that is wrong is worse than a hint that is
missing, because a missing hint merely excludes a unit from the gold set
whereas a wrong one puts a two-week impression into the pool of long-term
ownership that the strategies are being scored against.
"""

from __future__ import annotations

import re

# 45,000 km | 45000 kms | 45k kms | 1.2 lakh km | 90,000 kilometres
_KM = re.compile(
    r"(?<![\d.])(\d{1,3}(?:,\d{2,3})+|\d+(?:\.\d+)?)\s*(k|lakh|lac|l)?\s*"
    r"(?:km|kms|kilometer|kilometre|kilometers|kilometres)\b",
    re.IGNORECASE,
)

# 2 years | 18 months | 2.5 yrs | two years
#
# Words as well as digits, because an owner review is prose. "Bought it two
# years ago" is one of the commonest ways these reviews state an ownership
# period, and reading only digits discarded every one of them silently.
_WORD_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}
_DURATION = re.compile(
    r"(?<![\d.])(\d+(?:\.\d+)?|"
    + "|".join(sorted(_WORD_NUMBERS, key=len, reverse=True))
    + r")\s+(year|yr|yrs|years|month|months|mon|mos)\b",
    re.IGNORECASE,
)

# Only count a duration that is actually about owning the thing. "waited 2
# months for delivery" and "18 months warranty" are not ownership periods.
_OWNERSHIP_CONTEXT = re.compile(
    r"\b(own|owned|owning|ownership|had|have had|driving|driven|riding|ridden|"
    r"using|used|bought|purchased|"
    r"with (?:the|my|this) (?:car|bike|scooter|vehicle))\b",
    re.IGNORECASE,
)

_NOT_OWNERSHIP = re.compile(
    r"\b(warranty|waiting|waited|delivery|booked|booking|emi|loan|insurance|"
    r"service interval|free service)\b",
    re.IGNORECASE,
)

# Beyond these a number is far likelier to be a price, a typo or a joke than a
# reading off an odometer. India's highest-mileage taxis do reach 500,000 km,
# but one of those in the pool would distort the gold set on its own.
_MAX_KM = 500_000
_MAX_MONTHS = 30 * 12


def km_driven(text: str) -> int | None:
    """The largest distance the writer claims, or nothing.

    Largest rather than first, because "bought it at 5,000 km, now at 60,000"
    is describing one odometer and the useful number is the second one.
    """
    best: int | None = None
    for raw, unit in _KM.findall(text):
        value = float(raw.replace(",", ""))
        multiplier = {"k": 1_000, "lakh": 100_000, "lac": 100_000, "l": 100_000}
        if unit:
            value *= multiplier.get(unit.lower(), 1)
        if not (100 <= value <= _MAX_KM):
            continue
        km = round(value)
        if best is None or km > best:
            best = km
    return best


def ownership_months(text: str) -> int | None:
    """How long they say they have had it, in months.

    Requires an ownership word nearby and no contract word, so a warranty
    period or a waiting time is not mistaken for lived experience.
    """
    best: int | None = None
    for match in _DURATION.finditer(text):
        window = text[max(0, match.start() - 60) : match.end() + 60]
        if _NOT_OWNERSHIP.search(window) or not _OWNERSHIP_CONTEXT.search(window):
            continue
        raw = match.group(1).lower()
        value = float(_WORD_NUMBERS[raw]) if raw in _WORD_NUMBERS else float(raw)
        unit = match.group(2).lower()
        months = round(value * 12) if unit.startswith(("year", "yr")) else round(value)
        if not (1 <= months <= _MAX_MONTHS):
            continue
        if best is None or months > best:
            best = months
    return best


def looks_like_ownership_account(text: str) -> bool:
    """Whether the writer is speaking from ownership rather than opinion.

    Not a verified-owner flag and must never be stored as one. It is a weak
    textual signal, used only to prefer first-hand accounts when a platform
    offers no verification at all.
    """
    first_person = re.search(r"\b(i|my|we|our)\b", text, re.IGNORECASE) is not None
    return first_person and _OWNERSHIP_CONTEXT.search(text) is not None
