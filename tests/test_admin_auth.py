"""The gate on the operations surface.

Everything here is about the door rather than the rooms behind it. The rooms
are ordinary reads and the database-marked tests cover those; the door is the
part where a mistake is not a bug report, it is an open admin console on the
public internet.

get_settings is cached, so every test clears it. Without that, the first test
to read settings fixes them for the rest of the session and the "not
configured" case passes for the wrong reason.
"""

from __future__ import annotations

import base64
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
def _clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _auth(username: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _configure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "operator")
    monkeypatch.setenv("ADMIN_PASSWORD", "a-real-password")
    get_settings.cache_clear()


# ---------- fails closed ----------


@pytest.mark.parametrize("route", READ_ROUTES)
def test_unconfigured_admin_refuses_rather_than_opens(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    """The most important test in the file.

    A deployment that has not set the credentials must not serve operational
    data to anybody who asks. 503 and not 200, on every route, with no
    exceptions for the cheap ones.
    """
    monkeypatch.setenv("ADMIN_USERNAME", "")
    monkeypatch.setenv("ADMIN_PASSWORD", "")
    get_settings.cache_clear()

    response = client.get(route)
    assert response.status_code == 503, route
    assert "ADMIN_USERNAME" in response.json()["detail"]


def test_half_configured_is_treated_as_unconfigured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Somebody who set one and forgot the other meant to protect this."""
    monkeypatch.setenv("ADMIN_USERNAME", "operator")
    monkeypatch.setenv("ADMIN_PASSWORD", "")
    get_settings.cache_clear()

    assert client.get("/admin/whoami").status_code == 503


# ---------- rejects the wrong credentials ----------


@pytest.mark.parametrize("route", READ_ROUTES)
def test_no_credentials_is_refused(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    _configure(monkeypatch)
    assert client.get(route).status_code == 401, route


def test_wrong_password_is_refused(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch)
    response = client.get("/admin/whoami", headers=_auth("operator", "guess"))
    assert response.status_code == 401


def test_wrong_username_is_refused(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch)
    response = client.get("/admin/whoami", headers=_auth("admin", "a-real-password"))
    assert response.status_code == 401


def test_a_refusal_tells_the_browser_to_ask(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without this header a human opening the URL sees a dead end."""
    _configure(monkeypatch)
    response = client.get("/admin/whoami")
    assert response.headers["WWW-Authenticate"].startswith("Basic")


def test_the_password_is_never_echoed(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch)
    response = client.get("/admin/whoami", headers=_auth("operator", "a-real-password"))
    assert "a-real-password" not in response.text


# ---------- accepts the right ones ----------


def test_correct_credentials_are_accepted(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure(monkeypatch)
    response = client.get("/admin/whoami", headers=_auth("operator", "a-real-password"))
    assert response.status_code == 200
    assert response.json() == {"username": "operator", "authenticated": True}


# ---------- the surface behaves like the rest of the API ----------


def test_admin_is_never_cached(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """A stale operations console is worse than none: confidently wrong."""
    _configure(monkeypatch)
    response = client.get("/admin/whoami", headers=_auth("operator", "a-real-password"))
    assert response.headers["Cache-Control"] == "no-store"


def test_a_refusal_still_carries_the_security_headers(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The one surface people try passwords against must not go out bare."""
    _configure(monkeypatch)
    response = client.get("/admin/whoami")
    assert response.status_code == 401
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert len(response.headers["X-Request-ID"]) == 12


def test_the_write_route_is_also_gated(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """The only endpoint in the project that writes, and it needs the door."""
    _configure(monkeypatch)
    listing = "00000000-0000-0000-0000-000000000000"
    assert client.post(f"/admin/adjudication/{listing}", json={}).status_code == 401


def test_public_endpoints_are_unaffected(client: TestClient) -> None:
    """Adding an authenticated surface must not gate the read-only one."""
    assert client.get("/health").status_code in (200, 503)


def test_admin_routes_are_documented_as_a_group() -> None:
    """So the OpenAPI page shows an operator what exists without a tour."""
    paths = app.openapi()["paths"]
    admin = [p for p in paths if p.startswith("/admin")]
    assert len(admin) == 8, admin
    for path in admin:
        for method in paths[path].values():
            assert method["tags"] == ["admin"]
