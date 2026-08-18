from datetime import date
from decimal import Decimal

from django.contrib import admin
from django.core import management
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient

from apps.governance.models import AuditLog
from apps.ol_parameters.models import (
    OLParameterTableRegistry,
    OLPlanType,
    OLProduct,
    OLRiderRateRow,
    OLRiderRateTable,
    OLRiderSetup,
)
from apps.users.models import User


class OLRiderSetupTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="ol-rider-admin",
            email="ol-rider-admin@example.com",
            password="Strong-pass-123!",
            is_superuser=True,
            is_staff=True,
            is_active=True,
            is_approved=True,
        )
        self.client.force_authenticate(self.user)
        self.plan_type = OLPlanType.objects.create(
            code="ENDOWMENT",
            name="Endowment",
            description="Endowment plan type.",
            plan_category="INDIVIDUAL",
            effective_from=date(2026, 1, 1),
        )
        self.product = OLProduct.objects.create(
            code="STANDARD_ENDOWMENT",
            name="Standard Endowment",
            description="Standard endowment product.",
            plan_type=self.plan_type,
            insurance_class="INDIVIDUAL",
            currency="TZS",
            min_entry_age=18,
            max_entry_age=65,
            min_term=5,
            max_term=30,
            min_sum_assured=Decimal("1000000.00"),
            max_sum_assured=Decimal("1000000000.00"),
            premium_frequencies=["MONTHLY", "ANNUAL"],
            allow_riders=True,
            allow_loans=True,
            allow_withdrawals=False,
            allow_surrender=True,
            allow_paidup=True,
            allow_bonus=True,
            investment_linked=False,
            effective_from=date(2026, 1, 1),
        )

    def rider_payload(self, code="ACCIDENTAL_DEATH_RIDER_2026"):
        return {
            "code": code,
            "name": "Accidental Death Rider",
            "description": "Accidental death rider applicability.",
            "rider_category": "ACCIDENT",
            "benefit_type": "ACCIDENTAL_DEATH",
            "calculation_basis": "SUM_ASSURED",
            "min_age": 18,
            "max_age": 65,
            "min_term": 5,
            "max_term": 30,
            "min_sum_assured": "1000000.00",
            "max_sum_assured": "1000000000.00",
            "waiting_period_days": 30,
            "allows_standalone": False,
            "requires_underwriting": True,
            "exclusion_rules": {"codes": ["WAR"]},
            "product": str(self.product.pk),
            "plan": None,
            "effective_from": "2026-01-01",
            "effective_to": None,
            "is_active": True,
        }

    def table_payload(self, rider, table_code="ACCIDENTAL_DEATH_RIDER_RATES"):
        return {
            "table_code": table_code,
            "name": "Accidental Death Rider Rates",
            "description": "Versioned rider rate table.",
            "rider": str(rider.pk),
            "product": str(self.product.pk),
            "plan": None,
            "rating_basis": "AGE_TERM",
            "version": "1.0",
            "effective_from": "2026-01-01",
            "effective_to": None,
            "is_active": True,
        }

    def row_payload(self, table, code="ACCIDENTAL_DEATH_RIDER_RATE_M_NS"):
        return {
            "code": code,
            "name": "Accidental Death Male Non-Smoker Rate",
            "description": "Rider rate row.",
            "table": str(table.pk),
            "gender": "M",
            "smoker_status": "NS",
            "age_from": 18,
            "age_to": 65,
            "term_from": 5,
            "term_to": 30,
            "frequency": "ANNUAL",
            "sum_assured_band_from": "1000000.00",
            "sum_assured_band_to": "1000000000.00",
            "rate": "1.25000000",
            "rate_unit": "PER_THOUSAND_SUM_ASSURED",
            "effective_from": "2026-01-01",
            "effective_to": None,
            "is_active": True,
        }

    def create_resource(self, endpoint, payload, expected=201, request_id=None):
        kwargs = {"format": "json"}
        if request_id:
            kwargs["HTTP_X_REQUEST_ID"] = request_id
        url = endpoint if endpoint.startswith("/") else f"/api/v1/ol-parameters/{endpoint}/"
        response = self.client.post(url, payload, **kwargs)
        self.assertEqual(response.status_code, expected, response.data)
        return response

    def create_rider_and_table(self):
        rider_response = self.create_resource(
            "rider-setups",
            self.rider_payload(),
            request_id="rider-fixture-create",
        )
        rider = OLRiderSetup.objects.get(code="ACCIDENTAL_DEATH_RIDER_2026")
        table_response = self.create_resource(
            "rider-rate-tables",
            self.table_payload(rider),
            request_id="rider-table-fixture-create",
        )
        table = OLRiderRateTable.objects.get(table_code="ACCIDENTAL_DEATH_RIDER_RATES")
        return rider_response, rider, table_response, table

    def test_all_three_resources_support_crud_and_table_filters(self):
        rider_create = self.create_resource("rider-setups", self.rider_payload(), request_id="rider-create")
        rider = OLRiderSetup.objects.get(code="ACCIDENTAL_DEATH_RIDER_2026")
        self.assertEqual(rider_create.status_code, 201)
        rider_patch = self.client.patch(
            f"/api/v1/ol-parameters/rider-setups/{rider.pk}/",
            {"waiting_period_days": 45},
            format="json",
            HTTP_X_REQUEST_ID="rider-update",
        )
        self.assertEqual(rider_patch.status_code, 200, rider_patch.data)

        table_create = self.create_resource(
            "rider-rate-tables",
            self.table_payload(rider),
            request_id="rider-table-create",
        )
        table = OLRiderRateTable.objects.get(table_code="ACCIDENTAL_DEATH_RIDER_RATES")
        self.assertEqual(table_create.status_code, 201)
        table_patch = self.client.patch(
            f"/api/v1/ol-parameters/rider-rate-tables/{table.pk}/",
            {"version": "2.0"},
            format="json",
            HTTP_X_REQUEST_ID="rider-table-update",
        )
        self.assertEqual(table_patch.status_code, 200, table_patch.data)

        row_create = self.create_resource(
            "rider-rate-rows",
            self.row_payload(table),
            request_id="rider-row-create",
        )
        row = OLRiderRateRow.objects.get(code="ACCIDENTAL_DEATH_RIDER_RATE_M_NS")
        self.assertEqual(row_create.status_code, 201)
        row_patch = self.client.patch(
            f"/api/v1/ol-parameters/rider-rate-rows/{row.pk}/",
            {"rate": "1.35000000"},
            format="json",
            HTTP_X_REQUEST_ID="rider-row-update",
        )
        self.assertEqual(row_patch.status_code, 200, row_patch.data)

        for endpoint, query in (
            ("rider-setups", f"product={self.product.pk}&rider_category=ACCIDENT&is_active=true"),
            ("rider-rate-tables", f"rider={rider.pk}&product={self.product.pk}&rating_basis=AGE_TERM"),
            ("rider-rate-rows", f"table={table.pk}&gender=M&smoker_status=NS&frequency=ANNUAL"),
        ):
            listing = self.client.get(
                f"/api/v1/ol-parameters/{endpoint}/?{query}&per_page=1&page=1"
            )
            self.assertEqual(listing.status_code, 200, listing.data)
            self.assertEqual(listing.data["pagination"]["total"], 1)
            self.assertEqual(len(listing.data["data"]), 1)

        for endpoint, record in (
            ("rider-setups", rider),
            ("rider-rate-tables", table),
            ("rider-rate-rows", row),
        ):
            retrieve = self.client.get(f"/api/v1/ol-parameters/{endpoint}/{record.pk}/")
            self.assertEqual(retrieve.status_code, 200, retrieve.data)

    def test_rider_applicability_and_date_validation_reject_invalid_payloads(self):
        invalid_riders = [
            {"max_age": 17},
            {"max_term": 4},
            {"max_sum_assured": "999999.99"},
        ]
        for index, override in enumerate(invalid_riders, start=1):
            self.create_resource(
                "rider-setups",
                {**self.rider_payload(f"INVALID_RIDER_{index}"), **override},
                expected=400,
            )

        invalid_dates = self.rider_payload("INVALID_RIDER_DATES")
        invalid_dates["effective_to"] = "2025-12-31"
        self.create_resource("rider-setups", invalid_dates, expected=400)

        _, rider, _, table = self.create_rider_and_table()
        invalid_rows = [
            {"age_from": 70, "age_to": 69},
            {"term_from": 10, "term_to": 5},
            {"sum_assured_band_from": "1000000.00", "sum_assured_band_to": "999999.99"},
            {"rate": "-1.00000000"},
        ]
        for index, override in enumerate(invalid_rows, start=1):
            self.create_resource(
                "rider-rate-rows",
                {**self.row_payload(table, f"INVALID_RIDER_ROW_{index}"), **override},
                expected=400,
            )
        self.assertEqual(rider.code, "ACCIDENTAL_DEATH_RIDER_2026")

    def test_active_rate_rows_cannot_overlap_same_dimensions(self):
        _, _, _, table = self.create_rider_and_table()
        self.create_resource("rider-rate-rows", self.row_payload(table, "RIDER_ROW_OVERLAP_1"))
        self.create_resource(
            "rider-rate-rows",
            self.row_payload(table, "RIDER_ROW_OVERLAP_2"),
            expected=400,
        )

        first = OLRiderRateRow.objects.get(code="RIDER_ROW_OVERLAP_1")
        second = OLRiderRateRow(
            code="RIDER_ROW_OVERLAP_3",
            name="Overlapping row",
            table=table,
            gender=first.gender,
            smoker_status=first.smoker_status,
            age_from=first.age_from,
            age_to=first.age_to,
            term_from=first.term_from,
            term_to=first.term_to,
            frequency=first.frequency,
            sum_assured_band_from=first.sum_assured_band_from,
            sum_assured_band_to=first.sum_assured_band_to,
            rate=Decimal("1.50000000"),
            rate_unit=first.rate_unit,
            effective_from=date(2026, 6, 1),
        )
        with self.assertRaises(ValidationError):
            second.full_clean()

    def test_permissions_and_audit_logs_are_enforced(self):
        created = self.create_resource(
            "rider-setups",
            self.rider_payload(),
            request_id="rider-audit-create",
        )
        self.assertEqual(created.status_code, 201)
        rider = OLRiderSetup.objects.get(code="ACCIDENTAL_DEATH_RIDER_2026")
        self.assertTrue(
            AuditLog.objects.filter(
                model_name="olridersetup",
                object_id=str(rider.pk),
                action="CREATE",
                correlation_id="rider-audit-create",
            ).exists()
        )

        updated = self.client.patch(
            f"/api/v1/ol-parameters/rider-setups/{rider.pk}/",
            {"waiting_period_days": 60},
            format="json",
            HTTP_X_REQUEST_ID="rider-audit-update",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertTrue(
            AuditLog.objects.filter(
                model_name="olridersetup",
                object_id=str(rider.pk),
                action="UPDATE",
                correlation_id="rider-audit-update",
            ).exists()
        )

        restricted_user = User.objects.create_user(
            username="ol-rider-viewer",
            email="ol-rider-viewer@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
        )
        restricted_client = APIClient()
        restricted_client.force_authenticate(restricted_user)
        for endpoint in ("rider-setups", "rider-rate-tables", "rider-rate-rows"):
            self.assertEqual(
                restricted_client.get(f"/api/v1/ol-parameters/{endpoint}/").status_code,
                403,
                endpoint,
            )

    def test_rider_seed_is_idempotent_and_registers_three_contracts(self):
        management.call_command("seed_ol_rider_setup", verbosity=0)
        first_counts = (
            OLRiderSetup.objects.count(),
            OLRiderRateTable.objects.count(),
            OLRiderRateRow.objects.count(),
            OLParameterTableRegistry.objects.filter(
                slug__in=["rider-setups", "rider-rate-tables", "rider-rate-rows"]
            ).count(),
        )
        management.call_command("seed_ol_rider_setup", verbosity=0)
        second_counts = (
            OLRiderSetup.objects.count(),
            OLRiderRateTable.objects.count(),
            OLRiderRateRow.objects.count(),
            OLParameterTableRegistry.objects.filter(
                slug__in=["rider-setups", "rider-rate-tables", "rider-rate-rows"]
            ).count(),
        )
        self.assertEqual(first_counts, second_counts)
        self.assertEqual(first_counts, (1, 1, 1, 3))

    def test_admin_registration_and_list_display_exist_for_all_rider_models(self):
        request = RequestFactory().get("/admin/")
        request.user = self.user
        for model in (OLRiderSetup, OLRiderRateTable, OLRiderRateRow):
            self.assertIn(model, admin.site._registry)
            model_admin = admin.site._registry[model]
            self.assertTrue(model_admin.has_view_permission(request))
            self.assertTrue(model_admin.list_display)
