"""CarWale owner reviews.

A second real source, and a genuinely independent one: CarWale belongs to
CarTrade, CarDekho to Girnar. That matters more than it sounds, because the
evidence floor asks for three *distinct* sources before publishing a verdict,
and counting two sites owned by the same company as two sources would be
gaming our own quality rule rather than meeting it.

Two things it has that CarDekho does not.

**Dates.** Every review carries a `datePublished`. CarDekho publishes none at
all, which means the recency weighting has had nothing to work with on real
evidence until now.

**Pages.** `?page=N` returns genuinely different reviews, verified to page 12,
where CarDekho ignores the parameter and hands back page one. So this source
can supply the volume the evidence floor needs, rather than the thirty reviews
per model that CarDekho caps at.

Cars only, deliberately. BikeWale is the same publisher's two-wheeler site and
exposes exactly one review in its JSON-LD however many pages you ask for, and
its manufacturer slugs are inconsistent with CarWale's. Two-wheelers are
covered by BikeDekho and YouTube instead.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from dateutil import parser as date_parser

from revix_core.enums import Modality, SourceKind
from revix_pipeline.connectors.base import (
    CatalogSeed,
    EvidenceUnitDraft,
    ExternalRef,
    RawPayload,
)
from revix_pipeline.connectors.hints import km_driven, ownership_months
from revix_pipeline.connectors.politeness import PoliteClient
from revix_pipeline.connectors.schema_org import (
    author_of,
    listing_title,
    rating_of,
    review_id,
    reviews_in,
    slug,
    variant_tokens,
)

HOST = "https://www.carwale.com"

#: Deliberately slow. Five pages across sixteen models is eighty requests a
#: night, which at this rate takes eight minutes and inconveniences nobody.
RATE_LIMIT_RPM = 10

#: Ten reviews a page, so eight pages is eighty per model. Five cleared the
#: forty-unit floor on paper and did not in practice: not every sentence
#: carries an opinion the extractor can use, and eleven of the twenty-eight
#: cars still published nothing. A model
#: with fewer reviews than this returns repeats on the trailing pages, and the
#: framework drops them by content hash.
PAGES_PER_MODEL = 8

MIN_BODY_CHARS = 60

#: What the site shows when a review was posted without a display name.
_PLACEHOLDER_AUTHORS = frozenset({"user", "User", "Anonymous", "CarWale User", "Guest"})


class CarWaleConnector:
    """Five pages of owner reviews per car model."""

    source_key = "carwale"
    display_name = "CarWale owner reviews"
    kind = SourceKind.OWNER_REVIEW
    base_url: str | None = HOST
    robots_policy: str | None = "robots.txt permits /reviews/, checked 2026-09-06; 10 rpm"
    rate_limit_rpm = RATE_LIMIT_RPM
    #: The same prior as CarDekho. Same kind of evidence, same absence of
    #: ownership verification; nothing about this site makes its reviewers
    #: more or less trustworthy than the other's.
    default_source_prior = 0.65

    def __init__(self, *, pages_per_model: int = PAGES_PER_MODEL) -> None:
        self.pages_per_model = pages_per_model
        self._client: PoliteClient | None = None
        # One connector instance serves one run, because the CLI is a fresh
        # process each time. Six Creta variants would otherwise fetch the same
        # five pages six times over.
        self._seen: set[str] = set()

    def _http(self) -> PoliteClient:
        if self._client is None:
            self._client = PoliteClient(
                self.source_key,
                rate_limit_rpm=self.rate_limit_rpm,
                # Ordinary unauthenticated page fetches, so robots applies in
                # full, unlike the credentialed API connectors.
                respect_robots=True,
            )
        return self._client

    # ---------- the contract ----------

    def discover(self, seed: CatalogSeed) -> Iterable[ExternalRef]:
        if seed.vehicle_class == "two_wheeler":
            # BikeWale exposes one review per page whatever you ask for. Two
            # wheelers come from BikeDekho and YouTube instead.
            return
        base = f"{HOST}/{slug(seed.manufacturer)}-cars/{slug(seed.model)}/reviews/"
        if base in self._seen:
            return
        self._seen.add(base)
        label = f"{seed.manufacturer} {seed.model}"
        for page in range(1, self.pages_per_model + 1):
            url = base if page == 1 else f"{base}?page={page}"
            yield ExternalRef(
                external_id=url,
                url=url,
                seed=seed,
                hint={"model": label, "page": str(page)},
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
        for review in reviews_in(html):
            body = str(review.get("reviewBody") or "").strip()
            title = str(review.get("name") or "").strip()
            if len(body) < MIN_BODY_CHARS:
                continue
            text = f"{title}. {body}" if title else body

            drafts.append(
                EvidenceUnitDraft(
                    external_id=review_id(raw.ref.url, title, body),
                    text=text,
                    modality=Modality.TEXT,
                    url=raw.ref.url,
                    author_ref=author_of(review, _PLACEHOLDER_AUTHORS),
                    lang=None,
                    published_at=_published(review.get("datePublished")),
                    rating_raw=rating_of(review),
                    rating_scale_max=5.0 if rating_of(review) is not None else None,
                    # Self-declared, like every other consumer review site.
                    # Null, so nothing from here can enter the 18.1 gold set.
                    is_verified_owner=None,
                    helpful_votes=None,
                    total_votes=None,
                    ownership_duration_months=ownership_months(text),
                    km_driven=km_driven(text),
                    listing_title=listing_title(model_label, text),
                    variant_hint=variant_tokens(text) or None,
                    model_hint=model_label
                    or (f"{seed.manufacturer} {seed.model}" if seed else None),
                )
            )
        return drafts


def _published(value: object) -> datetime | None:
    """The one thing CarDekho does not give us, so it is worth reading well."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = date_parser.isoparse(value)
    except (ValueError, OverflowError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
