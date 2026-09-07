"""The non-functional guarantees, asserted rather than assumed.

Security headers, rate limiting, cache directives and compression are the
kind of thing that works on the day it is added and quietly stops working six
commits later, because nothing about the app looks broken when they are gone.
A test is the only thing that notices.

None of these need a database. They exercise the middleware stack, which runs
before any endpoint touches a session, so /health answering 503 on a machine
with no Postgres is a perfectly good request for these purposes.
"""

from __future__ import annotations

import gzip
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from revix_api.main import app
from revix_api.middleware import (
    REQUEST_ID_HEADER,
    RESPONSE_TIME_HEADER,
    SECURITY_HEADERS,
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)


@pytest.fixture
def client() -> TestClient:
    # raise_server_exceptions=False so the catch-all handler can be observed
    # doing its job. With the default, the test client re-raises and we would
    # be testing pytest rather than the middleware.
    return TestClient(app, raise_server_exceptions=False)


def test_security_headers_on_every_response(client: TestClient) -> None:
    response = client.get("/health")
    for name, value in SECURITY_HEADERS.items():
        assert response.headers.get(name) == value, name


def test_security_headers_survive_an_error(client: TestClient) -> None:
    """A 404 is still a response somebody's browser will act on."""
    response = client.get("/no-such-endpoint")
    assert response.status_code == 404
    assert response.headers.get("X-Content-Type-Options") == "nosniff"


def test_every_response_is_identified_and_timed(client: TestClient) -> None:
    response = client.get("/health")
    assert len(response.headers.get(REQUEST_ID_HEADER, "")) == 12
    assert float(response.headers[RESPONSE_TIME_HEADER]) >= 0


def test_a_caller_supplied_request_id_is_kept(client: TestClient) -> None:
    """So a trace started in the browser survives into the API's logs."""
    response = client.get("/health", headers={REQUEST_ID_HEADER: "abc123def456"})
    assert response.headers[REQUEST_ID_HEADER] == "abc123def456"


def test_health_is_never_cached(client: TestClient) -> None:
    assert client.get("/health").headers["Cache-Control"] == "no-store"


def test_unhandled_errors_do_not_leak_a_traceback() -> None:
    """The shape of a 500, which is the response we least want to improvise."""
    app_under_test = FastAPI()
    app_under_test.add_middleware(RequestContextMiddleware)

    @app_under_test.get("/boom")
    def boom() -> None:
        raise RuntimeError("a secret path C:/Users/somebody/revix/.env")

    client = TestClient(app_under_test, raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == "The server could not complete this request."
    assert body["request_id"] == response.headers[REQUEST_ID_HEADER]
    assert "secret path" not in response.text
    assert "RuntimeError" not in response.text


def _limited_app(limit: int) -> TestClient:
    app_under_test = FastAPI()
    # The same order main.py uses, and the order is the point. Starlette runs
    # the last one added on the outside, so security headers must be added
    # after the rate limiter to end up wrapping it. Added the other way round,
    # a 429 short-circuits before the headers are applied and the one response
    # most likely to be sent to an unfriendly client is the one response that
    # goes out bare.
    app_under_test.add_middleware(RateLimitMiddleware, limit=limit)
    app_under_test.add_middleware(SecurityHeadersMiddleware)
    app_under_test.add_middleware(RequestContextMiddleware)

    @app_under_test.get("/thing")
    def thing() -> dict[str, bool]:
        return {"ok": True}

    @app_under_test.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app_under_test)


def test_the_limit_holds_and_then_refuses() -> None:
    client = _limited_app(limit=3)
    for _ in range(3):
        assert client.get("/thing").status_code == 200

    refused = client.get("/thing")
    assert refused.status_code == 429
    assert int(refused.headers["Retry-After"]) >= 1
    # A refusal a caller can act on: what the limit is and when to come back.
    assert "3 requests per 60s" in refused.json()["detail"]


def test_the_remaining_budget_is_published() -> None:
    """So a well-behaved client can slow down before it is refused."""
    client = _limited_app(limit=5)
    first = client.get("/thing")
    assert first.headers["X-RateLimit-Limit"] == "5"
    assert first.headers["X-RateLimit-Remaining"] == "4"
    assert client.get("/thing").headers["X-RateLimit-Remaining"] == "3"


def test_health_is_exempt_from_the_limit() -> None:
    """Rate limiting the health check would take the instance down to save it."""
    client = _limited_app(limit=2)
    for _ in range(10):
        assert client.get("/health").status_code == 200


def test_clients_are_counted_separately() -> None:
    """One noisy caller must not spend everybody else's allowance."""
    client = _limited_app(limit=2)
    for _ in range(2):
        client.get("/thing", headers={"X-Forwarded-For": "10.0.0.1"})
    assert client.get("/thing", headers={"X-Forwarded-For": "10.0.0.1"}).status_code == 429
    assert client.get("/thing", headers={"X-Forwarded-For": "10.0.0.2"}).status_code == 200


def test_a_refusal_is_still_identified() -> None:
    """A 429 without a request id is a support ticket nobody can answer."""
    client = _limited_app(limit=1)
    client.get("/thing")
    refused = client.get("/thing")
    assert refused.json()["request_id"] == refused.headers[REQUEST_ID_HEADER]
    assert refused.headers["X-Content-Type-Options"] == "nosniff"


def test_large_responses_are_compressed() -> None:
    """The catalogue is the response that actually costs bytes on a phone."""
    app_under_test = FastAPI()
    from fastapi.middleware.gzip import GZipMiddleware

    app_under_test.add_middleware(GZipMiddleware, minimum_size=500)

    payload = [{"variant": f"variant {i}", "score": 4.1} for i in range(200)]

    @app_under_test.get("/big")
    def big() -> list[dict[str, object]]:
        return payload

    client = TestClient(app_under_test)
    compressed = client.get("/big", headers={"Accept-Encoding": "gzip"})
    plain = client.get("/big", headers={"Accept-Encoding": "identity"})

    assert compressed.headers["Content-Encoding"] == "gzip"
    assert "Content-Encoding" not in plain.headers
    # httpx decodes for us, so compare the wire sizes directly.
    on_the_wire = len(gzip.compress(json.dumps(payload, separators=(",", ":")).encode()))
    assert on_the_wire < len(plain.content) / 2


def test_small_responses_are_left_alone() -> None:
    """Compressing a 40-byte body spends CPU to save nothing."""
    client = TestClient(app)
    response = client.get("/health", headers={"Accept-Encoding": "gzip"})
    assert "Content-Encoding" not in response.headers
