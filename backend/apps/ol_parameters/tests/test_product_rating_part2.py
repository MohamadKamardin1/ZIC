from datetime import date
from decimal import Decimal

from django.contrib import admin
from django.core import management
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient

from apps.governance.models import AuditLog
from apps.ol_parameters.models import (
    OLBonusRate,
    OLCashSurrenderValue,
    OLInstallmentChargeRate,
    OLMortgageInterestFactor,
    OLParameterTableRegistry,
    OLPlanType,
    OLProduct,
    OLReserveLoading,
    OLReinstatementInterestRate,
)
from apps.users.models import User


class OLProductRatingPart2Tests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="ol-rating-part2-admin",
            email="ol-rating-part2-admin@example.com",
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

    def reinstatement_payload(self, code="REINSTATEMENT_2026", effective_to=None):
        return {
            "code": code,
            "name": "Reinstatement Interest",
            "description": "Reinstatement interest assumption.",
            "product": str(self.product.pk),
            "plan": None,
            "rate": "8.00000000",
            "calculation_basis": "OUTSTANDING_PREMIUM",
            "effective_from": "2026-01-01",
            "effective_to": effective_to,
            "is_active": True,
        }

    def bonus_payload(self, code="BONUS_2026"):
        return {
            "code": code,
            "name": "Reversionary Bonus",
            "description": "Bonus assumption.",
            "product": str(self.product.pk),
            "plan": None,
            "bonus_type": "REVERSIONARY",
            "rate": "2.00000000",
            "valuation_year": 1,
            "declaration_frequency": "ANNUAL",
            "effective_from": "2026-01-01",
            "effective_to": None,
            "is_active": True,
        }

    def mortgage_payload(self, code="MORTGAGE_FACTOR_2026"):
        return {
            "code": code,
            "name": "Mortgage Interest Factor",
            "description": "Mortgage or policy-loan factor.",
            "product": str(self.product.pk),
            "plan": None,
            "factor": "1.08000000",
            "calculation_basis": "LOAN_BALANCE",
            "effective_from": "2026-01-01",
            "effective_to": None,
            "is_active": True,
        }

    def installment_payload(self, code="INSTALLMENT_CHARGE_2026"):
        return {
            "code": code,
            "name": "Installment Charge",
            "description": "Installment charge assumption.",
            "product": str(self.product.pk),
            "plan": None,
            "frequency": "MONTHLY",
            "charge_type": "PERCENTAGE",
            "rate_value": "2.50000000",
            "apply_on": "PREMIUM",
            "effective_from": "2026-01-01",
            "effective_to": None,
            "is_active": True,
        }

    def surrender_payload(self, code="CSV_2026"):
        return {
            "code": code,
            "name": "Cash Surrender Value",
            "description": "Surrender-value factor row.",
            "product": str(self.product.pk),
            "plan": None,
            "policy_year_from": 1,
            "policy_year_to": 30,
            "age_from": 18,
            "age_to": 65,
            "term_from": 5,
            "term_to": 30,
            "gender": "M",
            "smoker_status": "NS",
            "surrender_value_factor": "0.50000000",
            "rate": None,
            "effective_from": "2026-01-01",
            "effective_to": None,
            "is_active": True,
        }

    def reserve_payload(self, code="RESERVE_LOADING_2026"):
        return {
            "code": code,
            "name": "Expense Reserve Loading",
            "description": "Reserve expense loading.",
            "product": str(self.product.pk),
            "plan": None,
            "loading_type": "EXPENSE",
            "loading_basis": "RESERVE",
            "rate_value": "2.00000000",
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

    def test_all_six_resources_support_crud_and_table_filters(self):
        resources = [
            ("reinstatement-interest-rates", self.reinstatement_payload(), OLReinstatementInterestRate, "REINSTATEMENT_2026", {"rate": "8.50000000"}),
            ("bonus-rates", self.bonus_payload(), OLBonusRate, "BONUS_2026", {"rate": "2.25000000"}),
            ("mortgage-interest-factors", self.mortgage_payload(), OLMortgageInterestFactor, "MORTGAGE_FACTOR_2026", {"factor": "1.09000000"}),
            ("installment-charge-rates", self.installment_payload(), OLInstallmentChargeRate, "INSTALLMENT_CHARGE_2026", {"rate_value": "3.00000000"}),
            ("cash-surrender-values", self.surrender_payload(), OLCashSurrenderValue, "CSV_2026", {"surrender_value_factor": "0.55000000"}),
            ("reserve-loadings", self.reserve_payload(), OLReserveLoading, "RESERVE_LOADING_2026", {"rate_value": "2.50000000"}),
        ]
        for slug, payload, model, code, update in resources:
            create = self.create_resource(f"/api/v1/ol-parameters/{slug}/", payload, request_id=f"{slug}-create")
            record = model.objects.get(code=code)
            self.assertEqual(create.status_code, 201)
            patch = self.client.patch(
                f"/api/v1/ol-parameters/{slug}/{record.pk}/",
                update,
                format="json",
                HTTP_X_REQUEST_ID=f"{slug}-update",
            )
            self.assertEqual(patch.status_code, 200, patch.data)
            retrieve = self.client.get(f"/api/v1/ol-parameters/{slug}/{record.pk}/")
            self.assertEqual(retrieve.status_code, 200, retrieve.data)
            listing = self.client.get(
                f"/api/v1/ol-parameters/{slug}/?product={self.product.pk}&is_active=true&per_page=1&page=1"
            )
            self.assertEqual(listing.status_code, 200, listing.data)
            self.assertEqual(len(listing.data["data"]), 1)
            self.assertEqual(listing.data["pagination"]["total"], 1)

    def test_filters_expose_each_rating_dimension(self):
        self.create_resource("reinstatement-interest-rates", self.reinstatement_payload())
        self.create_resource("bonus-rates", self.bonus_payload())
        self.create_resource("mortgage-interest-factors", self.mortgage_payload())
        self.create_resource("installment-charge-rates", self.installment_payload())
        self.create_resource("cash-surrender-values", self.surrender_payload())
        self.create_resource("reserve-loadings", self.reserve_payload())

        filter_requests = [
            ("reinstatement-interest-rates", "calculation_basis=OUTSTANDING_PREMIUM"),
            ("bonus-rates", "bonus_type=REVERSIONARY&valuation_year=1&declaration_frequency=ANNUAL"),
            ("mortgage-interest-factors", "calculation_basis=LOAN_BALANCE"),
            ("installment-charge-rates", "frequency=MONTHLY&charge_type=PERCENTAGE&apply_on=PREMIUM"),
            ("cash-surrender-values", "policy_year_from=1&gender=M&smoker_status=NS"),
            ("reserve-loadings", "loading_type=EXPENSE&loading_basis=RESERVE"),
        ]
        for slug, query in filter_requests:
            response = self.client.get(f"/api/v1/ol-parameters/{slug}/?product={self.product.pk}&{query}")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["pagination"]["total"], 1)

    def test_invalid_values_scope_and_effective_dates_are_rejected(self):
        invalid_payloads = [
            ("reinstatement-interest-rates", {**self.reinstatement_payload("INVALID_REIN"), "rate": "-1"}),
            ("bonus-rates", {**self.bonus_payload("INVALID_BONUS"), "rate": "101"}),
            ("mortgage-interest-factors", {**self.mortgage_payload("INVALID_MORTGAGE"), "factor": "0"}),
            ("installment-charge-rates", {**self.installment_payload("INVALID_INSTALLMENT"), "rate_value": "-0.1"}),
            ("cash-surrender-values", {**self.surrender_payload("INVALID_CSV"), "surrender_value_factor": "1.1"}),
            ("reserve-loadings", {**self.reserve_payload("INVALID_RESERVE"), "rate_value": "100.1"}),
        ]
        for endpoint, payload in invalid_payloads:
            response = self.create_resource(f"/api/v1/ol-parameters/{endpoint}/", payload, expected=400)
            self.assertEqual(response.status_code, 400)

        invalid_dates = self.reinstatement_payload("INVALID_DATES", effective_to="2025-12-31")
        response = self.create_resource("/api/v1/ol-parameters/reinstatement-interest-rates/", invalid_dates, expected=400)
        self.assertEqual(response.status_code, 400)

        missing_scope = self.bonus_payload("MISSING_SCOPE")
        missing_scope["product"] = None
        response = self.create_resource("/api/v1/ol-parameters/bonus-rates/", missing_scope, expected=400)
        self.assertEqual(response.status_code, 400)

        invalid_model = OLReserveLoading(
            code="INVALID_RESERVE_MODEL",
            name="Invalid Reserve",
            product=None,
            plan=None,
            loading_type="EXPENSE",
            loading_basis="RESERVE",
            rate_value=Decimal("2"),
            effective_from=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            invalid_model.full_clean()

    def test_overlap_detection_prevents_duplicate_active_scopes(self):
        first = OLReinstatementInterestRate(
            code="REIN_OVERLAP_1",
            name="First Reinstatement Rate",
            product=self.product,
            rate=Decimal("8"),
            calculation_basis="OUTSTANDING_PREMIUM",
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
        )
        first.full_clean()
        first.save()
        second = OLReinstatementInterestRate(
            code="REIN_OVERLAP_2",
            name="Second Reinstatement Rate",
            product=self.product,
            rate=Decimal("9"),
            calculation_basis="OUTSTANDING_PREMIUM",
            effective_from=date(2026, 6, 1),
            effective_to=date(2027, 12, 31),
        )
        with self.assertRaises(ValidationError):
            second.full_clean()

        first_csv = OLCashSurrenderValue(
            code="CSV_OVERLAP_1",
            name="First CSV",
            product=self.product,
            policy_year_from=1,
            policy_year_to=10,
            age_from=18,
            age_to=65,
            term_from=5,
            term_to=30,
            gender="M",
            smoker_status="NS",
            surrender_value_factor=Decimal("0.5"),
            effective_from=date(2026, 1, 1),
        )
        first_csv.full_clean()
        first_csv.save()
        second_csv = OLCashSurrenderValue(
            code="CSV_OVERLAP_2",
            name="Second CSV",
            product=self.product,
            policy_year_from=5,
            policy_year_to=15,
            age_from=18,
            age_to=65,
            term_from=5,
            term_to=30,
            gender="M",
            smoker_status="NS",
            surrender_value_factor=Decimal("0.6"),
            effective_from=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            second_csv.full_clean()

    def test_permission_checks_and_audit_logs(self):
        created = self.create_resource(
            "bonus-rates",
            self.bonus_payload(),
            request_id="bonus-part2-create",
        )
        self.assertEqual(created.status_code, 201)
        bonus = OLBonusRate.objects.get(code="BONUS_2026")
        self.assertTrue(
            AuditLog.objects.filter(
                model_name="olbonusrate",
                object_id=str(bonus.pk),
                action="CREATE",
                correlation_id="bonus-part2-create",
            ).exists()
        )

        restricted_user = User.objects.create_user(
            username="ol-rating-part2-viewer",
            email="ol-rating-part2-viewer@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
        )
        restricted_client = APIClient()
        restricted_client.force_authenticate(restricted_user)
        for slug in (
            "reinstatement-interest-rates",
            "bonus-rates",
            "mortgage-interest-factors",
            "installment-charge-rates",
            "cash-surrender-values",
            "reserve-loadings",
        ):
            self.assertEqual(restricted_client.get(f"/api/v1/ol-parameters/{slug}/").status_code, 403, slug)

    def test_part2_seed_is_idempotent_and_registers_all_six_contracts(self):
        management.call_command("seed_ol_product_rating_part2", verbosity=0)
        first_counts = (
            OLReinstatementInterestRate.objects.count(),
            OLBonusRate.objects.count(),
            OLMortgageInterestFactor.objects.count(),
            OLInstallmentChargeRate.objects.count(),
            OLCashSurrenderValue.objects.count(),
            OLReserveLoading.objects.count(),
            OLParameterTableRegistry.objects.filter(
                slug__in=[
                    "reinstatement-interest-rates",
                    "bonus-rates",
                    "mortgage-interest-factors",
                    "installment-charge-rates",
                    "cash-surrender-values",
                    "reserve-loadings",
                ]
            ).count(),
        )
        management.call_command("seed_ol_product_rating_part2", verbosity=0)
        second_counts = (
            OLReinstatementInterestRate.objects.count(),
            OLBonusRate.objects.count(),
            OLMortgageInterestFactor.objects.count(),
            OLInstallmentChargeRate.objects.count(),
            OLCashSurrenderValue.objects.count(),
            OLReserveLoading.objects.count(),
            OLParameterTableRegistry.objects.filter(
                slug__in=[
                    "reinstatement-interest-rates",
                    "bonus-rates",
                    "mortgage-interest-factors",
                    "installment-charge-rates",
                    "cash-surrender-values",
                    "reserve-loadings",
                ]
            ).count(),
        )
        self.assertEqual(first_counts, second_counts)
        self.assertEqual(first_counts[-1], 6)

    def test_admin_registration_and_view_permissions_exist_for_all_part2_models(self):
        request = RequestFactory().get("/admin/")
        request.user = self.user
        models = (
            OLReinstatementInterestRate,
            OLBonusRate,
            OLMortgageInterestFactor,
            OLInstallmentChargeRate,
            OLCashSurrenderValue,
            OLReserveLoading,
        )
        for model in models:
            self.assertIn(model, admin.site._registry)
            model_admin = admin.site._registry[model]
            self.assertTrue(model_admin.has_view_permission(request))
            self.assertTrue(model_admin.list_display)
