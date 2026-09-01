from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.governance.services.audit_service import AuditService
from apps.ol_maturity_installments.models import (
    InstallmentItemStatus,
    InstallmentPlanStatus,
    OLInstallmentItem,
    OLMaturityInstallmentPlan,
)
from apps.ol_maturity_installments.services.reconciliation import (
    validate_audit_consistency,
    validate_plan_reconciliation,
)
from apps.ol_policies.models import Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner, PartnerBankAccount

RECONCILIATION_URL = "/api/v1/ol/maturity-installments/{plan_id}/reconciliation/"
PROCESS_URL = "/api/v1/ol/maturity-installments/items/{item_id}/process-payment/"
CONFIRM_URL = "/api/v1/ol/maturity-installments/items/{item_id}/confirm-payment/"


class ReconciliationTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="installments-recon",
            email="installments-recon@example.com",
            password="Strong-reconciliation-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-MIP-R-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Reconcilia Tor",
            email="reconcilia.tor@example.com",
            mobile_number="+255711700001",
            phone="+255711700001",
        )
        PartnerBankAccount.objects.create(
            partner=self.partner,
            bank_name="NBC Bank",
            branch_name="Dar es Salaam",
            account_name="Reconcilia Tor",
            account_number="1111111111",
            swift_code="NLCBTZTX",
            iban="TZ0011111111111",
            currency="TZS",
            is_primary=True,
            is_verified=True,
        )
        self.agent = Partner.objects.create(
            partner_number="ZIC-MIP-R-A-0001",
            partner_type="AGENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Recon Agent",
            email="recon.agent@example.com",
            mobile_number="+255711700002",
            phone="+255711700002",
        )
        self.policy = self._policy("POL-MIP-REC-0001", "QT-MIP-REC-0001", "PROP-MIP-REC-0001")
        self.plan = self._plan(total=Decimal("2000000.00"), count=2)
        self.item_one = self._item(1, date(2025, 1, 14), Decimal("1000000.00"))
        self.item_two = self._item(2, date(2026, 1, 14), Decimal("1000000.00"))
        self.client.force_authenticate(self.user)

    def _policy(self, policy_number, quote_number, proposal_number):
        quotation = OLQuotation.objects.create(
            quote_number=quote_number,
            quote_name="Recon quote",
            quote_date=date(2026, 1, 1),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number=proposal_number,
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
            product_plan_ref="OL_ENDOWMENT_STANDARD",
            currency="TZS",
            sum_assured=Decimal("25000000.00"),
            premium_amount=Decimal("125000.00"),
            premium_frequency="ANNUALLY",
            term_years=10,
            risk_commencement_date=date(2016, 1, 15),
            maturity_date=date(2026, 1, 14),
            status="MATURED",
        )

    def _plan(self, total=Decimal("2000000.00"), count=2, status=InstallmentPlanStatus.CREATED):
        return OLMaturityInstallmentPlan.objects.create(
            policy_ref=self.policy,
            partner=self.partner,
            currency="TZS",
            total_maturity_value=total,
            total_payable_amount=total,
            installment_count=count,
            frequency="ANNUAL",
            start_date=date(2025, 1, 14),
            end_date=date(2026, 1, 14),
            status=status,
            created_by=self.user,
        )

    def _item(self, number, due_date, amount, plan=None, status=InstallmentItemStatus.SCHEDULED):
        return OLInstallmentItem.objects.create(
            plan_ref=plan or self.plan,
            installment_number=number,
            due_date=due_date,
            amount=amount,
            status=status,
            created_by=self.user,
        )

    def _pay(self, item):
        self.client.post(PROCESS_URL.format(item_id=item.pk))
        response = self.client.post(CONFIRM_URL.format(item_id=item.pk))
        self.assertEqual(response.status_code, 200)

    # ------------------------------------------------------------------
    # Reconciliation service
    # ------------------------------------------------------------------

    def test_reconciliation_detects_missing_payments(self):
        self._pay(self.item_one)
        report = validate_plan_reconciliation(plan_id=self.plan.pk, actor=self.user)
        self.assertEqual(report.status, "FAIL")
        self.assertEqual(report.paid_amount, "1000000.00")
        self.assertEqual(report.missing_amount, "1000000.00")
        self.assertEqual(report.paid_item_count, 1)
        self.assertEqual(report.total_item_count, 2)
        codes = [item.code for item in report.discrepancies]
        self.assertIn("MISSING_PAYMENTS", codes)
        missing = [item for item in report.discrepancies if item.code == "MISSING_PAYMENTS"][0]
        self.assertEqual(missing.amount, "1000000.00")
        self.assertEqual(missing.item_numbers, [2])

    def test_reconciliation_passes_when_fully_paid(self):
        self._pay(self.item_one)
        self._pay(self.item_two)
        report = validate_plan_reconciliation(plan_id=self.plan.pk, actor=self.user)
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.paid_amount, "2000000.00")
        self.assertEqual(report.missing_amount, "0.00")
        self.assertEqual(report.discrepancies, [])

    def test_reconciliation_passes_within_tolerance(self):
        near = self._plan(total=Decimal("100.00"), count=1)
        item = self._item(1, date(2025, 1, 14), Decimal("99.99"), plan=near)
        self._pay(item)
        report = validate_plan_reconciliation(plan_id=near.pk, actor=self.user)
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.missing_amount, "0.01")

        strict = validate_plan_reconciliation(plan_id=near.pk, tolerance="0", actor=self.user)
        self.assertEqual(strict.status, "FAIL")
        self.assertEqual(strict.discrepancies[0].code, "MISSING_PAYMENTS")

    def test_reconciliation_reports_plan_total_mismatch(self):
        self.plan.total_maturity_value = Decimal("1999999.00")
        self.plan.save(update_fields=["total_maturity_value"])
        report = validate_plan_reconciliation(plan_id=self.plan.pk, actor=self.user)
        self.assertEqual(report.status, "FAIL")
        self.assertEqual(report.discrepancies[0].code, "PLAN_TOTAL_MISMATCH")

    def test_reconciliation_reports_over_payment(self):
        inflated = self._plan(total=Decimal("100.00"), count=1)
        item = self._item(1, date(2025, 1, 14), Decimal("150.00"), plan=inflated)
        self._pay(item)
        report = validate_plan_reconciliation(plan_id=inflated.pk, actor=self.user)
        self.assertEqual(report.status, "FAIL")
        codes = [entry.code for entry in report.discrepancies]
        self.assertIn("OVER_PAYMENT", codes)
        over = [entry for entry in report.discrepancies if entry.code == "OVER_PAYMENT"][0]
        self.assertEqual(over.amount, "50.00")

    def test_reconciliation_plan_not_found(self):
        from uuid import uuid4

        with self.assertRaises(Exception):
            validate_plan_reconciliation(plan_id=uuid4(), actor=self.user)

    # ------------------------------------------------------------------
    # Reconciliation endpoint
    # ------------------------------------------------------------------

    def test_endpoint_returns_fail_status_for_missing_payments(self):
        self._pay(self.item_one)
        response = self.client.get(RECONCILIATION_URL.format(plan_id=self.plan.pk))
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["status"], "FAIL")
        self.assertEqual(data["plan_number"], self.plan.plan_number)
        self.assertTrue(data["discrepancies"])
        self.assertEqual(data["discrepancies"][0]["code"], "MISSING_PAYMENTS")

    def test_endpoint_returns_pass_status_when_fully_paid(self):
        self._pay(self.item_one)
        self._pay(self.item_two)
        response = self.client.get(RECONCILIATION_URL.format(plan_id=self.plan.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["status"], "PASS")
        self.assertEqual(response.data["data"]["discrepancies"], [])

    def test_endpoint_returns_404_for_unknown_plan(self):
        from uuid import uuid4

        response = self.client.get(RECONCILIATION_URL.format(plan_id=uuid4()))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error_code"], "INSTALLMENT_PLAN_NOT_FOUND")

    # ------------------------------------------------------------------
    # Audit consistency utility
    # ------------------------------------------------------------------

    def test_audit_consistency_passes_on_fully_audited_data(self):
        AuditService.log_create(self.plan, actor=self.user, reason="Seeded plan.", source_channel="API")
        self._pay(self.item_one)
        report = validate_audit_consistency(plan_id=self.plan.pk, actor=self.user)
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.findings, [])
        self.assertEqual(report.checked_plans, 1)
        self.assertEqual(report.checked_items, 2)

    def test_audit_consistency_flags_unaudited_item_status(self):
        AuditService.log_create(self.plan, actor=self.user, reason="Seeded plan.", source_channel="API")
        self.item_one.status = InstallmentItemStatus.PAID
        self.item_one.save(update_fields=["status"])
        report = validate_audit_consistency(plan_id=self.plan.pk, actor=self.user)
        self.assertEqual(report.status, "FAIL")
        self.assertEqual(report.findings[0].code, "ITEM_STATUS_NOT_AUDITED")
        self.assertEqual(report.findings[0].entity_id, str(self.item_one.pk))
        self.assertEqual(report.findings[0].expected_status, "PAID")

    def test_audit_consistency_flags_missing_plan_audit(self):
        report = validate_audit_consistency(plan_id=self.plan.pk, actor=self.user)
        self.assertEqual(report.status, "FAIL")
        self.assertEqual(report.findings[0].code, "PLAN_MISSING_AUDIT")

    def test_audit_consistency_flags_plan_status_not_audited(self):
        AuditService.log_create(self.plan, actor=self.user, reason="Seeded plan.", source_channel="API")
        self.plan.status = InstallmentPlanStatus.ACTIVE
        self.plan.save(update_fields=["status"])
        report = validate_audit_consistency(plan_id=self.plan.pk, actor=self.user)
        self.assertEqual(report.status, "FAIL")
        codes = [finding.code for finding in report.findings]
        self.assertIn("PLAN_STATUS_NOT_AUDITED", codes)
        self.assertEqual(report.findings[0].expected_status, "ACTIVE")

    def test_audit_consistency_waived_items_have_audit_rows(self):
        AuditService.log_create(self.plan, actor=self.user, reason="Seeded plan.", source_channel="API")
        self.plan.status = InstallmentPlanStatus.ACTIVE
        self.plan.save(update_fields=["status"])
        self._pay(self.item_one)
        response = self.client.post(
            f"/api/v1/ol/maturity-installments/plans/{self.plan.pk}/cancel/",
            {"reason": "Waiver audit coverage."},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        report = validate_audit_consistency(plan_id=self.plan.pk, actor=self.user)
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.findings, [])
