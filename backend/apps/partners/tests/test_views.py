from datetime import date

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.models import User
from apps.partners.models import Partner


def create_test_user(**kwargs):
    defaults = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
    }
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def create_admin_user(**kwargs):
    defaults = {
        "email": "admin@example.com",
        "username": "adminuser",
        "password": "AdminPassword123!",
        "first_name": "Admin",
        "last_name": "User",
        "is_superuser": True,
    }
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def create_partner(**overrides):
    defaults = {
        "partner_number": "PN-2026-000001",
        "partner_type": "INDIVIDUAL",
        "first_name": "John",
        "surname": "Doe",
        "email": "john@example.com",
        "mobile_number": "+255700000001",
        "status": "ACTIVE",
    }
    defaults.update(overrides)
    return Partner.objects.create(**defaults)


class PartnerListViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_test_user()
        self.client.force_authenticate(user=self.user)

    def test_list_partners(self):
        create_partner()
        url = reverse("v1:partners-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertIn("data", response.data)

    def test_unauthenticated_list_rejected(self):
        self.client.force_authenticate(user=None)
        url = reverse("v1:partners-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

    def test_filter_by_partner_type(self):
        create_partner(partner_number="PN-2026-000001", partner_type="INDIVIDUAL", email="ind@example.com")
        create_partner(partner_number="PN-2026-000002", partner_type="CORPORATE", company_name="Corp", email="corp@example.com")
        url = reverse("v1:partners-list") + "?partner_type=INDIVIDUAL"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 1)

    def test_filter_by_status(self):
        create_partner(partner_number="PN-2026-000001", status="ACTIVE", email="active@example.com")
        create_partner(partner_number="PN-2026-000002", status="INACTIVE", email="inactive@example.com")
        url = reverse("v1:partners-list") + "?status=ACTIVE"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 1)

    def test_search_by_partner_number(self):
        create_partner(partner_number="PN-2026-000001")
        url = reverse("v1:partners-list") + "?search=PN-2026"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 1)


class PartnerDetailViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_test_user()
        self.client.force_authenticate(user=self.user)
        self.partner = create_partner()

    def test_retrieve_partner(self):
        url = reverse("v1:partners-detail", args=[self.partner.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertIn("contacts", response.data["data"])
        self.assertIn("bank_accounts", response.data["data"])


class PartnerCreateViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = create_admin_user()
        self.client.force_authenticate(user=self.admin)

    def test_direct_create_blocked(self):
        url = reverse("v1:partners-list")
        data = {
            "partner_number": "PN-2026-999999",
            "partner_type": "INDIVIDUAL",
            "email": "direct@example.com",
            "mobile_number": "+255799999999",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 405)


class PartnerDestroyViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = create_admin_user()
        self.client.force_authenticate(user=self.admin)
        self.partner = create_partner()

    def test_destroy_blocked(self):
        url = reverse("v1:partners-detail", args=[self.partner.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 405)


class PartnerDeactivateViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = create_admin_user()
        self.client.force_authenticate(user=self.admin)
        self.partner = create_partner(status="ACTIVE")

    def test_deactivate_partner(self):
        url = reverse("v1:partners-deactivate", args=[self.partner.id])
        data = {"reason": "Non-compliance"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.partner.refresh_from_db()
        self.assertEqual(self.partner.status, "INACTIVE")
        self.assertIsNotNone(self.partner.deactivated_at)
        self.assertEqual(self.partner.deactivation_reason, "Non-compliance")

    def test_deactivate_already_inactive(self):
        self.partner.status = "INACTIVE"
        self.partner.save()
        url = reverse("v1:partners-deactivate", args=[self.partner.id])
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 400)

    def test_deactivate_non_admin_rejected(self):
        user = create_test_user(username="normaluser")
        self.client.force_authenticate(user=user)
        url = reverse("v1:partners-deactivate", args=[self.partner.id])
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 403)


class PartnerActivateViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = create_admin_user()
        self.client.force_authenticate(user=self.admin)
        self.partner = create_partner(status="INACTIVE")

    def test_activate_partner(self):
        url = reverse("v1:partners-activate", args=[self.partner.id])
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.partner.refresh_from_db()
        self.assertEqual(self.partner.status, "ACTIVE")
        self.assertIsNotNone(self.partner.activated_at)

    def test_activate_already_active(self):
        self.partner.status = "ACTIVE"
        self.partner.save()
        url = reverse("v1:partners-activate", args=[self.partner.id])
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 400)
