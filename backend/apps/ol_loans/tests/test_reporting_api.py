from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient, APITestCase

from apps.governance.models import AuditLog
from apps.ol_loans.models import LoanScheduleStatus, LoanStatus, OLLoan, OLLoanSchedule
from apps.ol_policies.models import Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner


class OLLoanReportingApiTestCase(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_superuser(
            username="loan-reporting-admin",
            email="loan-reporting-admin@example.com",
            password="Strong-loan-reporting-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-LOAN-REPORT-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Reporting Applicant",
            email="reporting.applicant@example.com",
        )
        self.agent = Partner.objects.create(
            partner_number="ZIC-LOAN-REPORT-A-0001",
            partner_type="AGENT",
            partner_category="INTERMEDIARY",
            party_type="ORGANIZATION",
            legal_name="Asha Insurance Agency",
            email="asha.loan.reporting.agent@example.com",
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-LOAN-REPORT-001",
            quote_name="Reporting test",
            quote_date=date.today(),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-LOAN-REPORT-001",
            status="CONVERTED",
            partner=self.partner,
            currency="TZS",
            prospect_snapshot={},
            financial_summary_snapshot={},
        )
        policy = Policy.objects.create(
            proposal_ref=proposal,
            partner=self.partner,
            agent=self.agent,
            product_plan_ref="OL_REPORT_PLAN",
            currency="TZS",
            sum_assured=Decimal("10000000.00"),
            premium_amount=Decimal("100000.00"),
            premium_frequency="MONTHLY",
            term_years=10,
            risk_commencement_date=date.today(),
            maturity_date=date(date.today().year + 10, date.today().month, date.today().day),
            status="ACTIVE",
            contract_snapshot={
                "branch_name": "ZIC Stone Town Branch",
                "branch_code": "ST-001",
                "product_name": "Education Protection Plan",
            },
        )
        self.loan = OLLoan.objects.create(
            loan_number="LOAN-REPORT-001",
            policy_ref=policy,
            partner=self.partner,
            currency="TZS",
            principal_amount=Decimal("1000.00"),
            disbursed_amount=Decimal("1000.00"),
            interest_rate=Decimal("0.12000000"),
            compounding_frequency="MONTHLY",
            term_months=12,
            status=LoanStatus.ACTIVE,
            disbursement_date=date(2026, 8, 1),
            maturity_date=date(2027, 8, 1),
            outstanding_balance=Decimal("700.00"),
        )
        OLLoanSchedule.objects.create(
            loan=self.loan,
            installment_number=1,
            due_date=date.today() - timedelta(days=10),
            principal_due=Decimal("300.00"),
            balance=Decimal("300.00"),
            status=LoanScheduleStatus.OVERDUE,
        )
        self.closed_loan = OLLoan.objects.create(
            loan_number="LOAN-REPORT-CLOSED-001",
            policy_ref=policy,
            partner=self.partner,
            currency="TZS",
            principal_amount=Decimal("2000.00"),
            disbursed_amount=Decimal("2000.00"),
            interest_rate=Decimal("0.12000000"),
            compounding_frequency="MONTHLY",
            term_months=12,
            disbursement_date=date(2026, 8, 2),
            maturity_date=date(2027, 8, 2),
            status=LoanStatus.CLOSED,
            total_repaid=Decimal("2000.00"),
            outstanding_balance=Decimal("0.00"),
        )

    def test_list_contains_required_columns_and_display_names(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/v1/ol/loans/?page_size=20&ordering=loan_number")
        self.assertEqual(response.status_code, 200)
        row = next(item for item in response.data["data"]["results"] if item["loan_number"] == self.loan.loan_number)
        for field in (
            "loan_number",
            "policy_number",
            "policyholder_name",
            "product_display",
            "principal_amount",
            "outstanding_balance",
            "status_display",
            "disbursement_date",
            "maturity_date",
            "agent_display",
            "branch_display",
            "allowed_actions",
        ):
            self.assertIn(field, row)
        self.assertEqual(row["policy_number"], self.loan.policy_ref.policy_number)
        self.assertEqual(row["policyholder_name"], self.partner.legal_name)
        self.assertEqual(row["product_display"], "Education Protection Plan")
        self.assertEqual(row["agent_display"], self.agent.legal_name)
        self.assertEqual(row["branch_display"], "ZIC Stone Town Branch")
        self.assertIn("repay", row["allowed_actions"])
        self.assertNotIn("policy_ref", row)
        self.assertNotIn("partner", row)

    def test_search_and_status_balance_overdue_product_agent_branch_filters(self):
        self.client.force_authenticate(self.staff)
        base = "/api/v1/ol/loans/"
        self.assertEqual(self.client.get(f"{base}?q={self.loan.loan_number}").data["data"]["count"], 1)
        self.assertEqual(self.client.get(f"{base}?status=ACTIVE&balance_gt_zero=true").data["data"]["count"], 1)
        self.assertEqual(self.client.get(f"{base}?overdue_only=true").data["data"]["count"], 1)
        self.assertEqual(self.client.get(f"{base}?product=OL_REPORT_PLAN").data["data"]["count"], 2)
        self.assertEqual(self.client.get(f"{base}?agent=Asha").data["data"]["count"], 2)
        self.assertEqual(self.client.get(f"{base}?branch=Stone%20Town").data["data"]["count"], 2)
        self.assertEqual(self.client.get(f"{base}?status=CLOSED").data["data"]["count"], 1)

    def test_kpis_aggregate_filtered_real_time_amounts(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/v1/ol/loans/kpis/?date_from=2026-08-01&date_to=2026-08-31")
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["currency"], "TZS")
        self.assertEqual(Decimal(data["total_disbursed_period"]), Decimal("3000.00"))
        self.assertEqual(Decimal(data["total_outstanding"]), Decimal("700.00"))
        self.assertEqual(data["active_count"], 1)
        self.assertEqual(data["defaulted_count"], 0)
        self.assertEqual(data["settled_count"], 1)
        self.assertEqual(Decimal(data["amounts_by_currency"]["TZS"]["total_disbursed_period"]), Decimal("3000.00"))
        self.assertTrue(data["timestamp"])

    def test_detail_includes_children_audit_timeline_and_allowed_actions(self):
        AuditLog.objects.create(
            user=self.staff,
            action_type="UPDATE",
            entity_type="OLLoan",
            entity_id=self.loan.pk,
            entity_repr=self.loan.loan_number,
            before_state={"status": LoanStatus.APPROVED},
            after_state={"status": LoanStatus.ACTIVE},
            description="Loan activated for reporting test.",
            action="LOAN_DISBURSED",
            app_label="ol_loans",
            model_name="olloan",
            object_id=str(self.loan.pk),
            object_repr=self.loan.loan_number,
            reason="Disbursement completed.",
            source_channel="API",
            correlation_id="REPORTING-DETAIL-001",
        )
        self.client.force_authenticate(self.staff)
        response = self.client.get(f"/api/v1/ol/loans/{self.loan.pk}/")
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["header"]["policyholder_name"], self.partner.legal_name)
        self.assertEqual(len(data["schedules"]), 1)
        self.assertEqual(data["repayments"], [])
        self.assertEqual(data["interest_accruals"], [])
        self.assertEqual(data["offsets"], [])
        self.assertTrue(any(item["action"] == "LOAN_DISBURSED" for item in data["audit_timeline"]))
        self.assertIn("repay", data["allowed_actions"])

    def test_csv_export_respects_filters_and_has_display_headers(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/v1/ol/loans/export/?status=ACTIVE")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("loan_number,policy_number,policyholder_name", body)
        self.assertIn(self.loan.loan_number, body)
        self.assertNotIn(self.closed_loan.loan_number, body)
        self.assertIn(self.agent.legal_name, body)


class OLLoanReportingPermissionTestCase(TestCase):
    def test_unauthenticated_kpi_and_export_are_denied(self):
        client = APIClient()
        self.assertEqual(client.get("/api/v1/ol/loans/kpis/").status_code, 401)
        self.assertEqual(client.get("/api/v1/ol/loans/export/").status_code, 401)
