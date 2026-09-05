"""Cross-origin access to the serving layer.

No database, because this is a configuration fact rather than a query. A
preflight is answered by the middleware itself and never reaches a route.

This has its own file because it cost a green build once. The browser treats
"localhost" and "127.0.0.1" as different origins, the API answered the blocked
request with a healthy 200 in its own log, and the only visible symptom was a
search box quietly saying it was unavailable.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from revix_api.main import app
from revix_core.settings import Settings


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.parametrize("origin", ["http://localhost:3000", "http://127.0.0.1:3000"])
def test_the_web_app_may_read_the_api_from_either_loopback_spelling(
    client: TestClient, origin: str
) -> None:
    response = client.options(
        "/variants",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_an_unknown_origin_is_still_refused() -> None:
    """Permissive enough for the dev stack, not a wildcard."""
    assert "*" not in Settings().cors_origins


def test_origins_are_split_and_stripped() -> None:
    settings = Settings(cors_allowed_origins=" http://a.example , http://b.example ")
    assert settings.cors_origins == ["http://a.example", "http://b.example"]
