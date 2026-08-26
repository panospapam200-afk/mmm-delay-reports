"""Smoke test του HTTP layer.

Ξεχωριστό από τα tests του πυρήνα: αυτό απαιτεί να σηκωθεί η εφαρμογή FastAPI,
ενώ τα tests του ``app/core`` τρέχουν χωρίς καμία εξάρτηση.
"""

from fastapi.testclient import TestClient

from app import __version__
from app.main import app

client = TestClient(app)


def test_health_endpoint_reports_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_openapi_schema_is_generated() -> None:
    """Το OpenAPI schema χρησιμοποιείται ως τεκμηρίωση API στο παραδοτέο."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["version"] == __version__
