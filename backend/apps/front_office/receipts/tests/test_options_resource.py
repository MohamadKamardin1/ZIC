from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.partner_onboarding.models import Branch
from apps.partners.models import Partner

User = get_user_model()

ROOT = "/api/v1/front-office/options"
RECEIPTS = "/api/v1/front-office/receipts/options"


def _page(response):
    return response.data["data"]


class ReceiptOptionsResourceTests(APITestCase):
    """The web SmartSelect contract (receipts-api.ts RECEIPTS_OPTIONS_BASE).

    The manus client and MSW mocks mount the option catalogs at the front-office
    root (/api/v1/front-office/options/...), not under /receipts/. The root
    routes are the primary contract; the receipts-prefixed routes stay as
    compatibility aliases.
    """

    def setUp(self):
        call_command("seed_receipt_parameters")
        self.admin = User.objects.create_superuser(
            username="opt_admin", password="Password@12345", email="opt_admin@zic.tz"
        )
        self.viewer = User.objects.create_user(
            username="opt_viewer", password="Password@12345", email="opt_viewer@zic.tz"
        )
        self.branch = Branch.objects.create(code="DAR", name="Dar es Salaam")
        self.partner = Partner.objects.create(
            partner_number="OPT0001",
            partner_type="INDIVIDUAL",
            party_type="INDIVIDUAL",
            first_name="Jane",
            surname="Doe",
            email="opt@zic.tz",
            mobile_number="255700000001",
            is_active=True,
            status="ACTIVE",
        )

    def _get(self, path, user=None):
        self.client.force_authenticate(user or self.admin)
        return self.client.get(path)

    def test_all_option_catalogs_serve_paginated_shape_at_root(self):
        for resource in (
            "branches",
            "payers",
            "proposals",
            "source-modules",
            "currencies",
            "payment-modes",
            "bank-accounts",
            "statuses",
        ):
            response = self._get(f"{ROOT}/{resource}/")
            self.assertEqual(response.status_code, 200, (resource, response.data))
            page = _page(response)
            self.assertIsInstance(page["results"], list)
            self.assertIn("count", page)
            self.assertIn("next", page)
            self.assertIn("previous", page)
            self.assertIn("page", page)
            self.assertIn("page_size", page)

    def test_root_alias_has_value_label_options(self):
        response = self._get(f"{ROOT}/branches/")
        results = _page(response)["results"]
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["value"], str(self.branch.pk))
        self.assertEqual(results[0]["label"], "Dar es Salaam")

    def test_receipts_prefixed_aliases_serve_same_contract(self):
        response = self._get(f"{RECEIPTS}/statuses/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", _page(response))

    def test_search_query_narrows_results(self):
        response = self._get(f"{ROOT}/branches/?q=dar")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(_page(response)["results"]), 1)
        response = self._get(f"{ROOT}/branches/?q=zzzz")
        self.assertEqual(len(_page(response)["results"]), 0)

    def test_branch_quick_create_schema_and_create(self):
        schema = self._get(f"{ROOT}/branches/quick-create-schema/")
        self.assertEqual(schema.status_code, 200)
        self.assertEqual(schema.data["data"]["entity"], "branches")
        self.assertEqual(schema.data["data"]["permission"], "front_office.receipts.create")

        created = self.client.post(
            f"{ROOT}/branches/quick-create/", {"code": "MBA", "name": "Mbeya"}, format="json"
        )
        self.assertEqual(created.status_code, 201, created.data)
        option = created.data["data"]["option"]
        self.assertEqual(option["label"], "Mbeya")
        self.assertTrue(Branch.objects.filter(code="MBA", name="Mbeya").exists())

    def test_payer_quick_create(self):
        self.client.force_authenticate(self.admin)
        created = self.client.post(
            f"{ROOT}/payers/quick-create/",
            {"legal_name": "Neema Trading", "national_id": "12345678", "phone": "255700000002"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertTrue(Partner.objects.filter(legal_name="Neema Trading").exists())

    def test_unknown_resource_returns_404(self):
        response = self._get(f"{ROOT}/widgets/")
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.data["success"])
        self.assertTrue(response.data["error_code"])

    def test_viewer_without_permission_gets_403(self):
        self.client.force_authenticate(self.viewer)
        response = self.client.get(f"{ROOT}/branches/")
        self.assertEqual(response.status_code, 403)
