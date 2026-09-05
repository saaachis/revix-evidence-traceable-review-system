"""YouTube, through the official Data API.

Not the videos. The comments underneath them.

An Indian vehicle review video collects hundreds of replies from people who
own the thing, and they argue with the reviewer, which is the useful part:
"he says the mileage is 22, I get 17 in Bangalore traffic" is precisely the
gap between an expert claim and lived experience that this project exists to
measure. The video itself is one expert opinion and we already have expert
opinion; the comments are a different population.

Quota is the real constraint and it shapes the design. A search costs 100
units against a default daily allowance of 10,000, while a page of comment
threads costs 1. So we spend one search per variant and then read deeply,
rather than searching repeatedly and reading thinly.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from dateutil import parser as date_parser

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
from revix_pipeline.connectors.schema_org import variant_tokens

API_BASE = "https://www.googleapis.com/youtube/v3"

# Google's own guidance is that quota, not rate, is the limit. This keeps a
# nightly run from looking like a burst to anyone watching.
RATE_LIMIT_RPM = 60

# Comments are shorter than forum posts, so the floor is lower than Reddit's.
# "Best bike" is not evidence; two clauses about the clutch is.
MIN_BODY_CHARS = 60

_SEARCH_COST = 100
_THREADS_COST = 1


class YouTubeConnector:
    """One search per variant, then the comment threads on what it finds."""

    source_key = "youtube"
    display_name = "YouTube review comments"
    kind = SourceKind.VIDEO
    base_url: str | None = API_BASE
    robots_policy: str | None = "official Data API v3, API key, quota limited"
    rate_limit_rpm = RATE_LIMIT_RPM
    # The lowest prior of any source we run. A YouTube comment section is
    # anonymous, rewards brevity and jokes, and has no verification of any
    # kind. It earns its place by volume and by disagreeing with the video.
    default_source_prior = 0.40

    def __init__(
        self,
        *,
        videos_per_variant: int = 4,
        comments_per_video: int = 100,
        daily_quota: int = 10_000,
    ) -> None:
        self.videos_per_variant = videos_per_variant
        self.comments_per_video = comments_per_video
        self.daily_quota = daily_quota
        self.quota_spent = 0
        self._client: PoliteClient | None = None

    def _authenticated(self) -> PoliteClient:
        settings = get_settings()
        if not settings.youtube_api_key:
            raise MissingCredentialsError(
                "youtube needs YOUTUBE_API_KEY. Enable the YouTube Data API v3 in a "
                "Google Cloud project and create an API key, then put it in .env."
            )
        if self._client is None:
            self._client = PoliteClient(
                self.source_key,
                rate_limit_rpm=self.rate_limit_rpm,
                # A keyed API client is not a crawler; see the same note on
                # the Reddit connector.
                respect_robots=False,
            )
        return self._client

    def _spend(self, units: int) -> bool:
        """Refuse to start a call we cannot afford.

        Overrunning the quota does not fail loudly. It returns 403 for the
        rest of the day, which would look like a broken connector tomorrow
        morning rather than a budget that ran out tonight.
        """
        if self.quota_spent + units > self.daily_quota:
            return False
        self.quota_spent += units
        return True

    # ---------- the contract ----------

    def discover(self, seed: CatalogSeed) -> Iterable[ExternalRef]:
        client = self._authenticated()
        settings = get_settings()
        if not self._spend(_SEARCH_COST):
            return
        query = f"{seed.manufacturer} {seed.model} review ownership"
        response = client.get(
            f"{API_BASE}/search",
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "regionCode": "IN",
                "relevanceLanguage": "en",
                "order": "relevance",
                "maxResults": self.videos_per_variant,
                "key": settings.youtube_api_key,
            },
        )
        if response.status_code != 200:
            return
        for item in response.json().get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if not video_id:
                continue
            snippet = item.get("snippet", {})
            yield ExternalRef(
                external_id=video_id,
                url=f"https://www.youtube.com/watch?v={video_id}",
                seed=seed,
                hint={
                    "title": snippet.get("title", ""),
                    "channel": snippet.get("channelTitle", ""),
                },
            )

    def fetch(self, ref: ExternalRef) -> RawPayload:
        client = self._authenticated()
        settings = get_settings()
        if not self._spend(_THREADS_COST):
            return RawPayload(ref=ref, body=b"", fetched_at=datetime.now(UTC), http_status=None)
        response = client.get(
            f"{API_BASE}/commentThreads",
            params={
                "part": "snippet",
                "videoId": ref.external_id,
                "order": "relevance",
                "textFormat": "plainText",
                "maxResults": self.comments_per_video,
                "key": settings.youtube_api_key,
            },
        )
        # The video title travels with the payload, because parse() gets bytes
        # and the title is what the resolver matches a listing on.
        body = response.content
        if response.status_code == 200:
            enriched = response.json()
            enriched["_revix_video_title"] = ref.hint.get("title", "")
            body = json.dumps(enriched).encode("utf-8")
        return RawPayload(
            ref=ref,
            body=body,
            fetched_at=datetime.now(UTC),
            http_status=response.status_code,
            content_type=response.headers.get("content-type"),
        )

    def parse(self, raw: RawPayload) -> list[EvidenceUnitDraft]:
        """Top-level comments only.

        Replies are usually people arguing with each other rather than
        describing a vehicle, and threading them would make one loud
        disagreement look like ten observations.
        """
        if raw.http_status != 200 or not raw.body:
            # 403 here is ordinarily "comments are disabled on this video",
            # which is a fact about the video and not a failure of ours.
            return []
        try:
            payload = json.loads(raw.body)
        except ValueError:
            return []

        title = str(payload.get("_revix_video_title") or "")
        seed = raw.ref.seed
        drafts: list[EvidenceUnitDraft] = []

        for item in payload.get("items", []):
            top = item.get("snippet", {}).get("topLevelComment", {})
            comment = top.get("snippet", {})
            text = str(comment.get("textOriginal") or comment.get("textDisplay") or "")
            if len(text.strip()) < MIN_BODY_CHARS:
                continue
            comment_id = top.get("id") or item.get("id")
            if not comment_id:
                continue
            drafts.append(
                EvidenceUnitDraft(
                    external_id=str(comment_id),
                    text=text.strip(),
                    modality=Modality.TEXT,
                    url=f"{raw.ref.url}&lc={comment_id}",
                    # The channel id rather than the display name, because
                    # display names are not unique and credibility is
                    # accumulated per author.
                    author_ref=_author_ref(comment),
                    lang=None,
                    published_at=_published(comment.get("publishedAt")),
                    rating_raw=None,
                    rating_scale_max=None,
                    is_verified_owner=None,
                    helpful_votes=_int_or_none(comment.get("likeCount")),
                    total_votes=None,
                    ownership_duration_months=ownership_months(text),
                    km_driven=km_driven(text),
                    listing_title=title or None,
                    # Read from the video's own title and the comment, not
                    # from the variant we happened to search for. Echoing the
                    # search term back would record every comment as naming a
                    # trim, which is a claim the source never made and which
                    # the resolver would then act on.
                    variant_hint=variant_tokens(f"{title} {text}") or None,
                    model_hint=f"{seed.manufacturer} {seed.model}" if seed else None,
                )
            )
        return drafts


def _author_ref(comment: dict[str, Any]) -> str | None:
    channel = comment.get("authorChannelId")
    if isinstance(channel, dict) and channel.get("value"):
        return str(channel["value"])
    name = comment.get("authorDisplayName")
    return str(name) if name else None


def _published(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = date_parser.isoparse(value)
    except (ValueError, OverflowError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None
