"""The politeness layer: rate limiting, the circuit breaker, robots, and the
client that ties them together.

None of this touches the network. The token bucket is driven by its own clock,
robots is fed a stub transport, and the client is given an httpx MockTransport
so the breaker's reaction to a refusal can be asserted without a real server.
"""

from __future__ import annotations

import time

import httpx
import pytest

from revix_pipeline.connectors.politeness import (
    CircuitBreaker,
    CircuitOpenError,
    PoliteClient,
    RobotsCache,
    RobotsDisallowedError,
    TokenBucket,
)


class TestTokenBucket:
    def test_a_non_positive_rate_is_refused(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            TokenBucket(0)

    def test_the_first_token_is_free_and_the_next_must_wait(self) -> None:
        bucket = TokenBucket(60, capacity=1)  # one per second, room for one
        assert bucket.acquire(sleep=False) == 0.0
        waited = bucket.acquire(sleep=False)
        assert waited == pytest.approx(1.0, abs=0.05)


class TestCircuitBreaker:
    def test_it_opens_after_the_threshold_and_then_refuses(self) -> None:
        breaker = CircuitBreaker(threshold=3)
        for _ in range(3):
            breaker.record_failure()
        assert breaker.is_open
        with pytest.raises(CircuitOpenError, match="circuit open"):
            breaker.check("dekho")

    def test_a_success_closes_it_again(self) -> None:
        breaker = CircuitBreaker(threshold=2)
        breaker.record_failure()
        breaker.record_success()
        assert not breaker.is_open
        assert breaker.failures == 0

    def test_it_goes_half_open_once_the_cooldown_passes(self) -> None:
        breaker = CircuitBreaker(threshold=2, reset_after=0.0)
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.opened_at is not None
        # reset_after is zero, so the next read lets one attempt through.
        assert breaker.is_open is False
        assert breaker.failures == breaker.threshold - 1


class _StubClient:
    def __init__(self, *, status: int = 200, text: str = "", boom: bool = False) -> None:
        self._status = status
        self._text = text
        self._boom = boom

    def get(self, url: str) -> httpx.Response:
        if self._boom:
            raise httpx.ConnectError("no route")
        return httpx.Response(self._status, text=self._text)


class TestRobotsCache:
    def test_a_disallowed_path_is_refused_and_a_sibling_is_allowed(self) -> None:
        robots = "User-agent: *\nDisallow: /private\n"
        cache = RobotsCache("revix-bot")
        stub = _StubClient(status=200, text=robots)
        assert cache.allows("http://host.test/public/page", client=stub) is True
        # Same origin, so the cached parser answers without a second fetch.
        assert cache.allows("http://host.test/private/secret", client=stub) is False

    def test_a_missing_robots_file_is_read_as_permission(self) -> None:
        cache = RobotsCache("revix-bot")
        assert cache.allows("http://nofile.test/x", client=_StubClient(status=404)) is True

    def test_an_unreadable_robots_file_does_not_block_the_crawl(self) -> None:
        cache = RobotsCache("revix-bot")
        assert cache.allows("http://down.test/x", client=_StubClient(boom=True)) is True


class TestPoliteClient:
    def _client(self, handler) -> PoliteClient:  # type: ignore[no-untyped-def]
        pc = PoliteClient("test-source", respect_robots=False)
        pc._client = httpx.Client(transport=httpx.MockTransport(handler))
        return pc

    def test_a_good_response_passes_through_and_keeps_the_breaker_closed(self) -> None:
        pc = self._client(lambda request: httpx.Response(200, text="ok"))
        response = pc.get("http://example.test/thing")
        assert response.status_code == 200
        assert pc.breaker.failures == 0
        pc.close()

    def test_a_refusal_counts_against_the_breaker(self) -> None:
        pc = self._client(lambda request: httpx.Response(403))
        response = pc.get("http://example.test/denied")
        assert response.status_code == 403
        assert pc.breaker.failures == 1
        pc.close()

    def test_robots_is_consulted_before_a_get(self) -> None:
        pc = PoliteClient("test-source", respect_robots=True)
        pc.robots.allows = lambda url, client=None: False  # type: ignore[method-assign]
        with pytest.raises(RobotsDisallowedError, match="disallows"):
            pc.get("http://example.test/blocked")
        pc.close()

    def test_an_open_breaker_short_circuits_before_any_request(self) -> None:
        pc = self._client(lambda request: httpx.Response(200))
        pc.breaker.failures = pc.breaker.threshold
        pc.breaker.opened_at = time.monotonic()
        with pytest.raises(CircuitOpenError):
            pc.get("http://example.test/thing")
        pc.close()
