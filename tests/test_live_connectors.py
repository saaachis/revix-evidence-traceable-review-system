"""The live connectors, without going anywhere near the network.

Everything here is parsing and policy, which is where connector bugs actually
live. A connector that cannot reach its API fails loudly and visibly; a
connector that silently drops half a thread, or invents a verified owner,
fails quietly for weeks.

The payloads below are trimmed copies of the real response shapes. They are
deliberately awkward: deleted comments, a bot, a one-word reply, a "more"
stub. Those are what the parser has to survive.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from revix_core.enums import Modality
from revix_pipeline.connectors import registry
from revix_pipeline.connectors.base import (
    CatalogSeed,
    ExternalRef,
    MissingCredentialsError,
    RawPayload,
)
from revix_pipeline.connectors.hints import (
    km_driven,
    looks_like_ownership_account,
    ownership_months,
)
from revix_pipeline.connectors.reddit import RedditConnector
from revix_pipeline.connectors.youtube import YouTubeConnector

SEED = CatalogSeed(
    variant_id="00000000-0000-0000-0000-000000000001",
    manufacturer="Hyundai",
    model="Creta",
    variant_name="SX (O) Turbo DCT",
    vehicle_class="car",
)


class TestOwnershipHints:
    """The gold set in section 18.1 is defined by these two numbers."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("Done 45,000 km on mine so far.", 45000),
            ("about 45000 kms and no issues", 45000),
            ("crossed 60k kms last month", 60000),
            ("1.2 lakh km and still going", 120000),
            ("bought it at 5,000 km, now at 60,000 kms", 60000),
            ("no numbers here", None),
            # A price, not an odometer.
            ("it costs 12 lakh on road", None),
        ],
    )
    def test_distance(self, text: str, expected: int | None) -> None:
        assert km_driven(text) == expected

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("I have owned this car for 2 years now.", 24),
            ("18 months of ownership and the clutch went", 18),
            ("been driving it for 6 months", 6),
            # Neither of these is a period of ownership, and counting them
            # would put a stranger's guess into the held-out gold set.
            ("the warranty is 3 years", None),
            ("waited 2 months for delivery", None),
            ("great car", None),
        ],
    )
    def test_duration(self, text: str, expected: int | None) -> None:
        assert ownership_months(text) == expected

    def test_first_hand_account_is_a_weak_signal_not_a_verification(self) -> None:
        assert looks_like_ownership_account("I have owned mine for a year")
        assert not looks_like_ownership_account("The Creta is a good SUV apparently")


REDDIT_THREAD = [
    {
        "data": {
            "children": [
                {
                    "kind": "t3",
                    "data": {
                        "id": "abc123",
                        "title": "Hyundai Creta SX(O) 20,000 km ownership review",
                        "selftext": (
                            "Bought my Creta SX(O) diesel in 2022 and I have driven it "
                            "for 2 years now, about 45,000 km. The ride quality is "
                            "excellent on highways but the service centre experience "
                            "has been genuinely poor every single time."
                        ),
                        "author": "creta_owner",
                        "created_utc": 1700000000,
                        "score": 143,
                        "permalink": "/r/CarsIndia/comments/abc123/review/",
                    },
                }
            ]
        }
    },
    {
        "data": {
            "children": [
                {
                    "kind": "t1",
                    "data": {
                        "id": "c1",
                        "body": (
                            "Same experience here. I have had mine for 18 months and the "
                            "mileage in city traffic is nowhere near what they claim, "
                            "around 12 kmpl against the 17 on the brochure."
                        ),
                        "author": "another_owner",
                        "created_utc": 1700100000,
                        "score": 22,
                        "permalink": "/r/CarsIndia/comments/abc123/review/c1/",
                    },
                },
                # Too short to be evidence.
                {"kind": "t1", "data": {"id": "c2", "body": "nice", "author": "x", "score": 1}},
                # Deleted.
                {
                    "kind": "t1",
                    "data": {"id": "c3", "body": "[deleted]", "author": "y", "score": 0},
                },
                # A bot.
                {
                    "kind": "t1",
                    "data": {
                        "id": "c4",
                        "body": "Your post was removed because of rule 4. " * 4,
                        "author": "AutoModerator",
                        "score": 1,
                    },
                },
                # A "more" stub, which is a pointer rather than content.
                {"kind": "more", "data": {"id": "c5", "children": ["c6", "c7"]}},
            ]
        }
    },
]


def _raw(body: object, url: str = "https://www.reddit.com/r/CarsIndia/comments/abc123/review/"):
    return RawPayload(
        ref=ExternalRef(external_id="t3_abc123", url=url, seed=SEED),
        body=json.dumps(body).encode("utf-8"),
        fetched_at=datetime.now(UTC),
        http_status=200,
        content_type="application/json",
    )


class TestRedditParsing:
    connector = RedditConnector()

    def test_the_post_and_the_substantial_comment_both_become_evidence(self) -> None:
        drafts = self.connector.parse(_raw(REDDIT_THREAD))
        assert [d.external_id for d in drafts] == ["t3_abc123", "t1_c1"]

    def test_noise_is_dropped(self) -> None:
        """A shrug, a deleted body and a moderator bot are not observations."""
        kept = {d.external_id for d in self.connector.parse(_raw(REDDIT_THREAD))}
        assert {"t1_c2", "t1_c3", "t1_c4", "t1_c5"}.isdisjoint(kept)

    def test_ownership_signals_are_read_out_of_the_prose(self) -> None:
        post = self.connector.parse(_raw(REDDIT_THREAD))[0]
        assert post.ownership_duration_months == 24
        assert post.km_driven == 45000

    def test_verified_owner_is_never_asserted(self) -> None:
        """Reddit has no such flag. Guessing one would corrupt the gold set."""
        for draft in self.connector.parse(_raw(REDDIT_THREAD)):
            assert draft.is_verified_owner is None
            assert draft.rating_raw is None

    def test_every_unit_carries_the_thread_title_as_its_listing(self) -> None:
        """The resolver matches on the title, so it has to survive parsing."""
        for draft in self.connector.parse(_raw(REDDIT_THREAD)):
            assert draft.listing_title == "Hyundai Creta SX(O) 20,000 km ownership review"
            assert draft.model_hint == "Hyundai Creta"

    def test_the_post_body_is_prefixed_with_its_title(self) -> None:
        post = self.connector.parse(_raw(REDDIT_THREAD))[0]
        assert post.text.startswith("Hyundai Creta SX(O) 20,000 km ownership review")

    def test_scores_become_helpful_votes_and_dates_become_timestamps(self) -> None:
        post = self.connector.parse(_raw(REDDIT_THREAD))[0]
        assert post.helpful_votes == 143
        assert post.published_at == datetime.fromtimestamp(1700000000, tz=UTC)
        assert post.modality is Modality.TEXT

    @pytest.mark.parametrize(
        "body", [b"not json", b"{}", b"[]", json.dumps([{"data": {"children": []}}, {}]).encode()]
    )
    def test_a_malformed_payload_yields_nothing_rather_than_raising(self, body: bytes) -> None:
        raw = RawPayload(
            ref=ExternalRef(external_id="t3_x", url="https://example.test", seed=SEED),
            body=body,
            fetched_at=datetime.now(UTC),
            http_status=200,
        )
        assert self.connector.parse(raw) == []

    def test_a_non_200_yields_nothing(self) -> None:
        raw = _raw(REDDIT_THREAD)
        broken = RawPayload(ref=raw.ref, body=raw.body, fetched_at=raw.fetched_at, http_status=429)
        assert self.connector.parse(broken) == []


YOUTUBE_THREADS = {
    "_revix_video_title": "Hyundai Creta 2024 Long Term Review | 20,000 km later",
    "items": [
        {
            "snippet": {
                "topLevelComment": {
                    "id": "Ugx1",
                    "snippet": {
                        "textOriginal": (
                            "I have been driving my Creta for 3 years and 70,000 km. "
                            "The DCT gearbox is jerky in bumper to bumper traffic, "
                            "nobody mentions this in reviews."
                        ),
                        "authorDisplayName": "Ravi K",
                        "authorChannelId": {"value": "UC_ravi"},
                        "publishedAt": "2024-03-11T06:41:22Z",
                        "likeCount": 91,
                    },
                }
            }
        },
        {
            "snippet": {
                "topLevelComment": {
                    "id": "Ugx2",
                    "snippet": {
                        "textOriginal": "First!",
                        "authorDisplayName": "someone",
                        "publishedAt": "2024-03-11T06:42:00Z",
                        "likeCount": 0,
                    },
                }
            }
        },
    ],
}


class TestYouTubeParsing:
    connector = YouTubeConnector()

    def _raw(self, payload: object, status: int = 200) -> RawPayload:
        return RawPayload(
            ref=ExternalRef(
                external_id="vid1",
                url="https://www.youtube.com/watch?v=vid1",
                seed=SEED,
                hint={"title": "Hyundai Creta 2024 Long Term Review | 20,000 km later"},
            ),
            body=json.dumps(payload).encode("utf-8"),
            fetched_at=datetime.now(UTC),
            http_status=status,
        )

    def test_a_substantial_comment_becomes_evidence_and_a_cheer_does_not(self) -> None:
        drafts = self.connector.parse(self._raw(YOUTUBE_THREADS))
        assert [d.external_id for d in drafts] == ["Ugx1"]

    def test_the_author_is_the_channel_id_not_the_display_name(self) -> None:
        """Display names are not unique, and credibility accrues per author."""
        draft = self.connector.parse(self._raw(YOUTUBE_THREADS))[0]
        assert draft.author_ref == "UC_ravi"

    def test_ownership_signals_and_engagement_survive(self) -> None:
        draft = self.connector.parse(self._raw(YOUTUBE_THREADS))[0]
        assert draft.ownership_duration_months == 36
        assert draft.km_driven == 70000
        assert draft.helpful_votes == 91
        assert draft.published_at is not None
        assert draft.published_at.tzinfo is not None

    def test_the_video_title_becomes_the_listing(self) -> None:
        draft = self.connector.parse(self._raw(YOUTUBE_THREADS))[0]
        assert draft.listing_title == "Hyundai Creta 2024 Long Term Review | 20,000 km later"

    def test_comments_disabled_is_not_a_crash(self) -> None:
        """403 here means the uploader turned comments off, which is a fact."""
        assert self.connector.parse(self._raw({"error": {"code": 403}}, status=403)) == []

    def test_quota_is_refused_before_it_is_overrun(self) -> None:
        connector = YouTubeConnector(daily_quota=150)
        assert connector._spend(100) is True
        assert connector._spend(100) is False
        assert connector.quota_spent == 100


class TestCredentialsAreDemandedByName:
    """A missing key should name the key and where to get it."""

    def test_reddit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REDDIT_CLIENT_ID", "")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "")
        from revix_core.settings import get_settings

        get_settings.cache_clear()
        with pytest.raises(MissingCredentialsError, match="REDDIT_CLIENT_ID"):
            list(RedditConnector().discover(SEED))
        get_settings.cache_clear()

    def test_youtube(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("YOUTUBE_API_KEY", "")
        from revix_core.settings import get_settings

        get_settings.cache_clear()
        with pytest.raises(MissingCredentialsError, match="YOUTUBE_API_KEY"):
            list(YouTubeConnector().discover(SEED))
        get_settings.cache_clear()


class TestRegistration:
    def test_both_live_sources_are_registered_even_without_credentials(self) -> None:
        """So that `revix ingest --source reddit` says what is wrong."""
        assert "reddit" in registry
        assert "youtube" in registry

    def test_the_live_sources_are_not_more_trusted_than_the_expert_fixture(self) -> None:
        """A prior is a starting point, and anonymous text is not expert copy."""
        assert registry.get("reddit").default_source_prior < 0.8
        assert (
            registry.get("youtube").default_source_prior
            < registry.get("reddit").default_source_prior
        )
