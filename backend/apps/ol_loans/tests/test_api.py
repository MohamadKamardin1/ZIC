from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.ol_loans.models import LoanScheduleStatus, LoanStatus, OLLoan, OLLoanInterestAccrual, OLLoanRepayment, OLLoanSchedule
from apps.ol_policies.models import Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner


class OLLoanApiTestCase(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_superuser(
            username="loan-api-admin",
            email="loan-api-admin@example.com",
            password="Strong-loan-api-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-LOAN-API-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="API Applicant",
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-LOAN-API-001",
            quote_name="API test",
            quote_date=date.today(),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-LOAN-API-001",
            status="CONVERTED",
            partner=self.partner,
            currency="TZS",
            prospect_snapshot={},
            financial_summary_snapshot={},
        )
        policy = Policy.objects.create(
            proposal_ref=proposal,
            partner=self.partner,
            product_plan_ref="OL_API_PLAN",
            currency="TZS",
            sum_assured=Decimal("10000000.00"),
            premium_amount=Decimal("100000.00"),
            premium_frequency="MONTHLY",
            term_years=10,
            risk_commencement_date=date.today(),
            maturity_date=date(date.today().year + 10, date.today().month, date.today().day),
            status="ACTIVE",
        )
        self.loan = OLLoan.objects.create(
            loan_number="LOAN-API-001",
            policy_ref=policy,
            partner=self.partner,
            currency="TZS",
            principal_amount=Decimal("1000000.00"),
            interest_rate=Decimal("0.12000000"),
            compounding_frequency="MONTHLY",
            term_months=12,
            status=LoanStatus.REQUESTED,
            reason="Education support",
        )

    def test_policy_loan_eligibility_endpoint_returns_limit_contract(self):
        eligibility = {
            "policy_id": str(self.loan.policy_ref_id),
            "policy_number": self.loan.policy_ref.policy_number,
            "currency": "TZS",
            "policy_status": "ACTIVE",
            "eligible": True,
            "available_loan_limit": "1250000.00",
            "minimum_loan_amount": "100000.00",
            "maximum_loan_amount": "1250000.00",
            "repayment_modes": ["MONTHLY"],
        }
        self.client.force_authenticate(self.staff)
        with patch("apps.ol_loans.request_views.get_policy_loan_eligibility", return_value=eligibility):
            response = self.client.get(f"/api/v1/ol/policies/{self.loan.policy_ref_id}/loans/eligibility/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["available_loan_limit"], "1250000.00")
        self.assertEqual(response.data["data"]["repayment_modes"], ["MONTHLY"])

    def test_list_supports_search_pagination_and_display_fields(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/v1/ol/loans/?q=API-001&page=1&page_size=10")
        self.assertEqual(response.status_code, 200)
        payload = response.data["data"]
        self.assertEqual(payload["count"], 1)
        row = payload["results"][0]
        self.assertEqual(row["loan_number"], self.loan.loan_number)
        self.assertEqual(row["policy_display"], self.loan.policy_ref.policy_number)
        self.assertEqual(row["partner_display"], self.partner.legal_name)
        self.assertEqual(row["status_display"], "Requested")
        self.assertEqual(row["currency"], "TZS")

    def test_schedule_endpoint_returns_paginated_contractual_rows_and_aggregates(self):
        OLLoanSchedule.objects.create(
            loan=self.loan,
            installment_number=1,
            due_date=date.today(),
            principal_due=Decimal("80000.00"),
            interest_due=Decimal("6666.67"),
            penalty_due=Decimal("0.00"),
            principal_paid=Decimal("80000.00"),
            interest_paid=Decimal("6666.67"),
            amount_paid=Decimal("86666.67"),
            balance=Decimal("0.00"),
            status=LoanScheduleStatus.PAID,
        )
        self.client.force_authenticate(self.staff)
        response = self.client.get(f"/api/v1/ol/loans/{self.loan.pk}/schedule/?page=1&page_size=1")
        self.assertEqual(response.status_code, 200)
        payload = response.data["data"]
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["page_size"], 1)
        self.assertEqual(payload["results"][0]["installment_number"], 1)
        self.assertEqual(payload["results"][0]["status"], LoanScheduleStatus.PAID)

    def test_history_endpoints_return_immutable_repayment_and_accrual_rows(self):
        OLLoanRepayment.objects.create(
            loan=self.loan,
            receipt_ref="RCT-LOAN-API-001",
            amount=Decimal("125000.00"),
            currency="TZS",
            allocation_breakdown={"principal": "100000.00", "interest": "20000.00", "penalty": "5000.00"},
            source_channel="SYSTEM",
        )
        OLLoanInterestAccrual.objects.create(
            loan=self.loan,
            period_start=date.today().replace(day=1),
            period_end=date.today(),
            principal_base=Decimal("1000000.00"),
            interest_amount=Decimal("10000.00"),
            penalty_amount=Decimal("500.00"),
            cumulative_interest=Decimal("10500.00"),
            source_channel="SYSTEM",
        )
        self.client.force_authenticate(self.staff)
        repayments = self.client.get(f"/api/v1/ol/loans/{self.loan.pk}/repayments/")
        accruals = self.client.get(f"/api/v1/ol/loans/{self.loan.pk}/accruals/")
        self.assertEqual(repayments.status_code, 200)
        self.assertEqual(accruals.status_code, 200)
        self.assertEqual(repayments.data["data"]["results"][0]["source_channel"], "SYSTEM")
        self.assertEqual(repayments.data["data"]["results"][0]["allocation_breakdown"]["principal"], "100000.00")
        self.assertEqual(accruals.data["data"]["results"][0]["interest_amount"], "10000.00")
        self.assertEqual(accruals.data["data"]["results"][0]["cumulative_interest"], "10500.00")

    def test_retrieve_includes_child_collections_and_missing_loan_is_structured(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get(f"/api/v1/ol/loans/{self.loan.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["loan_number"], self.loan.loan_number)
        self.assertEqual(response.data["data"]["schedules"], [])
        self.assertEqual(response.data["data"]["repayments"], [])
        self.assertEqual(response.data["data"]["interest_accruals"], [])
        self.assertEqual(response.data["data"]["offsets"], [])

        missing = self.client.get("/api/v1/ol/loans/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.data["error_code"], "LOAN_NOT_FOUND")
        self.assertTrue(missing.data["resolution_steps"])

    def test_unauthenticated_list_is_denied(self):
        response = self.client.get("/api/v1/ol/loans/")
        self.assertEqual(response.status_code, 401)
