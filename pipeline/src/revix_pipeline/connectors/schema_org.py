"""Reading schema.org Review markup, shared by the review-site connectors.

Indian review sites publish their reviews twice: once as HTML with hashed
class names that change on every deploy, and once as JSON-LD in a script tag
because search engines ask for it. The second is a contract nobody breaks
casually, so it is the one we read.

This module holds the parts that are the same wherever that markup appears.
The connectors hold the parts that are not: which URL to visit, how many
pages, what the site does and does not record.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

_LD_JSON = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE
)

#: Words a reviewer uses when they do mention which one they bought. Fuel and
#: gearbox first because they are the most commonly stated, then the trim
#: ladders the Indian market actually uses.
VARIANT_TOKENS = re.compile(
    r"(?<![\w])("
    # The bracketed trim first, and deliberately with no trailing \b on it: a
    # word boundary after ")" only matches when the next character is a word
    # character, so requiring one threw the bracket away and captured the
    # malformed token "sx(o". Every other alternative keeps its \b, so that
    # "petrolhead" is not read as "petrol".
    r"sx\s*\(\s*o\s*\)|"
    r"(?:diesel|petrol|cng|electric|hybrid|ev)\b|"
    r"(?:manual|automatic|amt|dct|cvt|ivt|dsg)\b|"
    r"(?:sx|zx\+?|zxi\+?|vxi\+?|lxi|sigma|delta|zeta|alpha|titanium|trend|ambiente)\b|"
    r"turbo\b|"
    # An engine size only counts when the writer says so. A bare decimal is
    # just as often a rating ("4.5") or a dimension, and reading those as
    # trims produced listings like "Tata Nexon 6.2" that resolve to nothing.
    r"\d\.\d(?=\s*(?:l\b|litre|liter|turbo|petrol|diesel|engine))"
    r")",
    re.IGNORECASE,
)


def reviews_in(html: str) -> list[dict[str, Any]]:
    """Every schema.org Review in the page's JSON-LD blocks."""
    found: list[dict[str, Any]] = []
    for block in _LD_JSON.findall(html):
        try:
            data = json.loads(block)
        except ValueError:
            # One malformed block should not cost us the others.
            continue
        for item in data if isinstance(data, list) else [data]:
            if not isinstance(item, dict):
                continue
            reviews = item.get("review")
            if isinstance(reviews, dict):
                reviews = [reviews]
            if not isinstance(reviews, list):
                continue
            found.extend(r for r in reviews if isinstance(r, dict))
    return found


def rating_of(review: dict[str, Any], *, scale_max: float = 5.0) -> float | None:
    """The numeric rating, if there is a usable one."""
    rating = review.get("reviewRating")
    if not isinstance(rating, dict):
        return None
    try:
        value = float(rating.get("ratingValue"))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return value if 0.0 <= value <= scale_max else None


def author_of(review: dict[str, Any], placeholders: frozenset[str]) -> str | None:
    """The reviewer's name, unless the site used a placeholder for it.

    "user" and "Anonymous" are what these sites show for a review posted
    without a display name. Treating one as an author identity would pool
    thousands of strangers into a single reputation.
    """
    author = review.get("author")
    if not isinstance(author, dict):
        return None
    name = str(author.get("name") or "").strip()
    return name if name and name not in placeholders else None


def variant_tokens(text: str) -> str:
    """The trim, fuel and gearbox words the reviewer used, in order, deduped."""
    seen: list[str] = []
    for match in VARIANT_TOKENS.finditer(text):
        # Whitespace inside a bracketed trim is normalised away, so "SX ( O )"
        # and "SX(O)" resolve to the same listing rather than to two.
        token = re.sub(r"\s+", "", match.group(1)).lower()
        if token not in seen:
            seen.append(token)
    return " ".join(seen)


def listing_title(model_label: str, text: str) -> str:
    """What this review says it is about, in the source's own words.

    One listing per distinct combination, so a review that names a trim gets
    its own resolution decision instead of being lumped in with every other
    review of the model and resolved all or nothing.
    """
    tokens = variant_tokens(text)
    return f"{model_label} {tokens}".strip() if tokens else model_label


def review_id(url: str, title: str, body: str) -> str:
    """A stable identity, because these sites do not publish one.

    Derived from the content, so re-reading the page tomorrow recognises the
    same review rather than inserting it again. The URL is included without
    its query string, so a review does not change identity when it moves from
    page 3 to page 4 as newer reviews arrive above it.
    """
    basis = f"{url.split('?')[0]}|{title}|{body[:400]}".casefold()
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:32]


def slug(name: str) -> str:
    """Their URL form: lowercase, hyphenated, punctuation dropped."""
    cleaned = re.sub(r"[^a-z0-9\s-]", "", name.casefold())
    return re.sub(r"[\s-]+", "-", cleaned).strip("-")
