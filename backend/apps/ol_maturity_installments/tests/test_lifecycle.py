from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.common.models import DomainEvent
from apps.front_office.models import FORequisition
from apps.governance.models import AuditLog
from apps.ol_maturity_installments.events import INSTALLMENT_PAYMENT_MISSED
from apps.ol_maturity_installments.models import (
    InstallmentItemStatus,
    InstallmentPlanStatus,
    OLInstallmentItem,
    OLMaturityInstallmentPlan,
)
from apps.ol_maturity_installments.services.lifecycle import detect_missed_installments
from apps.ol_policies.models import Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner, PartnerBankAccount
from apps.system_parameters.models import ParameterGroup, SystemParameter
from apps.system_parameters.services.config_service import ConfigurationService

REVERSE_URL = "/api/v1/ol/maturity-installments/items/{item_id}/reverse-payment/"
CANCEL_URL = "/api/v1/ol/maturity-installments/plans/{plan_id}/cancel/"
PROCESS_URL = "/api/v1/ol/maturity-installments/items/{item_id}/process-payment/"
CONFIRM_URL = "/api/v1/ol/maturity-installments/items/{item_id}/confirm-payment/"


class InstallmentLifecycleTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="installments-lifecycle",
            email="installments-lifecycle@example.com",
            password="Strong-lifecycle-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-MIP-L-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Lei Fe Cycle",
            email="lei.lifecycle@example.com",
            mobile_number="+255711600001",
            phone="+255711600001",
        )
        PartnerBankAccount.objects.create(
            partner=self.partner,
            bank_name="NBC Bank",
            branch_name="Dar es Salaam",
            account_name="Lei Fe Cycle",
            account_number="0987654321",
            swift_code="NLCBTZTX",
            iban="TZ0010987654321",
            currency="TZS",
            is_primary=True,
            is_verified=True,
        )
        self.agent = Partner.objects.create(
            partner_number="ZIC-MIP-L-A-0001",
            partner_type="AGENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Lifecycle Agent",
            email="lifecycle.agent@example.com",
            mobile_number="+255711600002",
            phone="+255711600002",
        )
        self.policy = self._policy("POL-MIP-LC-0001", "QT-MIP-LC-0001", "PROP-MIP-LC-0001")
        self.plan = self._plan(installment_count=3)
        self.item_one = self._item(1, date(2025, 1, 14), Decimal("1000000.00"))
        self.item_two = self._item(2, date(2026, 1, 14), Decimal("1000000.00"))
        self.client.force_authenticate(self.user)

    def _policy(self, policy_number, quote_number, proposal_number):
        quotation = OLQuotation.objects.create(
            quote_number=quote_number,
            quote_name="Lifecycle quote",
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

    def _plan(self, installment_count=3, status=InstallmentPlanStatus.CREATED, total=Decimal("3000000.00")):
        return OLMaturityInstallmentPlan.objects.create(
            policy_ref=self.policy,
            partner=self.partner,
            currency="TZS",
            total_maturity_value=total,
            total_payable_amount=total,
            installment_count=installment_count,
            frequency="ANNUAL",
            start_date=date(2025, 1, 14),
            end_date=date(2027, 1, 14),
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

    def _paid_item(self, item):
        self.client.post(PROCESS_URL.format(item_id=item.pk))
        response = self.client.post(CONFIRM_URL.format(item_id=item.pk))
        self.assertEqual(response.status_code, 200)
        return OLInstallmentItem.objects.get(pk=item.pk)

    # ------------------------------------------------------------------
    # Missed detection
    # ------------------------------------------------------------------

    def test_missed_detection_marks_overdue_items(self):
        pending = self._item(3, date(2025, 2, 14), Decimal("1000000.00"), status=InstallmentItemStatus.PAYMENT_PENDING)
        result = detect_missed_installments(
            as_of=date(2026, 8, 30),
            actor=self.user,
            source_channel="BATCH",
            correlation_id="BATCH-TEST-0001",
        )
        self.assertEqual(result.processed, 3)
        self.assertEqual(result.missed, 3)
        for item in (self.item_one, self.item_two, pending):
            refreshed = OLInstallmentItem.objects.get(pk=item.pk)
            self.assertEqual(refreshed.status, InstallmentItemStatus.MISSED)
            self.assertEqual(refreshed.missed_date, date(2026, 8, 30))

    def test_missed_detection_skips_future_and_already_missed(self):
        self._item(3, date(2030, 1, 14), Decimal("1000000.00"))
        result = detect_missed_installments(
            as_of=date(2026, 8, 30),
            actor=self.user,
        )
        self.assertEqual(result.missed, 2)
        future = OLInstallmentItem.objects.get(plan_ref=self.plan, installment_number=3)
        self.assertEqual(future.status, InstallmentItemStatus.SCHEDULED)

    def test_missed_detection_is_idempotent(self):
        detect_missed_installments(as_of=date(2026, 8, 30), actor=self.user)
        second = detect_missed_installments(as_of=date(2026, 8, 30), actor=self.user)
        self.assertEqual(second.processed, 0)
        self.assertEqual(second.missed, 0)
        self.assertEqual(
            OLInstallmentItem.objects.filter(status=InstallmentItemStatus.MISSED).count(),
            2,
        )

    def test_missed_detection_command_updates_status(self):
        call_command("detect_missed_installments", as_of="2026-08-30", plan_id=str(self.plan.pk))
        self.assertEqual(
            OLInstallmentItem.objects.filter(plan_ref=self.plan, status=InstallmentItemStatus.MISSED).count(),
            2,
        )
        batch = AuditLog.objects.filter(action="INSTALLMENT_MISSED_DETECTION_BATCH").latest("created_at")
        self.assertEqual(batch.after_state["missed"], 2)

    def test_missed_detection_emits_event_and_audits(self):
        detect_missed_installments(as_of=date(2026, 8, 30), actor=self.user)
        event = DomainEvent.objects.filter(
            event_type=INSTALLMENT_PAYMENT_MISSED,
            aggregate_id=str(self.plan.pk),
        ).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.payload["to_status"], "MISSED")
        self.assertEqual(event.payload["metadata"]["as_of"], "2026-08-30")
        audit = AuditLog.objects.filter(
            action="INSTALLMENT_PAYMENT_MISSED",
            object_id=str(self.item_one.pk),
        ).first()
        self.assertEqual(audit.after_state["status"], "MISSED")
        self.assertEqual(audit.after_state["missed_date"], "2026-08-30")

    # ------------------------------------------------------------------
    # Reversal
    # ------------------------------------------------------------------

    def test_reversal_restores_scheduled_when_not_due(self):
        today = date.today()
        item = self._item(9, today, Decimal("1000000.00"))
        item = self._paid_item(item)
        response = self.client.post(
            REVERSE_URL.format(item_id=item.pk),
            {"reason": "Duplicate disbursement, reversing."},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["item"]["status"], "SCHEDULED")
        requisition = FORequisition.objects.filter(pk=item.payment_requisition_ref_id).first()
        self.assertEqual(requisition.status, "REVERSED")
        refreshed = OLInstallmentItem.objects.get(pk=item.pk)
        self.assertEqual(refreshed.status, InstallmentItemStatus.SCHEDULED)
        self.assertIsNone(refreshed.paid_date)
        self.assertIsNone(refreshed.payment_requisition_ref_id)
        self.assertIsNone(refreshed.paid_by)

    def test_reversal_restores_missed_when_due_date_passed(self):
        item = self._paid_item(self.item_one)
        response = self.client.post(
            REVERSE_URL.format(item_id=item.pk),
            {"reason": "Payment made in error."},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["item"]["status"], "MISSED")
        requisition = FORequisition.objects.filter(pk=item.payment_requisition_ref_id).first()
        self.assertEqual(requisition.status, "REVERSED")

    def test_reversal_audit_records_actor_and_reason(self):
        item = self._paid_item(self.item_one)
        self.client.post(
            REVERSE_URL.format(item_id=item.pk),
            {"reason": "Payment made in error."},
            format="json",
        )
        audit = AuditLog.objects.filter(
            action="INSTALLMENT_PAYMENT_REVERSED",
            object_id=str(item.pk),
        ).latest("created_at")
        self.assertEqual(audit.user, self.user)
        self.assertEqual(audit.reason, "Installment 1 payment reversed: Payment made in error.")
        self.assertEqual(audit.before_state["status"], "PAID")
        self.assertEqual(audit.after_state["status"], "MISSED")
        self.assertEqual(audit.after_state["requisition_status"], "REVERSED")

    def test_reversal_requires_reason(self):
        item = self._paid_item(self.item_one)
        response = self.client.post(REVERSE_URL.format(item_id=item.pk), {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error_code"], "INSTALLMENT_REVERSAL_REASON_REQUIRED")

    def test_reversal_blocked_for_non_paid_item(self):
        response = self.client.post(
            REVERSE_URL.format(item_id=self.item_one.pk),
            {"reason": "Reversing early."},
            format="json",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "INSTALLMENT_REVERSAL_NOT_ALLOWED")

    def test_reversal_cannot_happen_twice(self):
        item = self._paid_item(self.item_one)
        first = self.client.post(
            REVERSE_URL.format(item_id=item.pk),
            {"reason": "First reversal."},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        second = self.client.post(
            REVERSE_URL.format(item_id=item.pk),
            {"reason": "Second reversal."},
            format="json",
        )
        self.assertEqual(second.status_code, 422)
        self.assertEqual(second.data["error_code"], "INSTALLMENT_REVERSAL_NOT_ALLOWED")

    def test_reversal_window_expired(self):
        item = self._paid_item(self.item_one)
        item.paid_date = date.today() - timedelta(days=10)
        item.save(update_fields=["paid_date"])
        response = self.client.post(
            REVERSE_URL.format(item_id=item.pk),
            {"reason": "Late reversal attempt."},
            format="json",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "INSTALLMENT_REVERSAL_WINDOW_EXPIRED")
        self.assertEqual(
            OLInstallmentItem.objects.get(pk=item.pk).status,
            InstallmentItemStatus.PAID,
        )

    def test_reversed_item_can_be_processed_again(self):
        item = self._paid_item(self.item_one)
        self.client.post(REVERSE_URL.format(item_id=item.pk), {"reason": "Re-process after reversal."}, format="json")
        response = self.client.post(PROCESS_URL.format(item_id=item.pk))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["item"]["status"], "PAYMENT_PENDING")
        self.assertEqual(FORequisition.objects.count(), 2)

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    def test_cancellation_cancels_active_plan(self):
        self.plan.status = InstallmentPlanStatus.ACTIVE
        self.plan.save(update_fields=["status"])
        paid = self._paid_item(self.item_one)
        pending_item = self._item(3, date(2026, 6, 14), Decimal("1000000.00"))
        processed = self.client.post(PROCESS_URL.format(item_id=pending_item.pk))
        self.assertEqual(processed.status_code, 201)
        pending = OLInstallmentItem.objects.get(pk=pending_item.pk)
        self.assertEqual(pending.status, InstallmentItemStatus.PAYMENT_PENDING)
        response = self.client.post(
            CANCEL_URL.format(plan_id=self.plan.pk),
            {"reason": "Policyholder no longer requires the instalment payout."},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        plan = OLMaturityInstallmentPlan.objects.get(pk=self.plan.pk)
        self.assertEqual(plan.status, InstallmentPlanStatus.CANCELLED)
        self.assertIsNotNone(plan.cancelled_at)
        self.assertEqual(plan.cancelled_by, self.user)
        self.assertEqual(
            OLInstallmentItem.objects.get(pk=self.item_two.pk).status,
            InstallmentItemStatus.WAIVED,
        )
        self.assertEqual(
            OLInstallmentItem.objects.get(pk=pending.pk).status,
            InstallmentItemStatus.WAIVED,
        )
        self.assertEqual(
            OLInstallmentItem.objects.get(pk=paid.pk).status,
            InstallmentItemStatus.PAID,
        )
        requisition = FORequisition.objects.filter(pk=pending.payment_requisition_ref_id).first()
        self.assertEqual(requisition.status, "CANCELLED")
        self.assertEqual(response.data["data"]["plan"]["status"], "CANCELLED")

    def test_cancellation_audit_records_actor_and_reason(self):
        self.plan.status = InstallmentPlanStatus.ACTIVE
        self.plan.save(update_fields=["status"])
        self.client.post(
            CANCEL_URL.format(plan_id=self.plan.pk),
            {"reason": "Operator decision."},
            format="json",
        )
        audit = AuditLog.objects.filter(
            action="INSTALLMENT_PLAN_CANCELLED",
            object_id=str(self.plan.pk),
        ).latest("created_at")
        self.assertEqual(audit.user, self.user)
        self.assertEqual(audit.reason, f"Plan {self.plan.plan_number} cancelled: Operator decision.")
        self.assertEqual(audit.before_state["status"], "ACTIVE")
        self.assertEqual(audit.after_state["status"], "CANCELLED")
        self.assertEqual(audit.after_state["waived_installments"], [1, 2])

    def test_cancellation_requires_reason(self):
        self.plan.status = InstallmentPlanStatus.ACTIVE
        self.plan.save(update_fields=["status"])
        response = self.client.post(CANCEL_URL.format(plan_id=self.plan.pk), {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error_code"], "INSTALLMENT_CANCELLATION_REASON_REQUIRED")

    def test_cancellation_blocked_for_terminal_plan(self):
        self.plan.status = InstallmentPlanStatus.COMPLETED
        self.plan.save(update_fields=["status"])
        response = self.client.post(
            CANCEL_URL.format(plan_id=self.plan.pk),
            {"reason": "Attempting to cancel a completed plan."},
            format="json",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "INSTALLMENT_PLAN_CANNOT_CANCEL")

    def test_cancellation_blocked_when_fully_paid(self):
        single = self._plan(installment_count=1, total=Decimal("1000000.00"), status=InstallmentPlanStatus.ACTIVE)
        single_item = self._item(1, date(2025, 1, 14), Decimal("1000000.00"), plan=single)
        self._paid_item(single_item)
        # A fully paid plan is normally completed on confirmation; force the
        # inconsistent state to exercise the not-fully-paid guard directly.
        single.status = InstallmentPlanStatus.ACTIVE
        single.save(update_fields=["status"])
        response = self.client.post(
            CANCEL_URL.format(plan_id=single.pk),
            {"reason": "Should be blocked when fully paid."},
            format="json",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "INSTALLMENT_PLAN_CANNOT_CANCEL")
        self.assertEqual(
            OLMaturityInstallmentPlan.objects.get(pk=single.pk).status,
            InstallmentPlanStatus.ACTIVE,
        )

    def test_cancellation_blocked_when_irrevocable(self):
        self.plan.status = InstallmentPlanStatus.ACTIVE
        self.plan.save(update_fields=["status"])
        self._paid_item(self.item_one)
        group, _created = ParameterGroup.objects.get_or_create(
            code="OL_MATURITY_INSTALLMENTS",
            defaults={"name": "OL Maturity Installments"},
        )
        SystemParameter.objects.create(
            group=group,
            code="INSTALLMENT_PAYMENT_IRREVOCABLE",
            name="Irrevocable payments",
            value_type="BOOLEAN",
            boolean_value=True,
            is_active=True,
        )
        ConfigurationService.invalidate_parameter("INSTALLMENT_PAYMENT_IRREVOCABLE")
        response = self.client.post(
            CANCEL_URL.format(plan_id=self.plan.pk),
            {"reason": "Should be blocked by irrevocable parameter."},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["error_code"], "INSTALLMENT_PLAN_IRREVOCABLE")
        self.assertEqual(
            OLMaturityInstallmentPlan.objects.get(pk=self.plan.pk).status,
            InstallmentPlanStatus.ACTIVE,
        )
        # The DB row rolls back with the test but the LocMemCache entry does
        # not; drop it so later tests are not gated by an irrevocable flag.
        ConfigurationService.invalidate_parameter("INSTALLMENT_PAYMENT_IRREVOCABLE")
