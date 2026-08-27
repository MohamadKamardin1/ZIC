from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.ol_parameters.models import OLPlanType, OLProduct
from apps.ol_policies.models import Policy, PolicyStatus, WithdrawalPayment, WithdrawalRequest, WithdrawalStatus
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partner_onboarding.models import Branch
from apps.partners.models import Partner


class StaffWithdrawalsApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="withdrawal-staff",
            email="withdrawal-staff@example.com",
            password="Strong-withdrawal-password-123!",
        )
        self.client.force_authenticate(self.user)
        self.partner = Partner.objects.create(
            partner_number="ZIC-WDR-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Asha Mohammed",
            email="asha.withdrawal@example.com",
            mobile_number="+255711600001",
            phone="+255711600001",
        )
        self.agent = Partner.objects.create(
            partner_number="ZIC-WDR-A-0001",
            partner_type="AGENT",
            partner_category="CORPORATE",
            party_type="CORPORATE",
            legal_name="Zanzibar Life Brokers",
            email="agent.withdrawal@example.com",
            mobile_number="+255711600002",
            phone="+255711600002",
        )
        self.branch = Branch.objects.create(code="ZNZ-WDR", name="Withdrawals Branch", is_active=True)
        quotation = OLQuotation.objects.create(
            quote_number="QT-WDR-0001",
            quote_name="Withdrawal quote",
            quote_date=date.today() - timedelta(days=60),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-WDR-0001",
            status="CONVERTED",
            partner=self.partner,
            currency="TZS",
            prospect_snapshot={},
            financial_summary_snapshot={},
        )
        plan_type = OLPlanType.objects.create(code="WDR-PLAN", name="Withdrawal plan", is_active=True)
        self.product = OLProduct.objects.create(
            code="OL_WDR_PRODUCT",
            name="Withdrawal product",
            plan_type=plan_type,
            effective_from=date.today() - timedelta(days=365),
            premium_frequencies=["ANNUALLY"],
            allow_withdrawals=True,
            is_active=True,
        )
        self.policy = Policy.objects.create(
            proposal_ref=proposal,
            partner=self.partner,
            agent=self.agent,
            product_plan_ref=self.product.code,
            currency="TZS",
            sum_assured=Decimal("10000000.00"),
            premium_amount=Decimal("100000.00"),
            premium_frequency="ANNUALLY",
            term_years=10,
            risk_commencement_date=date.today() - timedelta(days=120),
            maturity_date=date.today() + timedelta(days=3000),
            status=PolicyStatus.ACTIVE,
            contract_snapshot={
                "cash_value": "2500000.00",
                "allow_withdrawals": True,
                "withdrawal_requires_approval": True,
                "withdrawal_fee_rate": "5.0000",
                "withdrawal_fee_basis": "PERCENTAGE",
                "branch_code": self.branch.code,
                "branch_name": self.branch.name,
                "plans": [{"product_id": str(self.product.pk), "product_code": self.product.code}],
            },
        )

    def test_staff_list_detail_options_and_unknown_catalog(self):
        withdrawal = WithdrawalRequest.objects.create(
            policy=self.policy,
            amount=Decimal("250000.00"),
            cash_value_before=Decimal("2500000.00"),
            loan_balance_before=Decimal("150000.00"),
            fee_amount=Decimal("12500.00"),
            fee_rate=Decimal("5.0000"),
            fee_basis="PERCENTAGE",
            net_amount=Decimal("237500.00"),
            reason="Education expenses",
            status=WithdrawalStatus.REQUESTED,
        )
        response = self.client.get("/api/v1/ol/withdrawals/")
        self.assertEqual(response.status_code, 200)
        row = response.data["data"]["results"][0]
        self.assertEqual(row["id"], str(withdrawal.pk))
        self.assertEqual(row["policyholder_display"], "ZIC-WDR-P-0001 — Asha Mohammed")
        self.assertEqual(row["product_display"], "OL_WDR_PRODUCT — Withdrawal product")
        self.assertEqual(row["agent_display"], "ZIC-WDR-A-0001 — Zanzibar Life Brokers")
        self.assertNotIn(str(self.partner.pk), row["policyholder_display"])

        detail = self.client.get(f"/api/v1/ol/withdrawals/{withdrawal.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["data"]["breakdown"]["net_payout"], "237500.00")
        self.assertEqual(detail.data["data"]["payments"], [])

        for kind in ("policies", "products", "branches", "agents", "payment-modes"):
            options = self.client.get(f"/api/v1/ol/withdrawals/options/{kind}/")
            self.assertEqual(options.status_code, 200, kind)
            self.assertIn("label", options.data["data"]["results"][0])
            self.assertIn("value", options.data["data"]["results"][0])

        searched = self.client.get("/api/v1/ol/withdrawals/options/agents/?q=Zanzibar")
        self.assertEqual(searched.status_code, 200)
        self.assertEqual(len(searched.data["data"]["results"]), 1)
        unknown = self.client.get("/api/v1/ol/withdrawals/options/unknown/")
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.data["error_code"], "WITHDRAWAL_OPTIONS_ENTITY_NOT_FOUND")

    def test_estimate_request_idempotency_and_limit_error(self):
        estimate = self.client.post(
            "/api/v1/ol/withdrawals/estimate/",
            {"policy_id": str(self.policy.pk), "amount": "100000.00"},
            format="json",
        )
        self.assertEqual(estimate.status_code, 200)
        self.assertEqual(estimate.data["data"]["estimated_fee"], "5000.00")
        self.assertEqual(estimate.data["data"]["estimated_net_payout"], "95000.00")

        too_large = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/withdrawals/request/",
            {"amount": "3000000.00", "reason": "Too much"},
            format="json",
        )
        self.assertEqual(too_large.status_code, 422)
        self.assertEqual(too_large.data["error_code"], "WITHDRAWAL_LIMIT_EXCEEDED")
        self.assertIn("amount", too_large.data["field_errors"])

        headers = {"HTTP_X_IDEMPOTENCY_KEY": "wdr-idempotency-001"}
        first = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/withdrawals/request/",
            {"amount": "100000.00", "reason": "Education expenses"},
            format="json",
            **headers,
        )
        second = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/withdrawals/request/",
            {"amount": "100000.00", "reason": "Education expenses"},
            format="json",
            **headers,
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.data["data"]["withdrawal"]["id"], second.data["data"]["withdrawal"]["id"])
        self.assertEqual(WithdrawalRequest.objects.filter(policy=self.policy, idempotency_key="wdr-idempotency-001").count(), 1)

    def test_lifecycle_payment_audit_and_reversal_restore_available_limit(self):
        created = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/withdrawals/request/",
            {"amount": "200000.00", "reason": "Family emergency"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        withdrawal_id = created.data["data"]["withdrawal"]["id"]
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.contract_snapshot["withdrawals_total"], "200000.00")

        approved = self.client.post(f"/api/v1/ol/withdrawals/{withdrawal_id}/approve/", {"reason": "Documents verified"}, format="json")
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.data["data"]["withdrawal"]["status"], WithdrawalStatus.APPROVED)
        missing_payment = self.client.post(f"/api/v1/ol/withdrawals/{withdrawal_id}/process-payout/", {}, format="json")
        self.assertEqual(missing_payment.status_code, 422)
        self.assertIn("payment_mode", missing_payment.data["field_errors"])

        paid = self.client.post(
            f"/api/v1/ol/withdrawals/{withdrawal_id}/process-payout/",
            {"payment_mode": "BANK_TRANSFER", "receipt_reference": "RCT-WDR-0001"},
            format="json",
        )
        self.assertEqual(paid.status_code, 200)
        self.assertEqual(paid.data["data"]["withdrawal"]["status"], WithdrawalStatus.PAID)
        self.assertEqual(WithdrawalPayment.objects.filter(withdrawal_id=withdrawal_id).count(), 1)

        reversed_response = self.client.post(
            f"/api/v1/ol/withdrawals/{withdrawal_id}/reverse/",
            {"reason": "Payment returned by bank"},
            format="json",
        )
        self.assertEqual(reversed_response.status_code, 200)
        self.assertEqual(reversed_response.data["data"]["withdrawal"]["status"], WithdrawalStatus.REVERSED)
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.contract_snapshot["withdrawals_total"], "0.00")
        audit = self.client.get(f"/api/v1/ol/withdrawals/{withdrawal_id}/audit/")
        self.assertEqual(audit.status_code, 200)
        self.assertGreaterEqual(len(audit.data["data"]["results"]), 4)
