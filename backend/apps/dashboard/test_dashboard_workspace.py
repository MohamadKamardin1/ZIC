import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.dashboard.models import CurrencyPair, DashboardAlert, DashboardNotification, DashboardTask
from apps.partners.models import Partner


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        username="dashboard-user",
        email="dashboard@example.com",
        password="SecurePass123!",
        first_name="Dashboard",
        last_name="User",
    )


@pytest.fixture
def other_user(db):
    return get_user_model().objects.create_user(
        username="other-dashboard-user",
        email="other@example.com",
        password="SecurePass123!",
    )


@pytest.fixture
def client(user):
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
def test_task_lifecycle_is_persisted_and_scoped(client, user, other_user):
    response = client.post("/api/v1/dashboard/tasks/", {"title": "Review partner file", "priority": "HIGH"}, format="json")
    assert response.status_code == 201
    task_id = response.data["data"]["id"]
    assert DashboardTask.objects.get(pk=task_id).owner_id == user.id

    completed = client.patch(f"/api/v1/dashboard/tasks/{task_id}/", {"status": "DONE"}, format="json")
    assert completed.status_code == 200
    assert completed.data["data"]["status"] == "DONE"
    assert completed.data["data"]["completedAt"]

    other_client = APIClient()
    other_client.force_authenticate(user=other_user)
    assert other_client.patch(f"/api/v1/dashboard/tasks/{task_id}/", {"title": "Hijack"}, format="json").status_code == 404


@pytest.mark.django_db
def test_alert_actions_and_notification_read_state(client, user):
    alert = DashboardAlert.objects.create(owner=user, title="Document expiry", message="A partner document expires soon", severity="WARNING")
    response = client.post(f"/api/v1/dashboard/alerts/{alert.id}/acknowledge/")
    assert response.status_code == 200
    assert response.data["data"]["status"] == "ACKNOWLEDGED"

    notification = DashboardNotification.objects.create(owner=user, external_key="test:1", title="New activity", message="A test event")
    read = client.post(f"/api/v1/dashboard/notifications/{notification.id}/read/")
    assert read.status_code == 200
    assert read.data["data"]["isRead"] is True


@pytest.mark.django_db
def test_global_search_returns_database_entities_and_canonical_routes(client):
    partner = Partner.objects.create(
        partner_number="PT-SEARCH-001",
        first_name="Amina",
        surname="Searchable",
        email="amina.searchable@example.com",
    )
    response = client.get("/api/v1/dashboard/search/?q=PT-SEARCH-001")
    assert response.status_code == 200
    results = response.data["data"]["results"]
    assert any(item["id"] == str(partner.id) and item["route"] == f"/partners/{partner.id}" for item in results)


@pytest.mark.django_db
def test_currency_pairs_are_unique_per_user_and_isolated(client, user, other_user):
    first = client.post("/api/v1/dashboard/currencies/", {"baseCurrency": "USD", "quoteCurrency": "TZS"}, format="json")
    assert first.status_code == 201
    duplicate = client.post("/api/v1/dashboard/currencies/", {"baseCurrency": "USD", "quoteCurrency": "TZS"}, format="json")
    assert duplicate.status_code in {200, 400}
    assert CurrencyPair.objects.filter(owner=user, base_currency="USD", quote_currency="TZS").count() == 1

    other_client = APIClient()
    other_client.force_authenticate(user=other_user)
    listed = other_client.get("/api/v1/dashboard/currencies/")
    assert listed.status_code == 200
    assert listed.data["data"] == []
