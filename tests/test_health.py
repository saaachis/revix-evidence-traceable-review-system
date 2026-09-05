"""The health endpoint, including the case that only happens in production.

A health check is the one endpoint whose failure mode matters more than its
success. Locally the database is always up, so the interesting path here is
the one nobody sees until a deploy goes wrong.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from revix_api.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_an_unreachable_database_is_reported_rather_than_raised(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """503 and a structured body, not 500 and a stack trace.

    The endpoint deliberately opens its own session instead of taking the
    dependency, because a dependency that raises fails before the handler runs
    and there is then nothing to report with.
    """

    def explode(*_args: object, **_kwargs: object) -> object:
        raise OperationalError("select 1", {}, Exception("connection refused"))

    monkeypatch.setattr("revix_api.main.session_scope", explode)
    response = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["database"] is False
    assert body["status"] == "degraded"
    assert "Traceback" not in response.text


def test_the_failure_shape_matches_the_success_shape(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """So a caller parses one schema rather than branching on the status."""

    def explode(*_args: object, **_kwargs: object) -> object:
        raise OperationalError("select 1", {}, Exception("down"))

    monkeypatch.setattr("revix_api.main.session_scope", explode)
    assert set(client.get("/health").json()) == {"status", "database", "variants", "verdicts"}
