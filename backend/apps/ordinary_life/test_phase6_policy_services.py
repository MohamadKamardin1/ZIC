from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Sum

from apps.governance.models import AuditLog
from apps.ordinary_life.models import (
    OLPaymentAllocation,
    OLPolicyStatusHistory,
    OLPolicyTransaction,
    OLPremiumInstallment,
)
from apps.ordinary_life.services.application_service import OrdinaryLifeApplicationService
from apps.ordinary_life.services.policy_service import OrdinaryLifePolicyService
from apps.ordinary_life.test_phase5_application_services import OrdinaryLifeApplicationServiceTests


class OrdinaryLifePolicyServiceTests(OrdinaryLifeApplicationServiceTests):
    def _ready_proposal(self):
        proposal = self._proposal()
        case = OrdinaryLifeApplicationService.start_underwriting(
            proposal,
            actor=self.actor,
            reason="Policy risk review opened",
        )
        OrdinaryLifeApplicationService.assess_risk(
            case,
            "APPROVED",
            actor=self.actor,
            reason="Standard risk accepted",
        )
        OrdinaryLifeApplicationService.approve_proposal(
            proposal,
            actor=self.actor,
            reason="Business approval completed",
        )
        first_premium = proposal.payment_obligations.get(obligation_type="FIRST_PREMIUM")
        return proposal, first_premium

    def _issue_policy(self):
        proposal, first_premium = self._ready_proposal()
        OrdinaryLifePolicyService.allocate_payment(
            first_premium,
            first_premium.amount,
            "RCPT-PHASE6-FIRST",
            actor=self.actor,
            reason="First premium received",
        )
        policy = OrdinaryLifePolicyService.issue_policy(
            proposal,
            actor=self.actor,
            start_date=date(2026, 8, 1),
            beneficiary_allocations=[
                {
                    "name": "Fatma Ali",
                    "relationship": "Spouse",
                    "id_number": "BEN-001",
                    "percentage": "60.00",
                },
                {
                    "name": "Juma Ali",
                    "relationship": "Child",
                    "id_number": "BEN-002",
                    "percentage": "40.00",
                },
            ],
            reason="Issue approved policy",
            idempotency_key="ISSUE-PHASE6-001",
        )
        return policy

    def test_issue_policy_creates_immutable_party_beneficiary_schedule_and_transaction_artifacts(self):
        policy = self._issue_policy()

        self.assertEqual(policy.status, "ACTIVE")
        self.assertEqual(policy.policyholder_partner_id, self.policyholder.pk)
        self.assertEqual(policy.life_assured_partner_id, self.policyholder.pk)
        self.assertEqual(policy.policy_parties.count(), 4)
        self.assertEqual(policy.beneficiaries.count(), 2)
        self.assertEqual(policy.beneficiary_allocations.filter(is_active=True).aggregate(total=Sum("percentage"))["total"], Decimal("100.00"))
        schedule = policy.premium_schedules.get(is_current=True)
        self.assertEqual(schedule.frequency, "ANNUAL")
        self.assertEqual(schedule.installment_count, 10)
        self.assertEqual(schedule.installments.count(), 10)
        self.assertEqual(policy.payment_obligations.filter(obligation_type="INSTALMENT").count(), 10)
        self.assertEqual(policy.transactions.filter(transaction_type="ISSUANCE").count(), 1)
        self.assertEqual(policy.status_history.count(), 1)
        self.assertTrue(
            AuditLog.objects.filter(
                model_name="olpolicy",
                object_id=str(policy.pk),
                action="ISSUE_POLICY",
            ).exists()
        )

        repeated = OrdinaryLifePolicyService.issue_policy(
            policy.proposal,
            actor=self.actor,
            beneficiary_allocations=[],
            idempotency_key="ISSUE-PHASE6-001",
        )
        self.assertEqual(repeated.pk, policy.pk)
        self.assertEqual(policy.proposal.policy.pk, policy.pk)
        self.assertEqual(policy.transactions.filter(transaction_type="ISSUANCE").count(), 1)

    def test_issuance_requires_paid_first_premium_and_complete_beneficiary_total(self):
        proposal, first_premium = self._ready_proposal()
        with self.assertRaises(ValidationError):
            OrdinaryLifePolicyService.issue_policy(
                proposal,
                actor=self.actor,
                beneficiary_allocations=[{"name": "A", "relationship": "Spouse", "percentage": "100"}],
            )
        OrdinaryLifePolicyService.allocate_payment(
            first_premium,
            first_premium.amount,
            "RCPT-PHASE6-FIRST-2",
            actor=self.actor,
        )
        with self.assertRaises(ValidationError):
            OrdinaryLifePolicyService.issue_policy(
                proposal,
                actor=self.actor,
                beneficiary_allocations=[{"name": "A", "relationship": "Spouse", "percentage": "90"}],
            )

    def test_payment_allocation_is_exact_and_idempotent_by_receipt_reference(self):
        policy = self._issue_policy()
        obligation = policy.payment_obligations.filter(obligation_type="INSTALMENT").first()
        allocation = OrdinaryLifePolicyService.allocate_payment(
            obligation,
            obligation.amount,
            "RCPT-PHASE6-INST-001",
            actor=self.actor,
        )
        repeated = OrdinaryLifePolicyService.allocate_payment(
            obligation,
            obligation.amount,
            "RCPT-PHASE6-INST-001",
            actor=self.actor,
        )
        obligation.refresh_from_db()
        installment = OLPremiumInstallment.objects.get(pk=obligation.installment_id)
        self.assertEqual(allocation.pk, repeated.pk)
        self.assertEqual(obligation.status, "PAID")
        self.assertEqual(installment.status, "PAID")
        self.assertEqual(OLPaymentAllocation.objects.filter(obligation=obligation).count(), 1)
        with self.assertRaises(ValidationError):
            OrdinaryLifePolicyService.allocate_payment(
                obligation,
                Decimal("0.01"),
                "RCPT-PHASE6-INST-002",
                actor=self.actor,
            )

    def test_endorsement_requires_approval_and_preserves_before_after_snapshots(self):
        policy = self._issue_policy()
        endorsement = OrdinaryLifePolicyService.request_endorsement(
            policy,
            "SUM_ASSURED_CHANGE",
            {"sum_assured": "15000000.00"},
            requested_effective_date=date(2026, 9, 1),
            actor=self.actor,
            reason="Customer requested additional protection",
        )
        with self.assertRaises(ValidationError):
            OrdinaryLifePolicyService.apply_endorsement(endorsement, actor=self.actor)
        OrdinaryLifePolicyService.submit_endorsement(endorsement, actor=self.actor)
        OrdinaryLifePolicyService.approve_endorsement(endorsement, actor=self.actor, reason="Within underwriting authority")
        applied = OrdinaryLifePolicyService.apply_endorsement(
            endorsement,
            actor=self.actor,
            idempotency_key="ENDORSEMENT-PHASE6-001",
        )
        policy.refresh_from_db()
        self.assertEqual(applied.status, "APPLIED")
        self.assertEqual(policy.sum_assured, Decimal("15000000.00"))
        self.assertEqual(applied.before_snapshot["sum_assured"], "10000000.00")
        self.assertEqual(applied.after_snapshot["sum_assured"], "15000000.00")
        self.assertEqual(policy.transactions.filter(transaction_type="ENDORSEMENT").count(), 1)

    def test_lapse_requires_overdue_obligation_and_cancellation_writes_status_history(self):
        policy = self._issue_policy()
        obligation = policy.payment_obligations.filter(obligation_type="INSTALMENT").first()
        obligation.due_date = date(2026, 7, 1)
        obligation.save(update_fields=["due_date", "updated_at"])
        policy = OrdinaryLifePolicyService.lapse_policy(
            policy,
            actor=self.actor,
            as_of=date(2026, 8, 15),
            reason="Premium remained unpaid after grace period",
            idempotency_key="LAPSE-PHASE6-001",
        )
        policy.refresh_from_db()
        self.assertEqual(policy.status, "LAPSED")
        self.assertEqual(policy.transactions.filter(transaction_type="STATUS_CHANGE").count(), 1)
        cancelled = OrdinaryLifePolicyService.cancel_policy(
            policy,
            actor=self.actor,
            effective_date=date(2026, 8, 20),
            reason="Customer cancellation request",
            idempotency_key="CANCEL-PHASE6-001",
        )
        self.assertEqual(cancelled.status, "CANCELLED")
        policy.refresh_from_db()
        self.assertEqual(policy.status, "CANCELLED")
        self.assertEqual(policy.transactions.filter(transaction_type="CANCELLATION").count(), 1)
        self.assertEqual(OLPolicyStatusHistory.objects.filter(policy=policy).count(), 3)

    def test_renewal_requires_paid_renewal_premium_before_application(self):
        policy = self._issue_policy()
        renewal = OrdinaryLifePolicyService.request_renewal(
            policy,
            requested_effective_date=date(2036, 8, 1),
            new_end_date=date(2046, 7, 31),
            actor=self.actor,
            reason="Customer elected continuation",
        )
        OrdinaryLifePolicyService.submit_renewal(renewal, actor=self.actor)
        renewal = OrdinaryLifePolicyService.approve_renewal(renewal, actor=self.actor, reason="Renewal accepted")
        with self.assertRaises(ValidationError):
            OrdinaryLifePolicyService.apply_renewal(renewal, actor=self.actor)
        OrdinaryLifePolicyService.allocate_payment(
            renewal.payment_obligation,
            renewal.payment_obligation.amount,
            "RCPT-PHASE6-RENEWAL-001",
            actor=self.actor,
        )
        applied = OrdinaryLifePolicyService.apply_renewal(
            renewal,
            actor=self.actor,
            idempotency_key="RENEWAL-PHASE6-001",
        )
        policy.refresh_from_db()
        self.assertEqual(applied.status, "APPLIED")
        self.assertEqual(policy.end_date, date(2046, 7, 31))
        self.assertEqual(policy.transactions.filter(transaction_type="RENEWAL").count(), 1)

    def test_reinstatement_requires_paid_arrears_and_reactivates_lapsed_policy(self):
        policy = self._issue_policy()
        overdue = policy.payment_obligations.filter(obligation_type="INSTALMENT").first()
        overdue.due_date = date(2026, 7, 1)
        overdue.save(update_fields=["due_date", "updated_at"])
        OrdinaryLifePolicyService.lapse_policy(
            policy,
            actor=self.actor,
            as_of=date(2026, 8, 15),
            reason="Unpaid premium",
        )
        request = OrdinaryLifePolicyService.request_reinstatement(
            policy,
            requested_effective_date=date(2026, 8, 20),
            actor=self.actor,
            reason="Customer settled arrears request",
        )
        OrdinaryLifePolicyService.submit_reinstatement(request, actor=self.actor)
        request = OrdinaryLifePolicyService.approve_reinstatement(request, actor=self.actor, reason="Reinstatement accepted")
        with self.assertRaises(ValidationError):
            OrdinaryLifePolicyService.apply_reinstatement(request, actor=self.actor)
        OrdinaryLifePolicyService.allocate_payment(
            request.payment_obligation,
            request.payment_obligation.amount,
            "RCPT-PHASE6-REINSTATE-001",
            actor=self.actor,
        )
        applied = OrdinaryLifePolicyService.apply_reinstatement(
            request,
            actor=self.actor,
            idempotency_key="REINSTATE-PHASE6-001",
        )
        policy.refresh_from_db()
        self.assertEqual(applied.status, "APPLIED")
        self.assertEqual(policy.status, "ACTIVE")
        self.assertEqual(policy.transactions.filter(transaction_type="REINSTATEMENT").count(), 1)

    def test_maturity_is_guarded_by_contractual_end_date(self):
        policy = self._issue_policy()
        with self.assertRaises(ValidationError):
            OrdinaryLifePolicyService.mature_policy(policy, actor=self.actor, as_of=date(2030, 1, 1), reason="Too early")
        matured = OrdinaryLifePolicyService.mature_policy(
            policy,
            actor=self.actor,
            as_of=date(2036, 8, 1),
            reason="Contractual term completed",
            idempotency_key="MATURITY-PHASE6-001",
        )
        policy.refresh_from_db()
        self.assertEqual(matured.status, "MATURED")
        self.assertEqual(policy.status, "MATURED")
        self.assertEqual(policy.transactions.filter(transaction_type="MATURITY").count(), 1)
        self.assertEqual(OLPolicyTransaction.objects.filter(policy=policy, idempotency_key="MATURITY-PHASE6-001").count(), 1)
