from datetime import date
from decimal import Decimal

from django.contrib import admin
from django.core import management
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from rest_framework.test import APIClient

from apps.governance.models import AuditLog
from apps.ol_parameters.models import (
    OLInvestmentFund,
    OLInvestmentFundType,
    OLPlanOccupationRiskLimit,
    OLPlanRiskCategory,
    OLPlanTargetMarket,
    OLPlanTaxConfiguration,
    OLParameterTableRegistry,
    OLPlanType,
    OLProduct,
)
from apps.users.models import User


class OLProductSetupTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="ol-product-setup-admin",
            email="ol-product-setup-admin@example.com",
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

    def product_payload(self, code="STANDARD_ENDOWMENT"):
        return {
            "code": code,
            "name": "Standard Endowment",
            "description": "A standard table-driven product.",
            "plan_type": str(self.plan_type.pk),
            "insurance_class": "INDIVIDUAL",
            "currency": "TZS",
            "min_entry_age": 18,
            "max_entry_age": 65,
            "min_term": 5,
            "max_term": 30,
            "min_sum_assured": "1000000.00",
            "max_sum_assured": "1000000000.00",
            "premium_frequencies": ["MONTHLY", "ANNUAL"],
            "allow_riders": True,
            "allow_loans": True,
            "allow_withdrawals": False,
            "allow_surrender": True,
            "allow_paidup": True,
            "allow_bonus": True,
            "investment_linked": False,
            "effective_from": "2026-01-01",
        }

    def create_product(self, code="STANDARD_ENDOWMENT"):
        response = self.client.post("/api/v1/ol-parameters/products/", self.product_payload(code), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return OLProduct.objects.get(code=code)

    def test_plan_type_crud_and_filtering(self):
        response = self.client.get("/api/v1/ol-parameters/plan-types/?plan_category=INDIVIDUAL&search=Endowment")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["code"], "ENDOWMENT")

        create_response = self.client.post(
            "/api/v1/ol-parameters/plan-types/",
            {
                "code": "WHOLE_LIFE",
                "name": "Whole Life",
                "description": "Whole life category.",
                "plan_category": "INDIVIDUAL",
                "effective_from": "2026-01-01",
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201, create_response.data)
        record = OLPlanType.objects.get(code="WHOLE_LIFE")
        update_response = self.client.patch(
            f"/api/v1/ol-parameters/plan-types/{record.pk}/",
            {"name": "Whole Life Updated"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200, update_response.data)
        self.assertEqual(update_response.data["name"], "Whole Life Updated")
        retrieve_response = self.client.get(f"/api/v1/ol-parameters/plan-types/{record.pk}/")
        self.assertEqual(retrieve_response.status_code, 200)
        self.assertEqual(retrieve_response.data["code"], "WHOLE_LIFE")

    def test_product_save_normalizes_frequency_codes(self):
        payload = self.product_payload("NORMALIZED_FREQUENCIES")
        payload["premium_frequencies"] = ["monthly", "quarterly", "SEMI_ANNUAL", "ANNUALLY", "single"]
        response = self.client.post("/api/v1/ol-parameters/products/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        product = OLProduct.objects.get(code="NORMALIZED_FREQUENCIES")
        self.assertEqual(
            product.premium_frequencies,
            ["MONTHLY", "QUARTERLY", "SEMI_ANNUALLY", "ANNUALLY", "SINGLE"],
        )
        self.assertEqual(response.data["premium_frequencies"], product.premium_frequencies)

    def test_seeded_product_validates_with_multiple_canonical_frequencies(self):
        management.call_command("seed_ol_product_setup", verbosity=0)
        product = OLProduct.objects.get(code="STANDARD_ENDOWMENT")
        self.assertGreaterEqual(len(product.premium_frequencies), 2)
        self.assertTrue(set(product.premium_frequencies).issubset({"ANNUALLY", "SEMI_ANNUALLY", "QUARTERLY", "MONTHLY", "SINGLE"}))
        self.assertEqual(product.premium_frequencies, ["MONTHLY", "QUARTERLY", "SEMI_ANNUALLY", "ANNUALLY"])

    def test_product_rejects_unsupported_frequency_code(self):
        payload = self.product_payload("UNSUPPORTED_FREQUENCY")
        payload["premium_frequencies"] = ["MONTHLY", "WEEKLY"]
        response = self.client.post("/api/v1/ol-parameters/products/", payload, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        frequency_error = response.data["error"]["details"]["premium_frequencies"]
        self.assertIn("WEEKLY", str(frequency_error))
        self.assertIn("ANNUALLY", str(frequency_error))

    def test_product_crud_filter_and_csv_export(self):
        response = self.client.post("/api/v1/ol-parameters/products/", self.product_payload(), format="json", HTTP_X_REQUEST_ID="product-create")
        self.assertEqual(response.status_code, 201, response.data)
        product = OLProduct.objects.get(code="STANDARD_ENDOWMENT")
        self.assertEqual(response.data["currency"], "TZS")
        self.assertEqual(str(response.data["plan_type"]), str(self.plan_type.pk))

        update_response = self.client.patch(
            f"/api/v1/ol-parameters/products/{product.pk}/",
            {"max_entry_age": 70, "allow_withdrawals": True},
            format="json",
            HTTP_X_REQUEST_ID="product-update",
        )
        self.assertEqual(update_response.status_code, 200, update_response.data)
        product.refresh_from_db()
        self.assertEqual(product.max_entry_age, 70)
        self.assertTrue(product.allow_withdrawals)

        list_response = self.client.get("/api/v1/ol-parameters/products/?insurance_class=INDIVIDUAL&is_active=true")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual([row["code"] for row in list_response.data["data"]], ["STANDARD_ENDOWMENT"])
        export_response = self.client.get("/api/v1/ol-parameters/products/export/")
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("STANDARD_ENDOWMENT", export_response.content.decode())

        self.assertTrue(AuditLog.objects.filter(
            app_label="ol_parameters",
            model_name="olproduct",
            object_id=str(product.pk),
            action="CREATE",
            correlation_id="product-create",
        ).exists())
        self.assertTrue(AuditLog.objects.filter(
            app_label="ol_parameters",
            model_name="olproduct",
            object_id=str(product.pk),
            action="UPDATE",
            correlation_id="product-update",
        ).exists())

    def test_all_remaining_product_setup_tables_are_crud_resources(self):
        product = self.create_product()
        payloads = [
            (
                "/api/v1/ol-parameters/plan-tax-configurations/",
                {
                    "code": "TAX_STANDARD",
                    "name": "Tax Standard",
                    "product": str(product.pk),
                    "tax_type": "STAMP_DUTY",
                    "tax_basis": "PREMIUM",
                    "rate_type": "PERCENTAGE",
                    "rate_value": "2.500000",
                    "apply_on": "PREMIUM_RECEIPT",
                    "sequence": 1,
                    "country_or_branch": "TZ",
                    "effective_from": "2026-01-01",
                },
            ),
            (
                "/api/v1/ol-parameters/plan-target-markets/",
                {
                    "code": "MARKET_STANDARD",
                    "name": "Standard Market",
                    "product": str(product.pk),
                    "target_market_type": "INDIVIDUAL_RESIDENT",
                    "min_age": 18,
                    "max_age": 65,
                    "occupation_categories": ["OFFICE"],
                    "residency_requirement": "TZ_RESIDENT",
                },
            ),
            (
                "/api/v1/ol-parameters/plan-risk-categories/",
                {
                    "code": "RISK_STANDARD",
                    "name": "Standard Risk",
                    "product": str(product.pk),
                    "underwriting_class": "STANDARD",
                    "loading_basis": "NO_LOADING",
                },
            ),
            (
                "/api/v1/ol-parameters/plan-occupation-risk-limits/",
                {
                    "code": "OCCUPATION_STANDARD",
                    "name": "Occupation Standard",
                    "product": str(product.pk),
                    "occupation_risk_category": "MANUAL_RISK",
                    "max_sum_assured": "500000000.00",
                    "loading_rate": "10.000000",
                    "exclusion_flag": False,
                    "effective_from": "2026-01-01",
                },
            ),
        ]
        for endpoint, payload in payloads:
            response = self.client.post(endpoint, payload, format="json")
            self.assertEqual(response.status_code, 201, {"endpoint": endpoint, "response": response.data})

        fund_type_response = self.client.post(
            "/api/v1/ol-parameters/investment-fund-types/",
            {
                "code": "MODERATE",
                "name": "Moderate Fund",
                "description": "Moderate risk profile.",
                "risk_profile": "MODERATE",
                "effective_from": "2026-01-01",
            },
            format="json",
        )
        self.assertEqual(fund_type_response.status_code, 201, fund_type_response.data)
        fund_type = OLInvestmentFundType.objects.get(code="MODERATE")
        fund_response = self.client.post(
            "/api/v1/ol-parameters/investment-funds/",
            {
                "code": "BALANCED_FUND",
                "name": "Balanced Fund",
                "description": "Balanced fund.",
                "fund_type": str(fund_type.pk),
                "currency": "TZS",
                "valuation_frequency": "DAILY",
                "unit_price": "100.000000",
                "allocation_rules": {"minimum": 0, "maximum": 100},
                "effective_from": "2026-01-01",
            },
            format="json",
        )
        self.assertEqual(fund_response.status_code, 201, fund_response.data)
        self.assertEqual(OLInvestmentFund.objects.count(), 1)

    def test_product_invariants_reject_invalid_ranges_and_scopes(self):
        invalid_product = OLProduct(
            code="INVALID_PRODUCT",
            name="Invalid Product",
            plan_type=self.plan_type,
            currency="TZS",
            min_entry_age=70,
            max_entry_age=65,
            min_term=10,
            max_term=5,
            min_sum_assured=Decimal("100"),
            max_sum_assured=Decimal("50"),
            premium_frequencies=["ANNUAL"],
            effective_from=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            invalid_product.full_clean()

        tax_without_scope = OLPlanTaxConfiguration(
            code="TAX_NO_SCOPE",
            name="Tax No Scope",
            tax_type="STAMP_DUTY",
            tax_basis="PREMIUM",
            rate_type="PERCENTAGE",
            rate_value=Decimal("5"),
            apply_on="PREMIUM",
            effective_from=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            tax_without_scope.full_clean()

        tax_over_100 = OLPlanTaxConfiguration(
            code="TAX_OVER_100",
            name="Tax Over 100",
            product=self.create_product(),
            tax_type="STAMP_DUTY",
            tax_basis="PREMIUM",
            rate_type="PERCENTAGE",
            rate_value=Decimal("101"),
            apply_on="PREMIUM",
            effective_from=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            tax_over_100.full_clean()

        fund_type = OLInvestmentFundType.objects.create(
            code="INVALID_FUND_TYPE",
            name="Invalid Fund Type",
            risk_profile="MODERATE",
            effective_from=date(2026, 1, 1),
        )
        fund = OLInvestmentFund(
            code="INVALID_FUND",
            name="Invalid Fund",
            fund_type=fund_type,
            currency="TZS",
            valuation_frequency="DAILY",
            unit_price=Decimal("0"),
            effective_from=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            fund.full_clean()

    def test_scoped_rows_prevent_duplicate_active_overlap(self):
        product = self.create_product()
        first = OLPlanTargetMarket(
            code="MARKET_001",
            name="Market One",
            product=product,
            target_market_type="RESIDENT",
            min_age=18,
            max_age=65,
            residency_requirement="TZ",
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
        )
        first.full_clean()
        first.save()
        second = OLPlanTargetMarket(
            code="MARKET_002",
            name="Market Two",
            product=product,
            target_market_type="RESIDENT",
            min_age=30,
            max_age=55,
            residency_requirement="TZ",
            effective_from=date(2026, 6, 1),
            effective_to=date(2027, 5, 31),
        )
        with self.assertRaises(ValidationError):
            second.full_clean()

        first_risk = OLPlanRiskCategory(
            code="RISK_001",
            name="Risk One",
            product=product,
            underwriting_class="STANDARD",
            loading_basis="NONE",
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
        )
        first_risk.full_clean()
        first_risk.save()
        second_risk = OLPlanRiskCategory(
            code="RISK_002",
            name="Risk Two",
            product=product,
            underwriting_class="STANDARD",
            loading_basis="NONE",
            effective_from=date(2026, 7, 1),
            effective_to=date(2027, 12, 31),
        )
        with self.assertRaises(ValidationError):
            second_risk.full_clean()

    def test_permission_is_required_for_product_setup_tables(self):
        restricted_user = User.objects.create_user(
            username="ol-product-setup-viewer",
            email="ol-product-setup-viewer@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
        )
        restricted_client = APIClient()
        restricted_client.force_authenticate(restricted_user)
        response = restricted_client.get("/api/v1/ol-parameters/products/")
        self.assertEqual(response.status_code, 403)

    def test_seed_command_is_idempotent_and_registers_all_eight_tables(self):
        management.call_command("seed_ol_product_setup")
        first_counts = {
            "plan_types": OLPlanType.objects.count(),
            "products": OLProduct.objects.count(),
            "taxes": OLPlanTaxConfiguration.objects.count(),
            "markets": OLPlanTargetMarket.objects.count(),
            "risks": OLPlanRiskCategory.objects.count(),
            "occupation_limits": OLPlanOccupationRiskLimit.objects.count(),
            "fund_types": OLInvestmentFundType.objects.count(),
            "funds": OLInvestmentFund.objects.count(),
            "registry": OLParameterTableRegistry.objects.filter(parameter_group="Product Setup").count(),
        }
        management.call_command("seed_ol_product_setup")
        second_counts = {
            "plan_types": OLPlanType.objects.count(),
            "products": OLProduct.objects.count(),
            "taxes": OLPlanTaxConfiguration.objects.count(),
            "markets": OLPlanTargetMarket.objects.count(),
            "risks": OLPlanRiskCategory.objects.count(),
            "occupation_limits": OLPlanOccupationRiskLimit.objects.count(),
            "fund_types": OLInvestmentFundType.objects.count(),
            "funds": OLInvestmentFund.objects.count(),
            "registry": OLParameterTableRegistry.objects.filter(parameter_group="Product Setup").count(),
        }
        self.assertEqual(first_counts, second_counts)
        self.assertEqual(first_counts["plan_types"], 6)
        self.assertEqual(first_counts["products"], 1)
        self.assertEqual(first_counts["registry"], 8)

    def test_all_product_setup_models_are_registered_with_permission_aware_admin(self):
        for model in (
            OLPlanType,
            OLProduct,
            OLPlanTaxConfiguration,
            OLPlanTargetMarket,
            OLPlanRiskCategory,
            OLPlanOccupationRiskLimit,
            OLInvestmentFundType,
            OLInvestmentFund,
        ):
            self.assertIn(model, admin.site._registry)
            self.assertTrue(admin.site._registry[model].has_view_permission(type("Request", (), {"user": self.user})()))
