"""API contract tests.

Marked `db` because the API is a read of real rows by design. Mocking the
database here would test a mock rather than the contract, and the contract is
the thing the frontend depends on.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from revix_api.main import agreement_word, app
from revix_core.models import Verdict

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def seeded(client: TestClient) -> dict[str, object]:
    """Skip the whole module if the pipeline has not been run locally."""
    health = client.get("/health").json()
    if health["verdicts"] == 0:
        pytest.skip("no verdicts computed. Run: uv run revix pipeline nightly")
    return health


class TestAgreementWording:
    """A decimal means nothing to a person choosing a car."""

    @pytest.mark.parametrize(
        ("divergence", "expected"),
        [(0.61, "sharply split"), (0.30, "some disagreement"), (0.05, "broad agreement")],
    )
    def test_divergence_becomes_words(self, divergence: float, expected: str) -> None:
        assert agreement_word(divergence) == expected

    def test_unknown_divergence_says_so(self) -> None:
        assert agreement_word(None) == "unknown"


class TestContract:
    def test_health_reports_what_exists(self, client: TestClient) -> None:
        body = client.get("/health").json()
        assert body["status"] == "ok"
        assert body["database"] is True

    def test_the_switch_offers_exactly_the_seeded_strategies(
        self, client: TestClient, seeded: dict[str, object]
    ) -> None:
        configs = client.get("/fusion-configs").json()
        names = [c["name"] for c in configs]
        assert names == ["equal", "source_weighted", "credibility_weighted"]
        assert sum(1 for c in configs if c["is_default"]) == 1

    def test_an_unknown_weighting_is_rejected_with_the_valid_options(
        self, client: TestClient, seeded: dict[str, object]
    ) -> None:
        response = client.get("/variants?fusion=nonsense")
        assert response.status_code == 404
        assert "equal" in response.json()["detail"]

    def test_search_filters_the_catalogue(
        self, client: TestClient, seeded: dict[str, object]
    ) -> None:
        results = client.get("/variants?q=Creta&limit=20").json()
        assert results
        assert all("Creta" in v["model"] or "Creta" in v["variant_name"] for v in results)

    def test_two_wheelers_can_be_filtered_out(
        self, client: TestClient, seeded: dict[str, object]
    ) -> None:
        bikes = client.get("/variants?vehicle_class=two_wheeler&limit=50").json()
        assert bikes
        assert all(v["vehicle_class"] == "two_wheeler" for v in bikes)


class TestVerdict:
    @pytest.fixture
    def variant_id(self, client: TestClient, seeded: dict[str, object]) -> str:
        results = client.get("/variants?limit=100").json()
        scored = [v for v in results if not v["is_suppressed"]]
        if not scored:
            pytest.skip("no unsuppressed verdicts available")
        return str(scored[0]["id"])

    def test_a_verdict_states_how_much_it_rests_on(
        self, client: TestClient, variant_id: str
    ) -> None:
        """A number you cannot judge is a number you have to trust blindly."""
        body = client.get(f"/variants/{variant_id}/verdict").json()
        assert body["evidence_count"] > 0
        assert body["effective_sample_size"] is not None
        assert body["sources_used"]
        assert body["computed_at"]

    def test_effective_sample_never_exceeds_the_evidence_count(
        self, client: TestClient, variant_id: str
    ) -> None:
        body = client.get(f"/variants/{variant_id}/verdict").json()
        assert body["effective_sample_size"] <= body["evidence_count"]

    def test_aspects_are_ordered_by_disagreement_not_by_score(
        self, client: TestClient, variant_id: str
    ) -> None:
        """Conflict first. The opposite of what every competitor does."""
        aspects = client.get(f"/variants/{variant_id}/verdict").json()["aspects"]
        divergences = [a["divergence_index"] or 0 for a in aspects]
        assert divergences == sorted(divergences, reverse=True)

    def test_every_aspect_carries_words_as_well_as_a_number(
        self, client: TestClient, variant_id: str
    ) -> None:
        aspects = client.get(f"/variants/{variant_id}/verdict").json()["aspects"]
        allowed = {"sharply split", "some disagreement", "broad agreement", "unknown"}
        assert all(a["agreement"] in allowed for a in aspects)

    def test_the_score_always_sits_inside_its_own_interval(
        self, client: TestClient, variant_id: str
    ) -> None:
        body = client.get(f"/variants/{variant_id}/verdict").json()
        assert body["confidence_low"] <= body["overall_score"] <= body["confidence_high"]
        for a in body["aspects"]:
            assert a["ci_low"] <= a["score"] <= a["ci_high"]

    def test_switching_the_weighting_returns_a_different_verdict(
        self, client: TestClient, variant_id: str
    ) -> None:
        """The flagship. If these were identical the product would have no point."""
        equal = client.get(f"/variants/{variant_id}/verdict?fusion=equal").json()
        cred = client.get(f"/variants/{variant_id}/verdict?fusion=credibility_weighted").json()
        assert equal["fusion"] != cred["fusion"]
        assert equal["effective_sample_size"] != cred["effective_sample_size"]

    def test_weighting_carefully_lowers_the_effective_sample(
        self, client: TestClient, variant_id: str
    ) -> None:
        """Being choosier about evidence means having less of it, and saying so."""
        equal = client.get(f"/variants/{variant_id}/verdict?fusion=equal").json()
        cred = client.get(f"/variants/{variant_id}/verdict?fusion=credibility_weighted").json()
        assert cred["effective_sample_size"] < equal["effective_sample_size"]

    def test_an_unknown_variant_is_a_404(self, client: TestClient) -> None:
        missing = "00000000-0000-0000-0000-000000000000"
        assert client.get(f"/variants/{missing}/verdict").status_code == 404


class TestTraceability:
    def test_every_number_can_be_traced_to_the_reviews_behind_it(
        self, client: TestClient, seeded: dict[str, object]
    ) -> None:
        """The guarantee the whole project rests on, exercised over HTTP."""
        results = [v for v in client.get("/variants?limit=100").json() if not v["is_suppressed"]]
        if not results:
            pytest.skip("no unsuppressed verdicts available")
        verdict = client.get(f"/variants/{results[0]['id']}/verdict").json()
        aspect = verdict["aspects"][0]
        assert aspect["claim_id"], "an aspect with no claim cannot be traced"

        drawer = client.get(f"/claims/{aspect['claim_id']}/evidence").json()
        assert drawer["evidence"], "a claim with no evidence links is untraceable"
        assert drawer["aspect_key"] == aspect["aspect_key"]

        # Ordered by how much each review counted, and every weight is real.
        weights = [e["contribution_weight"] for e in drawer["evidence"]]
        assert weights == sorted(weights, reverse=True)
        assert all(0 < w <= 1 for w in weights)
        ranks = [e["rank"] for e in drawer["evidence"]]
        assert ranks == list(range(1, len(ranks) + 1))


class TestSuppression:
    def test_thin_evidence_produces_no_score_and_says_why(self, session: Session) -> None:
        """Better to show nothing than a number built on nineteen reviews."""
        suppressed = session.scalar(select(Verdict).where(Verdict.is_suppressed))
        if suppressed is None:
            pytest.skip("nothing is below the evidence floor in this database")
        assert suppressed.overall_score is None
        assert suppressed.suppression_reason


class TestOps:
    def test_source_health_lists_every_registered_source(
        self, client: TestClient, seeded: dict[str, object]
    ) -> None:
        sources = client.get("/sources/health").json()
        assert sources
        assert all("source_key" in s and "status" in s for s in sources)
