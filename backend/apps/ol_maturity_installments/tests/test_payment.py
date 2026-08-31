from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.common.models import DomainEvent
from apps.front_office.models import FORequisition
from apps.governance.models import AuditLog
from apps.ol_maturity_installments.events import INSTALLMENT_PAYMENT_DUE, INSTALLMENT_PLAN_COMPLETED
from apps.ol_maturity_installments.models import (
    InstallmentItemStatus,
    InstallmentPlanStatus,
    OLInstallmentItem,
    OLMaturityInstallmentPlan,
)
from apps.ol_policies.models import Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner, PartnerBankAccount

PROCESS_URL = "/api/v1/ol/maturity-installments/items/{item_id}/process-payment/"
CONFIRM_URL = "/api/v1/ol/maturity-installments/items/{item_id}/confirm-payment/"


class InstallmentPaymentTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="installments-payer",
            email="installments-payer@example.com",
            password="Strong-installments-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-MIP-P-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Kito Milipaji",
            email="kito.payment@example.com",
            mobile_number="+255711500001",
            phone="+255711500001",
        )
        self.bank_account = PartnerBankAccount.objects.create(
            partner=self.partner,
            bank_name="NBC Bank",
            branch_name="Dar es Salaam",
            account_name="Kito Milipaji",
            account_number="0123456789",
            swift_code="NLCBTZTX",
            iban="TZ0010123456789",
            currency="TZS",
            is_primary=True,
            is_verified=True,
        )
        self.agent = Partner.objects.create(
            partner_number="ZIC-MIP-P-A-0001",
            partner_type="AGENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Payi Payment Agent",
            email="payi.payment@example.com",
            mobile_number="+255711500002",
            phone="+255711500002",
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-MIP-PAY-0001",
            quote_name="Quote payment",
            quote_date=date(2026, 1, 1),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-MIP-PAY-0001",
            status="POLICY_ISSUED",
            partner=self.partner,
            agent_partner=self.agent,
            currency="TZS",
        )
        self.policy = Policy.objects.create(
            policy_number="POL-MIP-PAY-0001",
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
        self.plan = OLMaturityInstallmentPlan.objects.create(
            policy_ref=self.policy,
            partner=self.partner,
            currency="TZS",
            total_maturity_value=Decimal("25000000.00"),
            total_payable_amount=Decimal("25000000.00"),
            installment_count=2,
            frequency="ANNUAL",
            start_date=date(2025, 1, 14),
            end_date=date(2026, 1, 14),
            status=InstallmentPlanStatus.CREATED,
            created_by=self.user,
        )
        self.item_one = self._item(1, date(2025, 1, 14), Decimal("12500000.00"))
        self.item_two = self._item(2, date(2026, 1, 14), Decimal("12500000.00"))
        self.client.force_authenticate(self.user)

    def _item(self, number, due_date, amount):
        return OLInstallmentItem.objects.create(
            plan_ref=self.plan,
            installment_number=number,
            due_date=due_date,
            amount=amount,
            status=InstallmentItemStatus.SCHEDULED,
            created_by=self.user,
        )

    def _process(self, item):
        return self.client.post(PROCESS_URL.format(item_id=item.pk))

    def _confirm(self, item):
        return self.client.post(CONFIRM_URL.format(item_id=item.pk))

    def test_process_payment_creates_requisition_and_updates_status(self):
        response = self._process(self.item_one)
        self.assertEqual(response.status_code, 201)
        data = response.data["data"]
        self.assertEqual(data["item"]["status"], "PAYMENT_PENDING")
        self.assertEqual(data["item"]["payment_bank_details"]["account_number"], "0123456789")
        self.assertEqual(data["item"]["payment_bank_details"]["bank_name"], "NBC Bank")
        requisition = FORequisition.objects.get(requisition_number=data["requisition"]["requisition_number"])
        self.assertTrue(data["requisition"]["requisition_number"])
        self.assertEqual(data["requisition"]["status"], "PENDING")

        item = OLInstallmentItem.objects.get(pk=self.item_one.pk)
        self.assertEqual(item.status, InstallmentItemStatus.PAYMENT_PENDING)
        self.assertEqual(item.payment_requisition_ref, requisition)
        self.assertEqual(item.payment_bank_details["account_name"], "Kito Milipaji")
        self.assertEqual(requisition.amount, Decimal("12500000.00"))
        self.assertEqual(requisition.department, "MATURITY_INSTALLMENTS")

        event = DomainEvent.objects.filter(
            event_type=INSTALLMENT_PAYMENT_DUE,
            aggregate_id=str(self.plan.pk),
        ).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.payload["item_id"], str(item.pk))
        self.assertEqual(event.payload["to_status"], "PAYMENT_PENDING")
        self.assertEqual(event.payload["metadata"]["requisition_number"], requisition.requisition_number)

    def test_confirmation_completes_item_and_plan(self):
        self._process(self.item_one)
        response = self._process(self.item_two)
        self.assertEqual(response.status_code, 201)

        first = self._confirm(self.item_one)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["data"]["item"]["status"], "PAID")
        self.assertTrue(first.data["data"]["paid_date"])
        self.assertFalse(first.data["data"]["plan_completed"])
        self.assertEqual(
            OLMaturityInstallmentPlan.objects.get(pk=self.plan.pk).status,
            InstallmentPlanStatus.CREATED,
        )

        second = self._confirm(self.item_two)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["data"]["item"]["status"], "PAID")
        self.assertTrue(second.data["data"]["plan_completed"])

        plan = OLMaturityInstallmentPlan.objects.get(pk=self.plan.pk)
        self.assertEqual(plan.status, InstallmentPlanStatus.COMPLETED)
        self.assertIsNotNone(plan.completed_at)
        self.assertEqual(plan.completed_by, self.user)
        item = OLInstallmentItem.objects.get(pk=self.item_two.pk)
        self.assertEqual(item.status, InstallmentItemStatus.PAID)
        self.assertEqual(item.paid_date, date.today())

        completed = DomainEvent.objects.filter(
            event_type=INSTALLMENT_PLAN_COMPLETED,
            aggregate_id=str(self.plan.pk),
        ).first()
        self.assertIsNotNone(completed)
        self.assertEqual(completed.payload["to_status"], "COMPLETED")

    def test_idempotent_processing_returns_existing_requisition(self):
        first = self._process(self.item_one)
        second = self._process(self.item_one)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(
            first.data["data"]["requisition"]["requisition_number"],
            second.data["data"]["requisition"]["requisition_number"],
        )
        self.assertEqual(FORequisition.objects.count(), 1)

    def test_idempotent_confirmation_is_safe(self):
        self._process(self.item_one)
        first = self._confirm(self.item_one)
        second = self._confirm(self.item_one)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["data"]["item"]["status"], "PAID")
        self.assertEqual(second.data["data"]["item"]["status"], "PAID")
        self.assertFalse(second.data["data"]["plan_completed"])

    def test_audit_row_complete(self):
        self._process(self.item_one)
        self._confirm(self.item_one)
        processed = AuditLog.objects.filter(
            app_label="ol_maturity_installments",
            model_name="olinstallmentitem",
            object_id=str(self.item_one.pk),
            action="INSTALLMENT_PAYMENT_PROCESSED",
        ).latest("created_at")
        self.assertEqual(processed.user, self.user)
        self.assertTrue(processed.after_state["requisition_number"])
        confirmed = AuditLog.objects.filter(
            app_label="ol_maturity_installments",
            model_name="olinstallmentitem",
            object_id=str(self.item_one.pk),
            action="INSTALLMENT_PAYMENT_CONFIRMED",
        ).latest("created_at")
        self.assertEqual(confirmed.user, self.user)
        self.assertEqual(confirmed.after_state["paid_date"], str(date.today()))

    def test_future_due_installment_blocked(self):
        future = self._item(9, date(2035, 1, 14), Decimal("1250000.00"))
        response = self._process(future)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "INSTALLMENT_PAYMENT_NOT_DUE")
        self.assertTrue(response.data["resolution_steps"])
        self.assertEqual(
            OLInstallmentItem.objects.get(pk=future.pk).status,
            InstallmentItemStatus.SCHEDULED,
        )

    def test_missing_bank_details_blocked(self):
        no_bank_partner = Partner.objects.create(
            partner_number="ZIC-MIP-P-NB-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="No Bank Holder",
            email="nobank@example.com",
            mobile_number="+255711500003",
            phone="+255711500003",
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-MIP-PAY-NB-0001",
            quote_name="No bank quote",
            quote_date=date(2026, 1, 1),
            partner=no_bank_partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-MIP-PAY-NB-0001",
            status="POLICY_ISSUED",
            partner=no_bank_partner,
            currency="TZS",
        )
        policy = Policy.objects.create(
            policy_number="POL-MIP-PAY-NB-0001",
            proposal_ref=proposal,
            partner=no_bank_partner,
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
        plan = OLMaturityInstallmentPlan.objects.create(
            policy_ref=policy,
            partner=no_bank_partner,
            currency="TZS",
            total_maturity_value=Decimal("25000000.00"),
            total_payable_amount=Decimal("25000000.00"),
            installment_count=1,
            frequency="ANNUAL",
            start_date=date(2026, 1, 14),
            end_date=date(2027, 1, 14),
            status=InstallmentPlanStatus.CREATED,
            created_by=self.user,
        )
        item = OLInstallmentItem.objects.create(
            plan_ref=plan,
            installment_number=1,
            due_date=date(2026, 1, 14),
            amount=Decimal("25000000.00"),
            status=InstallmentItemStatus.SCHEDULED,
            created_by=self.user,
        )
        response = self._process(item)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "INSTALLMENT_BANK_DETAILS_MISSING")
        self.assertEqual(
            OLInstallmentItem.objects.get(pk=item.pk).status,
            InstallmentItemStatus.SCHEDULED,
        )

    def test_paid_item_cannot_be_processed_again(self):
        self._process(self.item_one)
        self._confirm(self.item_one)
        response = self._process(self.item_one)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "INSTALLMENT_ITEM_INVALID_STATUS")
