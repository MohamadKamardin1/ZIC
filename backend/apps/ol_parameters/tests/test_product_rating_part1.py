from datetime import date
from decimal import Decimal

from django.contrib import admin
from django.core import management
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.governance.models import AuditLog
from apps.ol_parameters.models import (
    OLJointLifeSetup,
    OLMortalityRateRow,
    OLMortalityRateTable,
    OLParameterTableRegistry,
    OLProduct,
    OLPremiumRateRow,
    OLPremiumRateTable,
    OLPlanType,
)
from apps.users.models import User


class OLProductRatingPart1Tests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="ol-rating-admin",
            email="ol-rating-admin@example.com",
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

    def premium_table_payload(self, code="STANDARD_PREMIUM"):
        return {
            "table_code": code,
            "name": "Standard Premium Table",
            "description": "Premium table for the standard product.",
            "product": str(self.product.pk),
            "rating_basis": "AGE_TERM",
            "currency": "TZS",
            "version": "1.0",
            "effective_from": "2026-01-01",
            "is_active": True,
        }

    def premium_row_payload(self, table, code="PREM_M_NS_18_65_5_30"):
        return {
            "code": code,
            "name": "Male Non-Smoker Annual Premium",
            "description": "Premium row.",
            "table": str(table.pk),
            "gender": "M",
            "smoker_status": "NS",
            "age_from": 18,
            "age_to": 65,
            "term_from": 5,
            "term_to": 30,
            "frequency": "ANNUAL",
            "sum_assured_band_from": None,
            "sum_assured_band_to": None,
            "rate": "12.50000000",
            "rate_unit": "PER_THOUSAND_SUM_ASSURED",
            "effective_from": "2026-01-01",
            "is_active": True,
        }

    def mortality_table_payload(self, code="STANDARD_MORTALITY"):
        return {
            "table_code": code,
            "name": "Standard Mortality Table",
            "description": "Mortality table.",
            "version": "1.0",
            "effective_from": "2026-01-01",
            "is_active": True,
        }

    def mortality_row_payload(self, table, code="MORT_18_M_NS"):
        return {
            "code": code,
            "name": "Age 18 Male Non-Smoker",
            "description": "Mortality row.",
            "table": str(table.pk),
            "age": 18,
            "gender": "M",
            "smoker_status": "NS",
            "policy_year": None,
            "mortality_rate": "0.001200000000",
            "effective_from": "2026-01-01",
            "is_active": True,
        }

    def test_premium_table_and_row_crud_filter_and_export(self):
        table_response = self.client.post(
            "/api/v1/ol-parameters/premium-rate-tables/",
            self.premium_table_payload(),
            format="json",
            HTTP_X_REQUEST_ID="premium-table-create",
        )
        self.assertEqual(table_response.status_code, 201, table_response.data)
        table = OLPremiumRateTable.objects.get(table_code="STANDARD_PREMIUM")
        self.assertEqual(table_response.data["version"], "1.0")

        row_response = self.client.post(
            "/api/v1/ol-parameters/premium-rate-rows/",
            self.premium_row_payload(table),
            format="json",
            HTTP_X_REQUEST_ID="premium-row-create",
        )
        self.assertEqual(row_response.status_code, 201, row_response.data)
        row = OLPremiumRateRow.objects.get(code="PREM_M_NS_18_65_5_30")
        self.assertEqual(Decimal(row_response.data["rate"]), Decimal("12.50000000"))

        update_response = self.client.patch(
            f"/api/v1/ol-parameters/premium-rate-rows/{row.pk}/",
            {"rate": "13.50000000"},
            format="json",
            HTTP_X_REQUEST_ID="premium-row-update",
        )
        self.assertEqual(update_response.status_code, 200, update_response.data)
        self.assertEqual(Decimal(update_response.data["rate"]), Decimal("13.50000000"))

        list_response = self.client.get(
            "/api/v1/ol-parameters/premium-rate-rows/?gender=M&smoker_status=NS&age_from=18&term_to=30&frequency=ANNUAL"
        )
        self.assertEqual(list_response.status_code, 200, list_response.data)
        self.assertEqual([item["code"] for item in list_response.data["data"]], ["PREM_M_NS_18_65_5_30"])

        export_response = self.client.get("/api/v1/ol-parameters/premium-rate-tables/export/")
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("STANDARD_PREMIUM", export_response.content.decode())
        self.assertTrue(AuditLog.objects.filter(model_name="olpremiumratetable", action="CREATE", correlation_id="premium-table-create").exists())
        self.assertTrue(AuditLog.objects.filter(model_name="olpremiumraterow", action="CREATE", correlation_id="premium-row-create").exists())
        self.assertTrue(AuditLog.objects.filter(model_name="olpremiumraterow", action="UPDATE", correlation_id="premium-row-update").exists())

    def test_mortality_table_row_crud_filters_and_bulk_import(self):
        table_response = self.client.post(
            "/api/v1/ol-parameters/mortality-rate-tables/",
            self.mortality_table_payload(),
            format="json",
        )
        self.assertEqual(table_response.status_code, 201, table_response.data)
        table = OLMortalityRateTable.objects.get(table_code="STANDARD_MORTALITY")

        row_response = self.client.post(
            "/api/v1/ol-parameters/mortality-rate-rows/",
            self.mortality_row_payload(table),
            format="json",
        )
        self.assertEqual(row_response.status_code, 201, row_response.data)
        row = OLMortalityRateRow.objects.get(code="MORT_18_M_NS")
        self.assertEqual(Decimal(row_response.data["mortality_rate"]), Decimal("0.001200000000"))

        update_response = self.client.patch(
            f"/api/v1/ol-parameters/mortality-rate-rows/{row.pk}/",
            {"mortality_rate": "0.001300000000"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200, update_response.data)

        bulk_response = self.client.post(
            "/api/v1/ol-parameters/mortality-rate-rows/bulk-import/",
            {
                "rows": [
                    {
                        **self.mortality_row_payload(table, "MORT_19_F_SMOKER"),
                        "name": "Age 19 Female Smoker",
                        "age": 19,
                        "gender": "F",
                        "smoker_status": "SMOKER",
                        "mortality_rate": "0.001500000000",
                    },
                    {
                        **self.mortality_row_payload(table, "MORT_20_M_NS"),
                        "name": "Age 20 Male Non-Smoker",
                        "age": 20,
                        "mortality_rate": "0.001700000000",
                    },
                ]
            },
            format="json",
        )
        self.assertEqual(bulk_response.status_code, 201, bulk_response.data)
        self.assertEqual(len(bulk_response.data), 2)
        self.assertEqual(OLMortalityRateRow.objects.filter(table=table).count(), 3)

        list_response = self.client.get("/api/v1/ol-parameters/mortality-rate-rows/?age=19&gender=F&smoker_status=SMOKER")
        self.assertEqual(list_response.status_code, 200, list_response.data)
        self.assertEqual([item["code"] for item in list_response.data["data"]], ["MORT_19_F_SMOKER"])
        export_response = self.client.get("/api/v1/ol-parameters/mortality-rate-rows/export/")
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("MORT_19_F_SMOKER", export_response.content.decode())

    def test_joint_life_setup_crud_and_filter(self):
        payload = {
            "code": "JOINT_FIRST_DEATH",
            "name": "Joint First Death",
            "description": "Joint-life setup.",
            "product": str(self.product.pk),
            "plan": None,
            "joint_life_type": "FIRST_DEATH",
            "age_basis": "YOUNGER_LIFE",
            "survivor_benefit_rule": "PAY_ON_FIRST_DEATH",
            "premium_adjustment_factor": "1.150000",
            "underwriting_rule": "FULL_UNDERWRITING",
            "effective_from": "2026-01-01",
            "is_active": True,
        }
        create_response = self.client.post("/api/v1/ol-parameters/joint-life-setups/", payload, format="json")
        self.assertEqual(create_response.status_code, 201, create_response.data)
        setup = OLJointLifeSetup.objects.get(code="JOINT_FIRST_DEATH")
        self.assertEqual(Decimal(create_response.data["premium_adjustment_factor"]), Decimal("1.150000"))

        update_response = self.client.patch(
            f"/api/v1/ol-parameters/joint-life-setups/{setup.pk}/",
            {"premium_adjustment_factor": "1.200000"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200, update_response.data)
        list_response = self.client.get("/api/v1/ol-parameters/joint-life-setups/?joint_life_type=FIRST_DEATH&product=" + str(self.product.pk))
        self.assertEqual(list_response.status_code, 200, list_response.data)
        self.assertEqual([item["code"] for item in list_response.data["data"]], ["JOINT_FIRST_DEATH"])

    def test_rating_invariants_reject_invalid_bands_rates_scopes_and_overlaps(self):
        premium_table = OLPremiumRateTable(
            table_code="PREM_INVALID",
            name="Invalid Premium",
            product=self.product,
            rating_basis="AGE_TERM",
            currency="TZS",
            version="1.0",
            effective_from=date(2026, 1, 1),
        )
        premium_table.full_clean()
        premium_table.save()
        invalid_row = OLPremiumRateRow(
            code="PREM_INVALID_ROW",
            name="Invalid Premium Row",
            table=premium_table,
            gender="M",
            smoker_status="NS",
            age_from=70,
            age_to=65,
            term_from=10,
            term_to=5,
            frequency="ANNUAL",
            rate=Decimal("101"),
            rate_unit="PERCENTAGE",
            effective_from=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            invalid_row.full_clean()

        first = OLPremiumRateRow(
            **{**self.premium_row_payload(premium_table, "PREM_OVERLAP_1"), "table": premium_table, "effective_from": date(2026, 1, 1), "rate": Decimal("10")}
        )
        first.full_clean()
        first.save()
        second = OLPremiumRateRow(
            **{**self.premium_row_payload(premium_table, "PREM_OVERLAP_2"), "table": premium_table, "effective_from": date(2026, 6, 1), "rate": Decimal("11")}
        )
        with self.assertRaises(ValidationError):
            second.full_clean()

        mortality_table = OLMortalityRateTable(
            table_code="MORT_INVALID",
            name="Invalid Mortality",
            version="1.0",
            effective_from=date(2026, 1, 1),
        )
        mortality_table.full_clean()
        mortality_table.save()
        invalid_mortality = OLMortalityRateRow(
            code="MORT_INVALID_ROW",
            name="Invalid Mortality Row",
            table=mortality_table,
            age=151,
            gender="M",
            mortality_rate=Decimal("-0.01"),
            effective_from=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            invalid_mortality.full_clean()

        invalid_joint = OLJointLifeSetup(
            code="JOINT_INVALID",
            name="Invalid Joint",
            joint_life_type="FIRST_DEATH",
            age_basis="YOUNGER_LIFE",
            survivor_benefit_rule="PAY",
            premium_adjustment_factor=Decimal("0"),
            underwriting_rule="FULL",
            effective_from=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            invalid_joint.full_clean()

    def test_permission_is_required_for_product_rating(self):
        restricted_user = User.objects.create_user(
            username="ol-rating-viewer",
            email="ol-rating-viewer@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
        )
        restricted_client = APIClient()
        restricted_client.force_authenticate(restricted_user)
        for endpoint in (
            "/api/v1/ol-parameters/premium-rate-tables/",
            "/api/v1/ol-parameters/premium-rate-rows/",
            "/api/v1/ol-parameters/mortality-rate-tables/",
            "/api/v1/ol-parameters/mortality-rate-rows/",
            "/api/v1/ol-parameters/joint-life-setups/",
        ):
            self.assertEqual(restricted_client.get(endpoint).status_code, 403, endpoint)

    def test_rating_seed_command_is_idempotent_and_registers_all_resources(self):
        management.call_command("seed_ol_product_rating")
        first_counts = (
            OLPremiumRateTable.objects.count(),
            OLPremiumRateRow.objects.count(),
            OLMortalityRateTable.objects.count(),
            OLMortalityRateRow.objects.count(),
            OLJointLifeSetup.objects.count(),
            OLParameterTableRegistry.objects.filter(parameter_group="PRODUCT_RATING").count(),
        )
        management.call_command("seed_ol_product_rating")
        second_counts = (
            OLPremiumRateTable.objects.count(),
            OLPremiumRateRow.objects.count(),
            OLMortalityRateTable.objects.count(),
            OLMortalityRateRow.objects.count(),
            OLJointLifeSetup.objects.count(),
            OLParameterTableRegistry.objects.filter(parameter_group="PRODUCT_RATING").count(),
        )
        self.assertEqual(first_counts, second_counts)
        self.assertEqual(first_counts, (1, 1, 1, 1, 1, 5))

    def test_all_product_rating_models_are_registered_with_admin(self):
        for model in (OLPremiumRateTable, OLPremiumRateRow, OLMortalityRateTable, OLMortalityRateRow, OLJointLifeSetup):
            self.assertIn(model, admin.site._registry)
            self.assertTrue(admin.site._registry[model].has_view_permission(type("Request", (), {"user": self.user})()))
