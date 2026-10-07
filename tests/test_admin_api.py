"""The admin surface behind the door, with the door opened.

test_admin_auth covers the gate: who is turned away. This covers the rooms:
with the operator credentials configured and a populated database, each read
endpoint answers, and the one write endpoint reaches its handler. Marked ``db``
and skips without Postgres through the shared ``engine`` fixture.
"""

from __future__ import annotations

import base64
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from revix_api.main import app
from revix_core.settings import get_settings

READ_ROUTES = [
    "/admin/whoami",
    "/admin/connectors",
    "/admin/runs",
    "/admin/freshness",
    "/admin/coverage",
    "/admin/adjudication",
    "/admin/fusion-configs",
]


@pytest.fixture(autouse=True)
def _configured_admin(engine: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Configure the operator and ensure a database, or skip."""
    monkeypatch.setenv("ADMIN_USERNAME", "operator")
    monkeypatch.setenv("ADMIN_PASSWORD", "a-real-password")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _auth() -> dict[str, str]:
    token = base64.b64encode(b"operator:a-real-password").decode()
    return {"Authorization": f"Basic {token}"}


@pytest.mark.parametrize("route", READ_ROUTES)
def test_each_read_route_answers_for_the_operator(client: TestClient, route: str) -> None:
    response = client.get(route, headers=_auth())
    assert response.status_code == 200, f"{route}: {response.text[:200]}"


def test_connector_health_lists_the_registered_sources(client: TestClient) -> None:
    body = client.get("/admin/connectors", headers=_auth()).json()
    assert isinstance(body, list) and body
    assert "source_key" in body[0]


def test_runs_accepts_filters(client: TestClient) -> None:
    response = client.get(
        "/admin/runs", params={"source": "fixture_owner", "limit": 5}, headers=_auth()
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_coverage_can_show_everything_not_only_suppressed(client: TestClient) -> None:
    response = client.get(
        "/admin/coverage", params={"only_suppressed": False, "limit": 10}, headers=_auth()
    )
    assert response.status_code == 200


def test_fusion_configs_reports_the_three_strategies(client: TestClient) -> None:
    body = client.get("/admin/fusion-configs", headers=_auth()).json()
    assert len(body) == 3


def test_adjudicating_an_unknown_listing_is_a_not_found(client: TestClient) -> None:
    # A valid body (all fields optional) so the request reaches the handler,
    # then a listing id that does not exist exercises the lookup and its 404.
    missing = uuid.uuid4()
    response = client.post(
        f"/admin/adjudication/{missing}", json={"is_rejection": True}, headers=_auth()
    )
    assert response.status_code == 404
