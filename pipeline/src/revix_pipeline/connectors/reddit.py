"""Reddit, through the official API.

Indian ownership discussion happens in a handful of subreddits and it is the
closest thing to an unmoderated owner corpus that exists: nobody is selling a
car in r/CarsIndia, which is exactly what makes it worth reading and exactly
what makes it noisy.

Official OAuth API rather than scraping. Reddit publishes an API, asks for a
descriptive user agent and a rate limit, and grants read access to a script
application for free. Where a source offers that, taking it is both the polite
choice and the robust one, because an API contract changes on a deprecation
notice whereas markup changes on a Tuesday.

What Reddit cannot give us, and this matters for section 18.1: there is no
verified-owner flag. `is_verified_owner` therefore stays null on every unit
from this source rather than being guessed, and the ownership signals that the
gold set needs are read out of the text instead.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from revix_core.enums import Modality, SourceKind
from revix_core.settings import get_settings
from revix_pipeline.connectors.base import (
    CatalogSeed,
    EvidenceUnitDraft,
    ExternalRef,
    MissingCredentialsError,
    RawPayload,
)
from revix_pipeline.connectors.hints import km_driven, ownership_months
from revix_pipeline.connectors.politeness import PoliteClient

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API_BASE = "https://oauth.reddit.com"

# Reddit allows 100 requests per minute per OAuth client. Sitting well under
# it costs us nothing: the nightly run is not in a hurry.
RATE_LIMIT_RPM = 55

# Bodies that carry no evidence.
_DEAD = {"[deleted]", "[removed]", ""}
_BOTS = {"AutoModerator", "automoderator"}

# A one-line comment is a reaction, not evidence. The extractor can find an
# aspect in it and the fusion stage would then weight a shrug.
MIN_BODY_CHARS = 80


class RedditConnector:
    """Search a few Indian vehicle subreddits, read the discussion."""

    source_key = "reddit"
    display_name = "Reddit (r/CarsIndia and friends)"
    kind = SourceKind.FORUM
    base_url: str | None = API_BASE
    robots_policy: str | None = "official API, OAuth client credentials, 55 rpm"
    rate_limit_rpm = RATE_LIMIT_RPM
    # Middling. A subreddit is unverified and self-selecting, but it is also
    # the only place people describe a problem they are still living with.
    default_source_prior = 0.60

    def __init__(
        self,
        *,
        posts_per_variant: int = 6,
        comments_per_post: int = 100,
    ) -> None:
        self.posts_per_variant = posts_per_variant
        self.comments_per_post = comments_per_post
        self._client: PoliteClient | None = None
        self._token_expires_at = 0.0

    # ---------- authentication ----------

    def _authenticated(self) -> PoliteClient:
        """One token per run, refreshed a minute before it expires."""
        settings = get_settings()
        if not settings.reddit_client_id or not settings.reddit_client_secret:
            raise MissingCredentialsError(
                "reddit needs REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET. Create a "
                "'script' app at https://www.reddit.com/prefs/apps and put both in .env."
            )
        if self._client is None:
            self._client = PoliteClient(
                self.source_key,
                rate_limit_rpm=self.rate_limit_rpm,
                # An authenticated API client is not a crawler. robots.txt on
                # www.reddit.com governs crawlers, and applying it here would
                # block the very endpoint Reddit issued us credentials for.
                respect_robots=False,
                headers={"User-Agent": settings.reddit_user_agent or settings.user_agent},
            )
        if time.monotonic() < self._token_expires_at:
            return self._client

        response = self._client.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(settings.reddit_client_id, settings.reddit_client_secret),
        )
        if response.status_code != 200:
            raise MissingCredentialsError(
                f"reddit refused the credentials with HTTP {response.status_code}. "
                "Check the client id and secret, and that the app type is 'script'."
            )
        payload = response.json()
        self._client.set_header("Authorization", f"bearer {payload['access_token']}")
        self._token_expires_at = time.monotonic() + float(payload.get("expires_in", 3600)) - 60
        return self._client

    # ---------- the contract ----------

    def discover(self, seed: CatalogSeed) -> Iterable[ExternalRef]:
        """Search each subreddit for the model, not the variant.

        Nobody writes "Creta SX (O) Turbo DCT" in a post title. They write
        "Creta". Searching for the variant would return nothing, so we search
        for the model and let the resolver decide which variant the thread is
        actually about, which is the same division of labour every other
        connector follows.
        """
        client = self._authenticated()
        subreddits = get_settings().subreddits_for(seed.vehicle_class)
        query = f"{seed.manufacturer} {seed.model}"
        seen: set[str] = set()
        for subreddit in subreddits:
            response = client.get(
                f"{API_BASE}/r/{subreddit}/search",
                params={
                    "q": query,
                    "restrict_sr": "on",
                    "sort": "relevance",
                    "t": "all",
                    "type": "link",
                    "limit": self.posts_per_variant,
                    "raw_json": 1,
                },
            )
            if response.status_code != 200:
                # A private, renamed or misspelled subreddit. Skip it and read
                # the others rather than failing the whole source over one name.
                continue
            for child in response.json().get("data", {}).get("children", []):
                data = child.get("data", {})
                post_id = data.get("id")
                if not post_id or post_id in seen:
                    continue
                seen.add(post_id)
                yield ExternalRef(
                    external_id=f"t3_{post_id}",
                    url=f"https://www.reddit.com{data.get('permalink', '')}",
                    seed=seed,
                    hint={"subreddit": subreddit, "title": data.get("title", "")},
                )

    def fetch(self, ref: ExternalRef) -> RawPayload:
        """The post and its comments, in one documented call."""
        client = self._authenticated()
        post_id = ref.external_id.removeprefix("t3_")
        response = client.get(
            f"{API_BASE}/comments/{post_id}",
            params={
                "limit": self.comments_per_post,
                "depth": 1,
                "sort": "top",
                "raw_json": 1,
            },
        )
        return RawPayload(
            ref=ref,
            body=response.content,
            fetched_at=datetime.now(UTC),
            http_status=response.status_code,
            content_type=response.headers.get("content-type"),
        )

    def parse(self, raw: RawPayload) -> list[EvidenceUnitDraft]:
        """The post body and every top-level comment worth keeping."""
        if raw.http_status != 200:
            return []
        try:
            listings = json.loads(raw.body)
        except ValueError:
            return []
        if not isinstance(listings, list) or len(listings) < 2:
            return []

        post = _first_child(listings[0])
        if post is None:
            return []
        title = str(post.get("title") or "")
        drafts: list[EvidenceUnitDraft] = []

        selftext = str(post.get("selftext") or "")
        if selftext.strip() not in _DEAD and len(selftext) >= MIN_BODY_CHARS:
            drafts.append(self._draft(post, f"{title}\n\n{selftext}", title, raw.ref, "t3"))

        for child in listings[1].get("data", {}).get("children", []):
            if child.get("kind") != "t1":
                # "more" stubs, which would need another request each. The
                # long tail of a thread is where the least evidence lives.
                continue
            comment = child.get("data", {})
            body = str(comment.get("body") or "")
            if body.strip() in _DEAD or len(body) < MIN_BODY_CHARS:
                continue
            if str(comment.get("author") or "") in _BOTS:
                continue
            drafts.append(self._draft(comment, body, title, raw.ref, "t1"))

        return drafts

    def _draft(
        self,
        node: dict[str, Any],
        text: str,
        listing_title: str,
        ref: ExternalRef,
        kind: str,
    ) -> EvidenceUnitDraft:
        seed = ref.seed
        created = node.get("created_utc")
        score = node.get("score")
        return EvidenceUnitDraft(
            external_id=f"{kind}_{node.get('id')}",
            text=text.strip(),
            modality=Modality.TEXT,
            url=f"https://www.reddit.com{node.get('permalink', '')}",
            author_ref=str(node.get("author") or "") or None,
            # Hinglish is common here and the extractor handles it, so
            # asserting "en" would be a claim we have not checked.
            lang=None,
            published_at=(
                datetime.fromtimestamp(float(created), tz=UTC) if created is not None else None
            ),
            # Reddit has no rating and no owner verification. Both stay null
            # rather than being invented; section 18.1 depends on the
            # difference between "not an owner" and "we do not know".
            rating_raw=None,
            rating_scale_max=None,
            is_verified_owner=None,
            helpful_votes=max(0, int(score)) if isinstance(score, int | float) else None,
            total_votes=None,
            ownership_duration_months=ownership_months(text),
            km_driven=km_driven(text),
            listing_title=listing_title or None,
            variant_hint=seed.variant_name if seed else None,
            model_hint=f"{seed.manufacturer} {seed.model}" if seed else None,
        )


def _first_child(listing: object) -> dict[str, Any] | None:
    if not isinstance(listing, dict):
        return None
    children = listing.get("data", {}).get("children", [])
    if not children:
        return None
    data = children[0].get("data")
    return data if isinstance(data, dict) else None
