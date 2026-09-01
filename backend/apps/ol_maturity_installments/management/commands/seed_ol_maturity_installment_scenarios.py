"""Seed realistic OL Maturity Installments scenarios covering every state.

Creates exactly eight plans through the real services (creation, payment,
confirmation, missed detection, reversal, cancellation) plus four captured
failure proofs. Idempotent: stable policy numbers and idempotency keys mean a
re-run returns the previously seeded plans instead of duplicating them.
"""

import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.ol_maturity_installments.errors import MaturityInstallmentError
from apps.ol_maturity_installments.models import (
    InstallmentItemStatus,
    OLInstallmentItem,
    OLMaturityInstallmentPlan,
)
from apps.ol_maturity_installments.services.creation import create_installment_plan
from apps.ol_maturity_installments.services.lifecycle import (
    cancel_installment_plan,
    detect_missed_installments,
    reverse_item_payment,
)
from apps.ol_maturity_installments.services.payment import confirm_item_payment, process_item_payment
from apps.ol_maturity_installments.services.reconciliation import (
    validate_audit_consistency,
    validate_plan_reconciliation,
)
from apps.ol_parameters.models import OLAnticipatedEndowmentInstallmentRate
from apps.ol_policies.models import MaturityClaim, Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.ordinary_life.models import OLProduct
from apps.partners.models import Partner, PartnerBankAccount

MV = Decimal("25000000.00")
PREMIUM = Decimal("125000.00")


class Command(BaseCommand):
    help = "Seed eight OL Maturity Installments scenarios and capture failure proofs idempotently."

    # ------------------------------------------------------------------
    # Shared fixtures
    # ------------------------------------------------------------------

    def _ensure_admin(self):
        User = get_user_model()
        user, _created = User.objects.get_or_create(
            username="mip-seed-admin",
            defaults={
                "email": "mip.seed.admin@zic.local",
                "first_name": "Maturity",
                "last_name": "Seed Admin",
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if _created:
            user.set_password("Mip-seed-admin-2026!")
            user.save(update_fields=["password"])
        return user

    def _ensure_product(self):
        return OLProduct.objects.get_or_create(
            code="OL_ENDOWMENT_STANDARD",
            defaults={
                "name": "Endowment Standard",
                "business_area": "ORDINARY_LIFE",
                "is_active": True,
            },
        )[0]

    def _ensure_rates(self, product):
        created = []
        for code, frequency, factor in (
            ("MIP-SEED-QUARTERLY", "QUARTERLY", "25.00000000"),
            ("MIP-SEED-HALF_YEARLY", "HALF_YEARLY", "50.00000000"),
        ):
            _, was_created = OLAnticipatedEndowmentInstallmentRate.objects.get_or_create(
                code=code,
                defaults={
                    "name": f"Seed {frequency.replace('_', ' ').title()} installment rate",
                    "product": product,
                    "plan": None,
                    "installment_type": "ANTICIPATED_ENDOWMENT",
                    "frequency": frequency,
                    "term_from": None,
                    "term_to": None,
                    "rate_factor": Decimal(factor),
                    "currency": "",
                    "is_active": True,
                    "effective_from": date(2026, 1, 1),
                    "effective_to": None,
                },
            )
            created.append(was_created)
        # ANNUAL may already be provisioned (e.g. the existing R-PROBE3 row covers
        # term 10); only add a general ANNUAL row when none is active yet.
        if not OLAnticipatedEndowmentInstallmentRate.objects.filter(
            product=product,
            installment_type="ANTICIPATED_ENDOWMENT",
            frequency="ANNUAL",
            is_active=True,
        ).exists():
            _rate, was_created = OLAnticipatedEndowmentInstallmentRate.objects.get_or_create(
                code="MIP-SEED-ANNUAL",
                defaults={
                    "name": "Seed Annual installment rate",
                    "product": product,
                    "plan": None,
                    "installment_type": "ANTICIPATED_ENDOWMENT",
                    "frequency": "ANNUAL",
                    "term_from": None,
                    "term_to": None,
                    "rate_factor": Decimal("10.00000000"),
                    "currency": "",
                    "is_active": True,
                    "effective_from": date(2026, 1, 1),
                    "effective_to": None,
                },
            )
            created.append(was_created)
        return created

    def _agent(self):
        return Partner.objects.get_or_create(
            partner_number="ZIC-MIP-SC-A-0001",
            defaults={
                "partner_type": "AGENT",
                "partner_category": "INDIVIDUAL",
                "party_type": "INDIVIDUAL",
                "legal_name": "Seed Maturity Agent",
                "email": "mip.seed.agent@example.com",
            },
        )[0]

    def _partner(self, seq, label):
        return Partner.objects.get_or_create(
            partner_number=f"ZIC-MIP-SC-P-{seq:04d}",
            defaults={
                "partner_type": "CLIENT",
                "partner_category": "INDIVIDUAL",
                "party_type": "INDIVIDUAL",
                "legal_name": f"Seed Policyholder {label}",
                "email": f"mip.seed.p{seq:04d}@example.com",
                "mobile_number": f"+2557115{seq:04d}",
                "phone": f"+2557115{seq:04d}",
            },
        )[0]

    def _policy(self, code, partner, *, currency="TZS", status="MATURED", maturity_date=None, sum_assured=MV):
        number = f"POL-SC-{code}"
        existing = Policy.objects.filter(policy_number=number).first()
        if existing:
            return existing
        quotation = OLQuotation.objects.create(
            quote_number=f"QT-SC-{code}",
            quote_name=f"Quote SC-{code}",
            quote_date=date.today(),
            partner=partner,
            currency=currency,
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number=f"PROP-SC-{code}",
            status="POLICY_ISSUED",
            partner=partner,
            currency=currency,
        )
        return Policy.objects.create(
            policy_number=number,
            proposal_ref=proposal,
            partner=partner,
            agent=self._agent(),
            product_plan_ref="OL_ENDOWMENT_STANDARD",
            currency=currency,
            sum_assured=sum_assured,
            premium_amount=PREMIUM,
            premium_frequency="ANNUALLY",
            term_years=10,
            risk_commencement_date=date(2016, 1, 15),
            maturity_date=maturity_date or (timezone.localdate() - timedelta(days=90)),
            status=status,
        )

    def _claim(self, policy, *, seq):
        number = f"MAT-SC-{seq}"
        existing = MaturityClaim.objects.filter(claim_number=number).first()
        if existing:
            return existing
        return MaturityClaim.objects.create(
            policy=policy,
            claim_number=number,
            claim_date=timezone.localdate() - timedelta(days=30),
            maturity_value=policy.sum_assured,
            loan_deduction=Decimal("0.00"),
            net_payout=policy.sum_assured,
            payout_method="INSTALLMENTS",
            status="APPROVED",
        )

    def _bank(self, partner, *, currency="TZS"):
        return PartnerBankAccount.objects.get_or_create(
            partner=partner,
            account_number=f"0123{partner.partner_number[-4:]}789",
            defaults={
                "bank_name": "NBC Bank",
                "branch_name": "Dar es Salaam",
                "account_name": partner.legal_name,
                "swift_code": "NLCBTZTX",
                "iban": f"TZ0010123{partner.partner_number[-4:]}789",
                "currency": currency,
                "is_primary": True,
                "is_verified": True,
            },
        )[0]

    def _create_plan(self, policy, key, *, claim=None, frequency="ANNUAL", term_years=10, admin):
        existing = OLMaturityInstallmentPlan.objects.filter(idempotency_key=key).first()
        if existing:
            return existing, False
        return create_installment_plan(
            policy_id=policy.pk,
            maturity_claim_id=claim.pk if claim else None,
            frequency=frequency,
            term_years=term_years,
            idempotency_key=key,
            actor=admin,
            source_channel="BATCH",
        )

    def _plan_summary(self, plan):
        plan.refresh_from_db()
        item_rows = list(
            plan.items.values("installment_number", "status", "due_date", "paid_date").order_by(
                "installment_number"
            )
        )
        paid = OLInstallmentItem.objects.filter(plan_ref=plan, status=InstallmentItemStatus.PAID)
        paid_amount = str(sum((row.amount for row in paid), Decimal("0.00")))
        try:
            recon = validate_plan_reconciliation(plan_id=plan.pk)
            recon_status = recon.status
        except MaturityInstallmentError:
            recon_status = "ERROR"
        try:
            audit = validate_audit_consistency(plan_id=plan.pk)
            audit_status = audit.status
        except MaturityInstallmentError:
            audit_status = "ERROR"
        return {
            "plan_number": plan.plan_number,
            "policy_number": plan.policy_ref.policy_number,
            "claim_number": plan.maturity_claim_ref.claim_number if plan.maturity_claim_ref_id else None,
            "currency": plan.currency,
            "frequency": plan.frequency,
            "installment_count": plan.installment_count,
            "status": plan.status,
            "total_payable_amount": str(plan.total_payable_amount),
            "paid_amount": paid_amount,
            "paid_count": paid.count(),
            "items": item_rows,
            "reconciliation": recon_status,
            "audit_consistency": audit_status,
        }

    def _backdate(self, plan, offsets_by_number):
        """Simulate elapsed time by rewriting a freshly created item's due date."""
        for number, offset_days in offsets_by_number.items():
            item = plan.items.get(installment_number=number)
            item.due_date = timezone.localdate() + timedelta(days=offset_days)
            item.save(update_fields=["due_date"])

    def _pay(self, item, admin, *, paid_date=None):
        process_item_payment(item_id=item.pk, actor=admin, source_channel="BATCH")
        confirm_item_payment(item_id=item.pk, actor=admin, source_channel="BATCH", paid_date=paid_date)

    # ------------------------------------------------------------------
    # Scenario 1: standard active plan with mixed statuses (paid/missed)
    # ------------------------------------------------------------------

    def _scenario_mixed(self, admin):
        partner = self._partner(1, "Mixed Statuses")
        self._bank(partner)
        policy = self._policy("MIXED-0001", partner, status="MATURED")
        plan, created = self._create_plan(
            policy, "mip-seed-scenario-1", frequency="QUARTERLY", term_years=1, admin=admin
        )
        if not created:
            return self._plan_summary(plan)
        self._backdate(plan, {1: -180, 2: -120, 3: 30, 4: 60})
        # Pay installment 1 (activates the plan), miss installment 2, and leave 3-4 scheduled.
        self._pay(plan.items.get(installment_number=1), admin, paid_date=timezone.localdate() - timedelta(days=180))
        detect_missed_installments(as_of=timezone.localdate(), plan_id=plan.pk, actor=admin, source_channel="BATCH")
        return self._plan_summary(plan)

    # ------------------------------------------------------------------
    # Scenario 2: fully completed plan
    # ------------------------------------------------------------------

    def _scenario_completed(self, admin):
        partner = self._partner(2, "Completed")
        self._bank(partner)
        policy = self._policy("DONE-0002", partner, status="MATURED")
        plan, created = self._create_plan(
            policy, "mip-seed-scenario-2", frequency="ANNUAL", term_years=10, admin=admin
        )
        if not created:
            return self._plan_summary(plan)
        # Rewind each installment's due date so the plan has been running a full term.
        for number in range(1, plan.installment_count + 1):
            item = plan.items.get(installment_number=number)
            item.due_date = timezone.localdate() - timedelta(days=(plan.installment_count - number) * 30)
            item.save(update_fields=["due_date"])
        for number in range(1, plan.installment_count + 1):
            item = plan.items.get(installment_number=number)
            self._pay(item, admin, paid_date=item.due_date)
        plan.refresh_from_db()
        return self._plan_summary(plan)

    # ------------------------------------------------------------------
    # Scenario 3: plan with all payments missed
    # ------------------------------------------------------------------

    def _scenario_all_missed(self, admin):
        partner = self._partner(3, "All Missed")
        self._bank(partner)
        policy = self._policy("MISS-0003", partner, status="MATURED")
        plan, created = self._create_plan(
            policy, "mip-seed-scenario-3", frequency="QUARTERLY", term_years=1, admin=admin
        )
        if not created:
            return self._plan_summary(plan)
        self._backdate(plan, {1: -120, 2: -90, 3: -60, 4: -30})
        detect_missed_installments(as_of=timezone.localdate(), plan_id=plan.pk, actor=admin, source_channel="BATCH")
        return self._plan_summary(plan)

    # ------------------------------------------------------------------
    # Scenario 4: plan cancelled by admin
    # ------------------------------------------------------------------

    def _scenario_cancelled(self, admin):
        partner = self._partner(4, "Cancelled")
        self._bank(partner)
        policy = self._policy("CANCEL-0004", partner, status="MATURED")
        plan, created = self._create_plan(
            policy, "mip-seed-scenario-4", frequency="QUARTERLY", term_years=1, admin=admin
        )
        if not created:
            return self._plan_summary(plan)
        # Keep all installments future-dated so the plan never starts, then cancel.
        cancel_installment_plan(
            plan_id=plan.pk,
            reason="Policyholder changed maturity payout preference; plan cancelled by admin before any disbursement.",
            actor=admin,
            source_channel="ADMIN",
        )
        return self._plan_summary(plan)

    # ------------------------------------------------------------------
    # Scenario 5: plan with a reversed payment
    # ------------------------------------------------------------------

    def _scenario_reversed(self, admin):
        partner = self._partner(5, "Reversed Payment")
        self._bank(partner)
        policy = self._policy("REV-0005", partner, status="MATURED")
        plan, created = self._create_plan(
            policy, "mip-seed-scenario-5", frequency="HALF_YEARLY", term_years=1, admin=admin
        )
        if not created:
            return self._plan_summary(plan)
        item = plan.items.get(installment_number=1)
        self._pay(item, admin, paid_date=timezone.localdate())
        reverse_item_payment(
            item_id=item.pk,
            reason="Payment raised against a stale bank account; reversed within the reversal window.",
            actor=admin,
            source_channel="ADMIN",
        )
        return self._plan_summary(plan)

    # ------------------------------------------------------------------
    # Scenario 6: multi-currency plan
    # ------------------------------------------------------------------

    def _scenario_multi_currency(self, admin):
        partner = self._partner(6, "Multi Currency")
        self._bank(partner, currency="USD")
        policy = self._policy(
            "USD-0006",
            partner,
            currency="USD",
            status="MATURED",
            sum_assured=Decimal("250000.00"),
        )
        plan, created = self._create_plan(
            policy, "mip-seed-scenario-6", frequency="QUARTERLY", term_years=1, admin=admin
        )
        if not created:
            return self._plan_summary(plan)
        item = plan.items.get(installment_number=1)
        self._pay(item, admin, paid_date=timezone.localdate())
        return self._plan_summary(plan)

    # ------------------------------------------------------------------
    # Scenario 7: plan linked to a Maturity Claim
    # ------------------------------------------------------------------

    def _scenario_claim_linked(self, admin):
        partner = self._partner(7, "Claim Linked")
        self._bank(partner)
        policy = self._policy("CLAIM-0007", partner, status="MATURED")
        claim = self._claim(policy, seq=7)
        plan, created = self._create_plan(
            policy, "mip-seed-scenario-7", claim=claim, frequency="QUARTERLY", term_years=1, admin=admin
        )
        if not created:
            return self._plan_summary(plan)
        item = plan.items.get(installment_number=1)
        self._pay(item, admin, paid_date=timezone.localdate())
        claim.refresh_from_db()
        summary = self._plan_summary(plan)
        summary["claim_status"] = claim.status
        return summary

    # ------------------------------------------------------------------
    # Scenario 8: plan created from policy maturity only (no claim)
    # ------------------------------------------------------------------

    def _scenario_policy_only(self, admin):
        partner = self._partner(8, "Policy Only")
        self._bank(partner)
        policy = self._policy("POLONLY-0008", partner, status="MATURED")
        plan, created = self._create_plan(
            policy, "mip-seed-scenario-8", frequency="ANNUAL", term_years=10, admin=admin
        )
        return self._plan_summary(plan)

    # ------------------------------------------------------------------
    # Failure proofs
    # ------------------------------------------------------------------

    def _proof(self, attempted, expected_code, action):
        try:
            action()
            return {
                "attempted": attempted,
                "expected_error_code": expected_code,
                "raised": False,
                "message": "The call unexpectedly succeeded.",
            }
        except MaturityInstallmentError as exc:
            return {
                "attempted": attempted,
                "expected_error_code": expected_code,
                "raised": True,
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "details": exc.details,
                "resolution_steps": exc.resolution_steps,
            }

    def _failure_proofs(self, admin):
        # F1: create plan for an immature policy.
        partner = self._partner(9, "Immature Failure")
        policy = self._policy(
            "IMMATURE-0009",
            partner,
            status="ACTIVE",
            maturity_date=timezone.localdate() + timedelta(days=365),
        )
        f1 = self._proof(
            "create plan for immature policy",
            "PLAN_POLICY_NOT_MATURED",
            lambda: create_installment_plan(
                policy_id=policy.pk,
                frequency="ANNUAL",
                term_years=10,
                idempotency_key="mip-seed-failure-1",
                actor=admin,
                source_channel="API",
            ),
        )

        # F2: process payment for an already paid item (reuse scenario 2).
        completed = OLMaturityInstallmentPlan.objects.get(idempotency_key="mip-seed-scenario-2")
        paid_item = completed.items.filter(status=InstallmentItemStatus.PAID).first()
        f2 = self._proof(
            "process payment for an already paid item",
            "INSTALLMENT_ITEM_INVALID_STATUS",
            lambda: process_item_payment(item_id=paid_item.pk, actor=admin, source_channel="API"),
        )

        # F3: reverse a payment outside the configured window.
        partner = self._partner(10, "Reversal Window Failure")
        self._bank(partner)
        policy = self._policy("WINDOW-0010", partner, status="MATURED")
        plan, _created = self._create_plan(
            policy, "mip-seed-failure-3", frequency="QUARTERLY", term_years=1, admin=admin
        )
        item = plan.items.get(installment_number=1)
        if item.status != InstallmentItemStatus.PAID:
            self._pay(item, admin, paid_date=timezone.localdate())
        item.paid_date = timezone.localdate() - timedelta(days=30)
        item.save(update_fields=["paid_date"])
        f3 = self._proof(
            "reverse a payment outside the reversal window",
            "INSTALLMENT_REVERSAL_WINDOW_EXPIRED",
            lambda: reverse_item_payment(
                item_id=item.pk,
                reason="Attempting to reverse a payment made more than the window allows.",
                actor=admin,
                source_channel="API",
            ),
        )

        # F4: duplicate idempotent creation (replay scenario 8's key).
        original = OLMaturityInstallmentPlan.objects.get(idempotency_key="mip-seed-scenario-8")
        count_before = OLMaturityInstallmentPlan.objects.count()
        replayed, created = create_installment_plan(
            policy_id=original.policy_ref_id,
            frequency="ANNUAL",
            term_years=10,
            idempotency_key="mip-seed-scenario-8",
            actor=admin,
            source_channel="API",
        )
        count_after = OLMaturityInstallmentPlan.objects.count()
        f4 = {
            "attempted": "duplicate idempotent plan creation",
            "replayed_created_flag": created,
            "replayed_plan_number": replayed.plan_number,
            "original_plan_number": original.plan_number,
            "same_plan": replayed.pk == original.pk,
            "row_delta": count_after - count_before,
            "expected": "no duplicate row; same plan returned",
        }

        return {"immature_policy": f1, "already_paid_item": f2, "reverse_outside_window": f3, "duplicate_idempotent": f4}

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    @transaction.atomic
    def handle(self, *args, **options):
        admin = self._ensure_admin()
        product = self._ensure_product()
        self._ensure_rates(product)
        self._agent()

        scenarios = {
            "1_standard_active_mixed_statuses": self._scenario_mixed(admin),
            "2_fully_completed": self._scenario_completed(admin),
            "3_all_payments_missed": self._scenario_all_missed(admin),
            "4_cancelled_by_admin": self._scenario_cancelled(admin),
            "5_reversed_payment": self._scenario_reversed(admin),
            "6_multi_currency": self._scenario_multi_currency(admin),
            "7_linked_to_maturity_claim": self._scenario_claim_linked(admin),
            "8_policy_maturity_only": self._scenario_policy_only(admin),
        }
        failures = self._failure_proofs(admin)

        report = {
            "seeded_at": timezone.now().isoformat(),
            "scenarios": scenarios,
            "failure_proofs": failures,
        }
        self.stdout.write(json.dumps(report, indent=2, default=str))
        self.stdout.write(
            self.style.SUCCESS(
                f"OL Maturity Installments scenarios seeded: {len(scenarios)} plans across every lifecycle state "
                f"with {len(failures)} captured failure proofs."
            )
        )
