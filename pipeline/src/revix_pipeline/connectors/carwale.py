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

**Pages.** `?page=N` returns genuinely different reviews, where CarDekho
ignores the parameter and hands back page one. The Creta runs to 173 reviews
before the pages come back empty. So this source can supply the volume the
evidence floor needs, rather than the thirty per model CarDekho caps at.

Two-wheelers come from BikeWale, the same publisher's bike site, under the
same source key because it is the same publisher and counting it separately
would inflate our own source count.

BikeWale needs a different technique. Its JSON-LD carries exactly one review
however many pages you ask for, so the ten on the page have to be read from
the markup. Ten, not the forty anchors you will count in the DOM: each review
is linked about four times over, from its title, its image and its footer. The anchor is each review's permalink, /{make}-bikes/{model}/
reviews/{id}/, and from there the enclosing card is read by the shape of its
children rather than by class name: the class names are hashed and change on
every deploy, while a card that holds a title, a date, a body and a helpful
count is a structure nobody rewrites casually.

That gives two-wheelers what they were missing. Before this they had BikeDekho
and YouTube, which is two sources and roughly twenty usable reviews per model,
and every bike on the site sat under the evidence floor.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from dateutil import parser as date_parser
from selectolax.parser import HTMLParser, Node

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
BIKE_HOST = "https://www.bikewale.com"

#: BikeWale's own spellings, which are not our catalogue's. "Royal Enfield"
#: is one word there and "Hero MotoCorp" loses its second half. A model we
#: cannot address simply 404s and contributes nothing, which is the right
#: failure: no evidence rather than the wrong evidence.
BIKE_MAKE_SLUGS: dict[str, str] = {
    "royal enfield": "royalenfield",
    "hero motocorp": "hero",
    "bajaj auto": "bajaj",
    "tvs motor": "tvs",
}

#: A review's permalink. The one thing on a BikeWale card that is not a hashed
#: class name, and therefore the only thing worth anchoring to.
_REVIEW_LINK = re.compile(r"^/[a-z0-9-]+-bikes/[a-z0-9-]+/reviews/(\d+)/$")

#: "6 years ago". Searched for anywhere in a line rather than anchored, since
#: the card renders it as "6 years ago Soutam Ghosh" with the name attached.
_AGE = re.compile(r"\b(\d+)\s+(day|week|month|year)s?\s+ago\b", re.IGNORECASE)
_HELPFUL = re.compile(r"helpful\?\s*(\d+)\s+(\d+)", re.IGNORECASE)
_AGE_DAYS = {"day": 1, "week": 7, "month": 30, "year": 365}

#: Deliberately slow. Around ten pages across twenty-five car models is a
#: couple of hundred requests a night, which at this rate takes under half an
#: hour and inconveniences nobody.
RATE_LIMIT_RPM = 10

#: A ceiling, not a target. Ten reviews a page, and the Creta runs to 173
#: before repeating, so eight pages was leaving more than half of a popular
#: model's reviews on the table. YouTube was supplying 83% of the whole corpus
#: while being the source with the lowest prior in the project, and the only
#: way to shift that ratio is to take more from the review sites: adding
#: models cannot do it, because YouTube scales with models too.
#:
#: Most models never reach twenty. The connector stops asking as soon as a
#: page returns nothing it has not already seen, so a model with forty reviews
#: costs five requests rather than twenty, and the ceiling only binds on the
#: handful of vehicles that genuinely have that much written about them.
PAGES_PER_MODEL = 20

MIN_BODY_CHARS = 60

#: What the site shows when a review was posted without a display name.
_PLACEHOLDER_AUTHORS = frozenset({"user", "User", "Anonymous", "CarWale User", "Guest"})


class CarWaleConnector:
    """Owner reviews, as deep as each model goes."""

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
        # pages six times over.
        self._seen: set[str] = set()
        #: Review ids already returned for a model, so a page that repeats
        #: earlier reviews can be recognised as the end of the list.
        self._ids_by_model: dict[str, set[str]] = {}
        #: Models whose pagination has run out. Asking again would spend a
        #: request to be told the same thing.
        self._exhausted: set[str] = set()

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
        label = f"{seed.manufacturer} {seed.model}"
        if seed.vehicle_class == "two_wheeler":
            # One page only. BikeWale ignores ?page and returns the same ten
            # reviews, so there is nothing further to ask it for.
            make = BIKE_MAKE_SLUGS.get(seed.manufacturer.casefold(), slug(seed.manufacturer))
            url = f"{BIKE_HOST}/{make}-bikes/{slug(seed.model)}/reviews/"
            if url in self._seen:
                return
            self._seen.add(url)
            yield ExternalRef(
                external_id=url, url=url, seed=seed, hint={"model": label, "page": "1"}
            )
            return
        base = f"{HOST}/{slug(seed.manufacturer)}-cars/{slug(seed.model)}/reviews/"
        if base in self._seen:
            return
        self._seen.add(base)
        for page in range(1, self.pages_per_model + 1):
            url = base if page == 1 else f"{base}?page={page}"
            yield ExternalRef(
                external_id=url,
                url=url,
                seed=seed,
                hint={"model": label, "page": str(page)},
            )

    def _model_key(self, ref: ExternalRef) -> str:
        """A model's pages share everything before the query string."""
        return ref.url.split("?")[0]

    def fetch(self, ref: ExternalRef) -> RawPayload:
        # Nothing left on this model, so do not spend a request finding out
        # again. discover() has to yield every page up front, since it cannot
        # know where the list ends; this is where that guess gets corrected.
        if self._model_key(ref) in self._exhausted:
            return RawPayload(ref=ref, body=b"", fetched_at=datetime.now(UTC), http_status=None)
        response = self._http().get(ref.url)
        return RawPayload(
            ref=ref,
            body=response.content,
            fetched_at=datetime.now(UTC),
            http_status=response.status_code,
            content_type=response.headers.get("content-type"),
        )

    def _parse_bikewale(
        self,
        html: str,
        raw: RawPayload,
        model_label: str,
        seed: CatalogSeed | None,
    ) -> list[EvidenceUnitDraft]:
        """Ten reviews a page, read from the markup rather than JSON-LD."""
        tree = HTMLParser(html)
        drafts: list[EvidenceUnitDraft] = []
        seen: set[str] = set()

        for anchor in tree.css("a[href]"):
            href = anchor.attributes.get("href") or ""
            match = _REVIEW_LINK.match(href)
            if not match or match.group(1) in seen:
                continue
            card = _card_of(anchor)
            if card is None:
                continue
            seen.add(match.group(1))

            title = " ".join(anchor.text().split())
            parsed = _parse_card(card, title)
            body = str(parsed["body"])
            if len(body) < MIN_BODY_CHARS:
                continue
            text = f"{title}. {body}" if title else body
            author = parsed["author"]

            drafts.append(
                EvidenceUnitDraft(
                    external_id=review_id(f"{BIKE_HOST}{href}", title, body),
                    text=text,
                    modality=Modality.TEXT,
                    url=f"{BIKE_HOST}{href}",
                    author_ref=str(author) if author else None,
                    lang=None,
                    published_at=parsed["published"],  # type: ignore[arg-type]
                    # BikeWale shows stars in markup we would have to guess at,
                    # so no rating rather than a guessed one.
                    rating_raw=None,
                    rating_scale_max=None,
                    is_verified_owner=None,
                    helpful_votes=parsed["helpful"],  # type: ignore[arg-type]
                    total_votes=parsed["total"],  # type: ignore[arg-type]
                    ownership_duration_months=ownership_months(text),
                    km_driven=km_driven(text),
                    listing_title=listing_title(model_label, text),
                    variant_hint=variant_tokens(text) or None,
                    model_hint=model_label
                    or (f"{seed.manufacturer} {seed.model}" if seed else None),
                )
            )
        self._note_page(raw, [d.external_id for d in drafts])
        return drafts

    def _note_page(self, raw: RawPayload, ids: list[str]) -> None:
        """Record what this page held, and whether the model is finished.

        A page returning nothing new means the list has ended. CarWale serves
        the last page's contents again rather than a 404, so repetition is the
        only end-of-list signal there is.
        """
        key = self._model_key(raw.ref)
        seen = self._ids_by_model.setdefault(key, set())
        # An empty page is the clearest end-of-list signal there is: past the
        # last page CarWale serves the shell with no reviews in it. The first
        # version of this required a page to be non-empty before it counted as
        # exhausted, which meant every model fetched all twenty pages and the
        # early stop never fired once.
        if not ids or all(i in seen for i in ids):
            self._exhausted.add(key)
        seen.update(ids)

    def parse(self, raw: RawPayload) -> list[EvidenceUnitDraft]:
        if raw.http_status != 200 or not raw.body:
            return []
        html = raw.body.decode("utf-8", errors="replace")
        seed = raw.ref.seed
        model_label = str(raw.ref.hint.get("model") or "")

        if raw.ref.url.startswith(BIKE_HOST):
            return self._parse_bikewale(html, raw, model_label, seed)

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
        self._note_page(raw, [d.external_id for d in drafts])
        return drafts


def _card_of(anchor: Node) -> Node | None:
    """The element holding one whole review, found by walking up from its link.

    Identified by what it contains rather than by its class, which is hashed,
    or by its size, which was the first thing I tried and was wrong: a card is
    a card whether the review inside it is four hundred characters or eighty,
    and a size threshold silently dropped the short ones.

    A review card is the first ancestor that also holds the posting date, so
    that is what we look for.
    """
    node = anchor
    for _ in range(7):
        parent = node.parent
        if parent is None:
            return None
        node = parent
        text = " ".join(node.text(separator=" ").split())
        if _AGE.search(text) or _HELPFUL.search(text):
            return node
    return None


def _age_to_date(text: str) -> datetime | None:
    """ "6 years ago" into a date.

    Approximate on purpose, and approximate is worth having: the recency
    weighting cares whether a review is from this year or from 2018, not which
    Tuesday it was written.
    """
    match = _AGE.match(text.strip())
    if not match:
        return None
    amount, unit = int(match.group(1)), match.group(2).lower()
    return datetime.now(UTC) - timedelta(days=amount * _AGE_DAYS[unit])


def _parse_card(card: Node, title: str) -> dict[str, object]:
    """Read a card by the shape of its children, not their class names."""
    out: dict[str, object] = {
        "body": "",
        "author": None,
        "published": None,
        "helpful": None,
        "total": None,
    }
    longest = ""
    for child in card.iter():
        text = " ".join(child.text(separator=" ").split())
        if not text or text == title:
            continue
        if (dated := _age_to_date(text)) is not None:
            out["published"] = dated
            # "6 years ago Soutam Ghosh": the name is whatever follows the age.
            remainder = _AGE.sub("", text).strip()
            out["author"] = remainder or None
            continue
        if (votes := _HELPFUL.search(text)) is not None:
            helpful, unhelpful = int(votes.group(1)), int(votes.group(2))
            out["helpful"], out["total"] = helpful, helpful + unhelpful
            continue
        if len(text) > len(longest):
            longest = text
    out["body"] = longest
    return out


def _published(value: object) -> datetime | None:
    """The one thing CarDekho does not give us, so it is worth reading well."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = date_parser.isoparse(value)
    except (ValueError, OverflowError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
