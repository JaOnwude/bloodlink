"""Tests for the service health endpoints and basic application wiring."""

from fastapi.testclient import TestClient

from app import __version__
from app.core.config import get_settings
from app.main import app

client = TestClient(app)
PREFIX = get_settings().api_prefix


def test_liveness_reports_service_details() -> None:
    """The liveness probe answers without needing a database and names the service."""
    response = client.get(f"{PREFIX}/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["service"]


def test_unknown_route_returns_not_found() -> None:
    """Unmapped paths produce a 404 rather than a server error."""
    assert client.get(f"{PREFIX}/does-not-exist").status_code == 404


def test_cors_allows_the_configured_frontend_origin() -> None:
    """A browser preflight from the local frontend is accepted with credentials enabled."""
    response = client.options(
        f"{PREFIX}/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"
