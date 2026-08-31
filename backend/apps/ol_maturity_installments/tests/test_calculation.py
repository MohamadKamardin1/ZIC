from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.governance.models import AuditLog
from apps.ol_maturity_installments.errors import INSTALLMENT_ERROR_REGISTRY
from apps.ol_maturity_installments.services.calculation import (
    calculate_schedule,
    generate_schedule,
)
from apps.ol_parameters.models import OLAnticipatedEndowmentInstallmentRate
from apps.ol_policies.models import Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.ordinary_life.models import OLProduct
from apps.partners.models import Partner


class InstallmentCalculationTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="installments-engine",
            email="installments-engine@example.com",
            password="Strong-installments-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-MIP-C-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Baraka Mchumi",
            email="baraka.calculation@example.com",
            mobile_number="+255711200001",
            phone="+255711200001",
        )
        self.agent = Partner.objects.create(
            partner_number="ZIC-MIP-C-A-0001",
            partner_type="AGENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Neema Calculation Agent",
            email="neema.calculation@example.com",
            mobile_number="+255711200002",
            phone="+255711200002",
        )
        self.product = OLProduct.objects.create(
            code="OL_ENDOWMENT_STANDARD",
            name="Endowment Standard",
            business_area="ORDINARY_LIFE",
            is_active=True,
        )
        OLProduct.objects.create(
            code="OL_ENDOWMENT_NO_RATE",
            name="Endowment Without Rate Table",
            business_area="ORDINARY_LIFE",
            is_active=True,
        )
        self._rate("MIP-ANNUAL-10", frequency="ANNUAL", term_from=10, term_to=10, rate_factor="10.00000000")
        self._rate("MIP-ANNUAL-3", frequency="ANNUAL", term_from=3, term_to=3, rate_factor="33.33333333")
        self._rate("MIP-QUARTERLY-3", frequency="QUARTERLY", term_from=3, term_to=3, rate_factor="10.00000000")
        self.maturity_value = Decimal("25000000.00")

        self.policy = self._policy(
            "POL-MIP-CALC-0001",
            maturity_date=date(2026, 1, 14),
            product_plan_ref="OL_ENDOWMENT_STANDARD",
        )
        self.future_policy = self._policy(
            "POL-MIP-CALC-FUTURE-0001",
            maturity_date=date(2026, 12, 31),
            product_plan_ref="OL_ENDOWMENT_STANDARD",
        )
        self.no_rate_policy = self._policy(
            "POL-MIP-CALC-NORATE-0001",
            maturity_date=date(2026, 1, 14),
            product_plan_ref="OL_ENDOWMENT_NO_RATE",
        )
        self.client.force_authenticate(self.user)

    def _rate(self, code, *, frequency, term_from=None, term_to=None, rate_factor):
        return OLAnticipatedEndowmentInstallmentRate.objects.create(
            code=code,
            name=f"Test rate {code}",
            product=self.product,
            plan=None,
            installment_type="ANTICIPATED_ENDOWMENT",
            frequency=frequency,
            term_from=term_from,
            term_to=term_to,
            rate_factor=Decimal(rate_factor),
            currency="",
            is_active=True,
            effective_from=date(2026, 1, 1),
            effective_to=None,
        )

    def _policy(self, policy_number, *, maturity_date, product_plan_ref):
        quotation = OLQuotation.objects.create(
            quote_number=f"QT-{policy_number}",
            quote_name=f"Quote {policy_number}",
            quote_date=date(2026, 1, 1),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number=f"PROP-{policy_number}",
            status="POLICY_ISSUED",
            partner=self.partner,
            agent_partner=self.agent,
            currency="TZS",
        )
        return Policy.objects.create(
            policy_number=policy_number,
            proposal_ref=proposal,
            partner=self.partner,
            agent=self.agent,
            product_plan_ref=product_plan_ref,
            currency="TZS",
            sum_assured=Decimal("25000000.00"),
            premium_amount=Decimal("125000.00"),
            premium_frequency="ANNUALLY",
            term_years=10,
            risk_commencement_date=date(2016, 1, 15),
            maturity_date=maturity_date,
            status="MATURED",
        )

    def _on(self):
        return date(2026, 1, 15)

    def test_generate_schedule_returns_correct_schedule(self):
        items = generate_schedule(
            self.policy,
            self.maturity_value,
            "ANNUAL",
            10,
            on_date=self._on(),
            start_date=date(2026, 1, 15),
            actor=self.user,
            source_channel="WEB",
        )

        self.assertEqual(len(items), 10)
        for index, item in enumerate(items, start=1):
            self.assertEqual(item["installment_number"], index)
            self.assertEqual(item["date"], date(2026, 1, 15).replace(year=2025 + index))
            self.assertEqual(item["amount"], Decimal("2500000.00"))
        self.assertEqual(sum(item["amount"] for item in items), self.maturity_value)

    def test_calculate_schedule_reconciles_total_to_maturity_value(self):
        schedule = calculate_schedule(
            self.policy,
            self.maturity_value,
            "ANNUAL",
            10,
            on_date=self._on(),
            start_date=date(2026, 1, 15),
            actor=self.user,
            source_channel="API",
        )

        self.assertEqual(schedule["total_payable_amount"], self.maturity_value)
        self.assertEqual(schedule["installment_count"], 10)
        self.assertEqual(schedule["frequency"], "ANNUAL")
        self.assertEqual(schedule["start_date"], date(2026, 1, 15))
        self.assertEqual(schedule["end_date"], date(2035, 1, 15))
        self.assertEqual(schedule["frequency_matches_policy"], True)
        self.assertEqual(schedule["rate_used"]["rate_factor"], "10.00000000")
        self.assertEqual(schedule["parameters_used"], ["OLAnticipatedEndowmentInstallmentRate"])

    def test_rounding_distribution_makes_total_equal_maturity_value(self):
        items = generate_schedule(
            self.policy,
            Decimal("100.00"),
            "ANNUAL",
            3,
            on_date=self._on(),
            start_date=date(2026, 1, 15),
        )

        self.assertEqual(len(items), 3)
        amounts = [item["amount"] for item in items]
        self.assertEqual(amounts, [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")])
        self.assertEqual(sum(amounts), Decimal("100.00"))

    def test_non_matured_policy_raises_teachable_error(self):
        with self.assertRaises(Exception) as ctx:
            generate_schedule(
                self.future_policy,
                self.maturity_value,
                "ANNUAL",
                10,
                on_date=self._on(),
            )
        error = ctx.exception
        self.assertEqual(error.error_code, "PLAN_POLICY_NOT_MATURED")
        self.assertEqual(error.status_code, INSTALLMENT_ERROR_REGISTRY["PLAN_POLICY_NOT_MATURED"]["status_code"])
        self.assertTrue(error.resolution_steps)

    def test_missing_parameter_returns_teachable_error(self):
        with self.assertRaises(Exception) as ctx:
            generate_schedule(
                self.no_rate_policy,
                self.maturity_value,
                "ANNUAL",
                10,
                on_date=self._on(),
            )
        error = ctx.exception
        self.assertEqual(error.error_code, "PLAN_PARAMETER_MISSING")
        self.assertEqual(error.status_code, 422)
        self.assertTrue(error.resolution_steps)
        self.assertEqual(error.details["product"], "OL_ENDOWMENT_NO_RATE")
        self.assertEqual(error.details["frequency"], "ANNUAL")

    def test_unreconcilable_rate_raises_calculation_mismatch(self):
        with self.assertRaises(Exception) as ctx:
            generate_schedule(
                self.policy,
                Decimal("10000.00"),
                "QUARTERLY",
                3,
                on_date=self._on(),
                start_date=date(2026, 1, 15),
            )
        error = ctx.exception
        self.assertEqual(error.error_code, "PLAN_CALCULATION_MISMATCH")
        self.assertEqual(error.status_code, 422)
        self.assertTrue(error.resolution_steps)

    def test_invalid_frequency_and_term_are_structured(self):
        with self.assertRaises(Exception) as ctx:
            generate_schedule(self.policy, self.maturity_value, "WEEKLY", 10, on_date=self._on())
        self.assertEqual(ctx.exception.error_code, "INSTALLMENT_INVALID_FREQUENCY")

        with self.assertRaises(Exception) as ctx:
            generate_schedule(self.policy, self.maturity_value, "ANNUAL", 0, on_date=self._on())
        self.assertEqual(ctx.exception.error_code, "INSTALLMENT_INVALID_TERM")

    def test_calculation_run_is_audited(self):
        calculate_schedule(
            self.policy,
            self.maturity_value,
            "ANNUAL",
            10,
            on_date=self._on(),
            start_date=date(2026, 1, 15),
            actor=self.user,
            source_channel="WEB",
        )
        log = AuditLog.objects.filter(
            app_label="ol_maturity_installments",
            model_name="installment_schedule",
            object_id=str(self.policy.pk),
        ).latest("created_at")
        self.assertEqual(log.action, "CALCULATE")
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.source_channel, "WEB")
        self.assertEqual(log.after_state["total_payable_amount"], str(self.maturity_value))
        self.assertEqual(log.after_state["reconciled"], "True")

    def test_frequency_options_endpoint_returns_labeled_data(self):
        response = self.client.get("/api/v1/ol/maturity-installments/options/frequencies/")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["entity"], "frequencies")
        labels = {item["label"] for item in data["items"]}
        self.assertEqual(labels, {"Single", "Monthly", "Quarterly", "Half yearly", "Annual"})
        single = next(item for item in data["items"] if item["value"] == "SINGLE")
        self.assertEqual(single["meta"]["monthsBetween"], 0)
        monthly = next(item for item in data["items"] if item["value"] == "MONTHLY")
        self.assertEqual(monthly["meta"]["payoutPerYear"], 12)

    def test_term_options_endpoint_returns_labeled_data(self):
        response = self.client.get("/api/v1/ol/maturity-installments/options/terms/")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["entity"], "terms")
        values = {int(item["value"]) for item in data["items"]}
        self.assertIn(3, values)
        self.assertIn(10, values)
        term_three = next(item for item in data["items"] if item["value"] == "3")
        self.assertEqual(term_three["label"], "3 years")
        self.assertEqual(term_three["meta"]["termMonths"], 36)
        self.assertEqual(term_three["meta"]["source"], "INSTALLMENT_RATE_TABLE")

    def test_options_endpoints_support_product_scoping_and_search(self):
        response = self.client.get(
            "/api/v1/ol/maturity-installments/options/terms/",
            {"product": "OL_ENDOWMENT_STANDARD"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.json()["data"]["items"]), 0)

        response = self.client.get(
            "/api/v1/ol/maturity-installments/options/frequencies/",
            {"q": "month"},
        )
        self.assertEqual(response.status_code, 200)
        values = {item["value"] for item in response.json()["data"]["items"]}
        self.assertIn("MONTHLY", values)
