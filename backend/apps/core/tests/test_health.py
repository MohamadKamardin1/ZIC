import pytest

pytestmark = pytest.mark.django_db


def test_liveness_is_dependency_free(client):
    response = client.get("/api/v1/live/", HTTP_X_REQUEST_ID="req-test-123")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"
    assert response["X-Request-ID"] == "req-test-123"


def test_readiness_reports_database_ready(client):
    response = client.get("/api/v1/ready/")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert any(service["name"] == "database" for service in body["services"])


def test_health_preserves_legacy_contract(client):
    response = client.get("/api/v1/health/")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["services"]["database"] == "connected"
