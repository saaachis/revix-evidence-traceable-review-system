"""CarDekho and BikeDekho owner reviews, from the structured data they publish.

The first source in this project that produces real Indian owner reviews, and
the first that carries a star rating, which neither Reddit nor YouTube has.

We read the schema.org `Review` objects in the page's JSON-LD block. That is
markup a site publishes specifically so machines can read it, which makes this
the most durable thing on the page: the surrounding HTML uses hashed class
names that change on every deploy, while the JSON-LD is a contract with search
engines that nobody breaks casually. Both hosts permit these paths in
robots.txt, checked before any of this was written. ZigWheels does not, and is
therefore absent. See ADR 0008.

The honest limitation, and it decides what this source can and cannot do: a
review here is about a MODEL, not a variant. CarDekho does not ask which trim
you bought. So most units from this source will not resolve to a variant and
will sit unresolved, and the ones that do resolve do so because the reviewer
happened to write "SX(O) diesel" in their own words. We measure that rate
rather than guessing at it, and we never spread a model-level review across
every variant of the model, which would attribute a turbo owner's complaint to
someone who bought the base manual.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from revix_core.enums import Modality, SourceKind
from revix_pipeline.connectors.base import (
    CatalogSeed,
    EvidenceUnitDraft,
    ExternalRef,
    RawPayload,
)
from revix_pipeline.connectors.hints import km_driven, ownership_months
from revix_pipeline.connectors.politeness import PoliteClient

CAR_HOST = "https://www.cardekho.com"
BIKE_HOST = "https://www.bikedekho.com"

#: Deliberately slow. Nothing here is urgent, these are somebody else's servers,
#: and one page per model means the whole catalogue costs a couple of hundred
#: requests a night.
RATE_LIMIT_RPM = 10

#: Their reviews run short. A single line still carries a rating, but not
#: enough language for the aspect extractor to find anything in.
MIN_BODY_CHARS = 60

_LD_JSON = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE
)

#: Words a reviewer uses when they do mention which one they bought. Fuel and
#: gearbox first because they are the most commonly stated, then the trim
#: ladders the Indian market actually uses.
_VARIANT_TOKENS = re.compile(
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
    # An engine size only counts when the writer says so. A bare decimal
    # is just as often a rating ("4.5") or a dimension, and reading those
    # as trims produced listings like "Tata Nexon 6.2" that resolve to
    # nothing and pollute the listing table.
    r"\d\.\d(?=\s*(?:l\b|litre|liter|turbo|petrol|diesel|engine))"
    r")",
    re.IGNORECASE,
)


class DekhoConnector:
    """One page per model, thirty reviews a page, both hosts."""

    source_key = "cardekho"
    display_name = "CarDekho and BikeDekho owner reviews"
    # Self-declared owners on a review site. Not verified, but people are
    # writing about a car they say they bought, which is a different act from
    # commenting under a video.
    kind = SourceKind.OWNER_REVIEW
    base_url: str | None = CAR_HOST
    robots_policy: str | None = "robots.txt permits these paths, checked 2026-09-06; 10 rpm"
    rate_limit_rpm = RATE_LIMIT_RPM
    #: Above the anonymous sources and below an expert publication. A star
    #: rating and a named account are worth something; the absence of any
    #: ownership verification caps it.
    default_source_prior = 0.65

    def __init__(self) -> None:
        self._client: PoliteClient | None = None
        # One connector instance serves one run, because the CLI is a fresh
        # process each time. Six Creta variants would otherwise fetch the same
        # model page six times for the same thirty reviews.
        self._seen_urls: set[str] = set()

    def _http(self) -> PoliteClient:
        if self._client is None:
            self._client = PoliteClient(
                self.source_key,
                rate_limit_rpm=self.rate_limit_rpm,
                # Unauthenticated fetches of ordinary pages, so robots applies
                # in full, unlike the credentialed API connectors.
                respect_robots=True,
            )
        return self._client

    # ---------- the contract ----------

    def discover(self, seed: CatalogSeed) -> Iterable[ExternalRef]:
        """One reviews page per model, visited once per run."""
        two_wheeler = seed.vehicle_class == "two_wheeler"
        host = BIKE_HOST if two_wheeler else CAR_HOST
        path = "reviews" if two_wheeler else "user-reviews"
        url = f"{host}/{_slug(seed.manufacturer)}/{_slug(seed.model)}/{path}"
        if url in self._seen_urls:
            return
        self._seen_urls.add(url)
        yield ExternalRef(
            external_id=url,
            url=url,
            seed=seed,
            hint={"model": f"{seed.manufacturer} {seed.model}"},
        )

    def fetch(self, ref: ExternalRef) -> RawPayload:
        response = self._http().get(ref.url)
        return RawPayload(
            ref=ref,
            body=response.content,
            fetched_at=datetime.now(UTC),
            http_status=response.status_code,
            content_type=response.headers.get("content-type"),
        )

    def parse(self, raw: RawPayload) -> list[EvidenceUnitDraft]:
        if raw.http_status != 200 or not raw.body:
            return []
        html = raw.body.decode("utf-8", errors="replace")
        seed = raw.ref.seed
        model_label = str(raw.ref.hint.get("model") or "")

        drafts: list[EvidenceUnitDraft] = []
        for review in _reviews_in(html):
            body = str(review.get("reviewBody") or "").strip()
            title = str(review.get("name") or "").strip()
            if len(body) < MIN_BODY_CHARS:
                continue
            text = f"{title}. {body}" if title else body

            author = review.get("author")
            author_name = (
                str(author.get("name")) if isinstance(author, dict) and author.get("name") else None
            )
            # "user" is what the site shows for a review posted without a
            # display name. It is a placeholder, not a person, and treating it
            # as an author identity would pool thousands of strangers into one
            # reputation.
            if author_name in {"user", "User", "Anonymous", ""}:
                author_name = None

            drafts.append(
                EvidenceUnitDraft(
                    external_id=_review_id(raw.ref.url, title, body),
                    text=text,
                    modality=Modality.TEXT,
                    url=raw.ref.url,
                    author_ref=author_name,
                    lang=None,
                    # The JSON-LD carries no date. Rather than invent one from
                    # the fetch time, which would make every review look like
                    # it was written today and hand the recency weighting a
                    # lie, it stays null.
                    published_at=None,
                    rating_raw=_rating(review),
                    rating_scale_max=5.0 if _rating(review) is not None else None,
                    # Self-declared, not verified by the platform. Null, so
                    # nothing from here can enter the section 18.1 gold set.
                    is_verified_owner=None,
                    helpful_votes=None,
                    total_votes=None,
                    ownership_duration_months=ownership_months(text),
                    km_driven=km_driven(text),
                    # The variant the reviewer named, if they named one. This
                    # is what gives the resolver something to work with on a
                    # page that is otherwise entirely model level.
                    listing_title=_listing_title(model_label, text),
                    variant_hint=_variant_tokens(text) or None,
                    model_hint=model_label
                    or (f"{seed.manufacturer} {seed.model}" if seed else None),
                )
            )
        return drafts


# ---------------------------------------------------------------------------
# parsing helpers
# ---------------------------------------------------------------------------


def _reviews_in(html: str) -> list[dict[str, Any]]:
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


def _rating(review: dict[str, Any]) -> float | None:
    rating = review.get("reviewRating")
    if not isinstance(rating, dict):
        return None
    try:
        value = float(rating.get("ratingValue"))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return value if 0.0 <= value <= 5.0 else None


def _variant_tokens(text: str) -> str:
    """The trim, fuel and gearbox words the reviewer used, in order, deduped."""
    seen: list[str] = []
    for match in _VARIANT_TOKENS.finditer(text):
        # Whitespace inside a bracketed trim is normalised away, so "SX ( O )"
        # and "SX(O)" resolve to the same listing rather than to two.
        token = re.sub(r"\s+", "", match.group(1)).lower()
        if token not in seen:
            seen.append(token)
    return " ".join(seen)


def _listing_title(model_label: str, text: str) -> str:
    """What this review says it is about, in the source's own words.

    One listing per distinct combination, so a review that names a trim gets
    its own resolution decision instead of being lumped in with every other
    review of the model and resolved all or nothing.
    """
    tokens = _variant_tokens(text)
    return f"{model_label} {tokens}".strip() if tokens else model_label


def _review_id(url: str, title: str, body: str) -> str:
    """A stable identity, because the source does not publish one.

    Derived from the content, so re-reading the page tomorrow recognises the
    same review rather than inserting it again.
    """
    basis = f"{url}|{title}|{body[:400]}".casefold()
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:32]


def _slug(name: str) -> str:
    """Their URL form: lowercase, hyphenated, punctuation dropped."""
    cleaned = re.sub(r"[^a-z0-9\s-]", "", name.casefold())
    return re.sub(r"[\s-]+", "-", cleaned).strip("-")
