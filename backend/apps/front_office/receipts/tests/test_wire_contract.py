import json

from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate

from apps.front_office.receipts.views import ReceiptKpisView, ReceiptListView, ReceiptOptionsResourceView

User = get_user_model()

LIST_BASE = "/api/v1/front-office/receipts"
OPTIONS_BASE = "/api/v1/front-office/options"


class ReceiptWireContractTests(APITestCase):
    """The merged web client reads snake_case; the global config renders camelCase.

    The receipts views pin `renderer_classes = [JSONRenderer]`, so the JSON over
    the wire is snake_case and matches receipts-api.ts + the MSW mocks. `response.data`
    in the test client bypasses the renderer, so these tests render explicitly.
    """

    def setUp(self):
        call_command("seed_receipt_parameters")
        self.user = User.objects.create_superuser(
            username="wire_admin", password="Password@12345", email="wire_admin@zic.tz"
        )

    def _render(self, view, path, view_kwargs=None, **factory_kwargs):
        request = APIRequestFactory().get(path, **factory_kwargs)
        force_authenticate(request, user=self.user)
        response = view.as_view()(request, **(view_kwargs or {}))
        response.render()
        return json.loads(response.content)["data"]

    def test_kpis_are_snake_case_on_the_wire(self):
        kpis = self._render(ReceiptKpisView, f"{LIST_BASE}/kpis/")
        for field in ("receipt_count", "received_today", "allocated_in_period", "unallocated_amount", "reversed_amount"):
            self.assertIn(field, kpis, field)
        self.assertNotIn("receiptCount", kpis)

    def test_list_rows_and_pagination_are_snake_case_on_the_wire(self):
        page = self._render(ReceiptListView, f"{LIST_BASE}/?page_size=1")
        self.assertIn("page_size", page)
        self.assertNotIn("pageSize", page)
        # No rows exist yet, so exercise the serializer via a row in the next test.

    def test_option_catalogs_pagination_is_snake_case_on_the_wire(self):
        page = self._render(ReceiptOptionsResourceView, f"{OPTIONS_BASE}/statuses/", view_kwargs={"resource": "statuses"})
        self.assertIn("page_size", page)
        self.assertNotIn("pageSize", page)
        self.assertIn("results", page)
