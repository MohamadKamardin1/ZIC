"""Seed a realistic, repeatable OL Policies demonstration dataset.

The command is intentionally additive and idempotent. It uses the issued-policy
and servicing services for transitions that exist in this bounded context. A
surrender is left as a paid payout handoff because payment settlement is owned
by the front-office/payment integration, not by the policy aggregate.
"""

import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand, call_command
from django.db import transaction

from apps.ol_commitments.models import CommitmentSourceType, OLCommitment
from apps.ol_parameters.models import (
    OLGracePeriod,
    OLLoanInterestControl,
    OLLoanSystemSetup,
    OLMaturityClaimSetup,
    OLPaidUpRate,
    OLPaidUpSetup,
    OLPlanType,
    OLProduct,
    OLReinstatementWindow,
    OLSurrenderSetup,
)
from apps.ol_policies.errors import PolicyError
from apps.ol_policies.models import (
    Policy,
    PolicyAuditLog,
    PolicyStatus,
    SurrenderStatus,
)
from apps.ol_policies.services.finance_service import (
    approve_policy_loan,
    disburse_policy_loan,
    request_policy_loan,
)
from apps.ol_policies.services.issuance_service import issue_policy_from_proposal
from apps.ol_policies.services.lifecycle_service import mark_policy_lapsed, reinstate_policy
from apps.ol_policies.services.maturity_service import create_maturity_claim, pay_maturity_claim
from apps.ol_policies.services.termination_service import (
    cancel_policy,
    convert_policy_to_paid_up,
    request_policy_surrender,
)
from apps.ol_proposals.models import OLProposal, OLProposalPlanConfig
from apps.ol_quotations.models import OLQuotation
from apps.ordinary_life.models import OLProduct as LegacyProduct
from apps.partners.models import Partner

SEED_PREFIX = "OL-SEED"


class Command(BaseCommand):
    help = "Seed eight idempotent Ordinary Life policy lifecycle scenarios and failure proofs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            help="Print the result as one JSON object instead of human-readable lines.",
        )

    def handle(self, *args, **options):
        actor = self._seed_actor()
        with transaction.atomic():
            call_command("seed_ol_policy_permissions", verbosity=0)
            self._seed_parameters()
            policies = [
                self._active_policy(actor),
                self._lapsed_policy(actor),
                self._reinstated_policy(actor),
                self._surrendered_policy(actor),
                self._matured_policy(actor),
                self._loan_policy(actor),
                self._cancelled_policy(actor),
                self._paid_up_policy(actor),
            ]
            failures = self._failure_proofs(actor)

        result = {
            "command": "seed_ol_policy_scenarios",
            "seeded_policy_numbers": [policy.policy_number for policy in policies],
            "policy_count": len(policies),
            "states": {policy.policy_number: policy.status for policy in policies},
            "failure_proofs": failures,
            "idempotent": True,
        }
        if options["json"]:
            self.stdout.write(json.dumps(result, sort_keys=True))
            return
        self.stdout.write(self.style.SUCCESS(f"Seeded/reused {len(policies)} OL policy scenarios."))
        for policy in policies:
            self.stdout.write(f"  {policy.policy_number}: {policy.status}")
        self.stdout.write("Failure proofs:")
        for key, proof in failures.items():
            self.stdout.write(f"  {key}: {proof['error_code']} — {proof['message']}")
        self.stdout.write(self.style.SUCCESS("The seed is idempotent; rerunning it reuses the same policy numbers."))

    def _seed_actor(self):
        User = get_user_model()
        actor, _ = User.objects.get_or_create(
            username="ol_policy_seed_operator",
            defaults={
                "email": "ol.policy.seed@zic.tz",
                "first_name": "OL Policy",
                "last_name": "Seed Operator",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if not actor.is_staff or not actor.is_superuser:
            actor.is_staff = True
            actor.is_superuser = True
            actor.save(update_fields=["is_staff", "is_superuser"])
        return actor

    def _partner(self, number, name, *, partner_type="CLIENT"):
        partner, _ = Partner.objects.get_or_create(
            partner_number=number,
            defaults={
                "partner_type": partner_type,
                "partner_category": "INDIVIDUAL",
                "party_type": "INDIVIDUAL",
                "legal_name": name,
                "first_name": name.split()[0],
                "surname": " ".join(name.split()[1:]),
                "email": f"{number.lower()}@zic.tz",
                "mobile_number": "+255700000001",
                "phone": "+255700000001",
                "is_active": True,
                "status": "ACTIVE",
            },
        )
        return partner

    def _quotation_and_proposal(self, suffix, partner, *, status="CONVERTED", commencement_days=400):
        quotation, _ = OLQuotation.objects.get_or_create(
            quote_number=f"{SEED_PREFIX}-Q-{suffix}",
            defaults={
                "quote_name": f"ZIC OL demonstration {suffix}",
                "quote_date": date.today() - timedelta(days=commencement_days),
                "partner": partner,
                "currency": "TZS",
            },
        )
        proposal, _ = OLProposal.objects.get_or_create(
            quotation=quotation,
            defaults={
                "proposal_number": f"{SEED_PREFIX}-PROP-{suffix}",
                "status": status,
                "partner": partner,
                "currency": "TZS",
                "prospect_snapshot": {"name": partner.legal_name, "identity_number": f"NIDA-{suffix}"},
                "financial_summary_snapshot": {"total_sum_assured": "50000000.00", "total_premium": "250000.00"},
            },
        )
        plan_config, _ = OLProposalPlanConfig.objects.get_or_create(
            proposal=proposal,
            section_number=1,
            defaults={
                "plan_name_snapshot": "ZIC OL Demonstration Plan",
                "sub_product_code": f"OL_SEED_{suffix}",
                "base_sum_assured": Decimal("50000000.00"),
                "term_years": 10,
                "payment_period_years": 10,
                "premium_frequency": "ANNUALLY",
                "quote_basis": "SUM_ASSURED",
                "estimated_maturity_value": Decimal("50000000.00"),
                "premium_factor": "NONE",
                "premium_amount": Decimal("250000.00"),
                "is_selected": True,
            },
        )
        if not plan_config.is_selected:
            plan_config.is_selected = True
            plan_config.save(update_fields=["is_selected"])
        return quotation, proposal

    def _issued_policy(self, suffix, partner, actor, *, policy_number=None, commencement_days=400):
        target_number = policy_number or f"{SEED_PREFIX}-{suffix}"
        existing = Policy.objects.filter(policy_number=target_number).first()
        if existing:
            return existing
        quotation, proposal = self._quotation_and_proposal(
            suffix,
            partner,
            status="AWAITING_FIRST_PREMIUM",
            commencement_days=commencement_days,
        )
        commitment, _ = OLCommitment.objects.get_or_create(
            commitment_number=f"{SEED_PREFIX}-FIRST-{suffix}",
            defaults={
                "source_type": CommitmentSourceType.PROPOSAL,
                "source_content_type": ContentType.objects.get_for_model(OLProposal),
                "source_object_id": str(proposal.pk),
                "source_reference": proposal.proposal_number,
                "partner": partner,
                "partner_name_snapshot": partner.legal_name,
                "currency": "TZS",
                "premium_frequency": "ANNUALLY",
                "due_date": date.today() - timedelta(days=commencement_days),
                "premium_amount": Decimal("250000.00"),
                "amount_paid": Decimal("250000.00"),
                "balance": Decimal("0.00"),
                "status": "COMPLETED",
            },
        )
        proposal.first_premium_commitment = commitment
        proposal.save(update_fields=["first_premium_commitment"])
        policy, _ = issue_policy_from_proposal(proposal.pk, actor=actor, source_channel="SEED")
        policy.policy_number = target_number
        policy.save(update_fields=["policy_number"])
        return policy

    def _policy_commitment(self, policy, suffix, actor, *, balance=Decimal("0.00"), status="COMPLETED", due_date=None):
        commitment, _ = OLCommitment.objects.get_or_create(
            commitment_number=f"{SEED_PREFIX}-POL-{suffix}",
            defaults={
                "source_type": CommitmentSourceType.POLICY,
                "source_content_type": ContentType.objects.get_for_model(Policy),
                "source_object_id": str(policy.pk),
                "source_reference": policy.policy_number,
                "partner": policy.partner,
                "partner_name_snapshot": policy.partner.legal_name,
                "currency": policy.currency,
                "premium_frequency": policy.premium_frequency,
                "installment_number": OLCommitment.objects.filter(source_reference=policy.policy_number).count() + 1,
                "due_date": due_date or date.today(),
                "premium_amount": policy.premium_amount,
                "amount_paid": max(Decimal("0.00"), policy.premium_amount - balance),
                "balance": balance,
                "status": status,
                "created_by": actor,
                "updated_by": actor,
            },
        )
        return commitment

    def _audit_seed(self, policy, event_type, actor, *, from_status="", reason="Seeded demonstration scenario"):
        PolicyAuditLog.objects.get_or_create(
            policy=policy,
            event_type=event_type,
            defaults={
                "actor": actor,
                "from_status": from_status,
                "to_status": policy.status,
                "before_snapshot": {"status": from_status} if from_status else {},
                "after_snapshot": {"status": policy.status, "policy_number": policy.policy_number},
                "reason": reason,
                "source_channel": "SYSTEM",
            },
        )

    def _active_policy(self, actor):
        partner = self._partner(f"{SEED_PREFIX}-P-ACTIVE", "Amina Active")
        return self._issued_policy("ACTIVE", partner, actor, policy_number=f"{SEED_PREFIX}-ACTIVE-001")

    def _lapsed_policy(self, actor):
        partner = self._partner(f"{SEED_PREFIX}-P-LAPSED", "Bakar Lapsed")
        policy = self._issued_policy("LAPSED", partner, actor, policy_number=f"{SEED_PREFIX}-LAPSED-001")
        if policy.status == PolicyStatus.ACTIVE:
            self._policy_commitment(
                policy,
                "LAPSED",
                actor,
                balance=Decimal("250000.00"),
                status="PENDING",
                due_date=date.today() - timedelta(days=30),
            )
            mark_policy_lapsed(policy, as_of=date.today(), actor=actor, source_channel="BATCH")
        return Policy.objects.get(pk=policy.pk)

    def _reinstated_policy(self, actor):
        partner = self._partner(f"{SEED_PREFIX}-P-REIN", "Chausiku Reinstated")
        policy = self._issued_policy("REIN", partner, actor, policy_number=f"{SEED_PREFIX}-REINSTATED-001")
        if policy.status == PolicyStatus.ACTIVE:
            self._policy_commitment(
                policy,
                "REIN",
                actor,
                balance=Decimal("250000.00"),
                status="PENDING",
                due_date=date.today() - timedelta(days=30),
            )
            mark_policy_lapsed(policy, as_of=date.today(), actor=actor, source_channel="BATCH")
        if policy.status == PolicyStatus.LAPSED:
            reinstate_policy(
                policy.pk,
                payment_amount=Decimal("999999.00"),
                medical_clearance=True,
                as_of=date.today(),
                actor=actor,
                source_channel="API",
            )
        policy = Policy.objects.get(pk=policy.pk)
        self._audit_seed(policy, "PolicyReinstatedHistoryPreserved", actor, from_status=PolicyStatus.LAPSED)
        return policy

    def _surrendered_policy(self, actor):
        partner = self._partner(f"{SEED_PREFIX}-P-SURR", "Dua Surrendered")
        policy = self._issued_policy(
            "SURR",
            partner,
            actor,
            policy_number=f"{SEED_PREFIX}-SURRENDERED-001",
            commencement_days=800,
        )
        if policy.status == PolicyStatus.ACTIVE:
            plan_type, _ = OLPlanType.objects.get_or_create(
                code=f"{SEED_PREFIX}-SURR-PLAN",
                defaults={"name": "Seed surrender plan", "is_active": True},
            )
            product, _ = OLProduct.objects.get_or_create(
                code=f"{SEED_PREFIX}-SURR-PRODUCT",
                defaults={
                    "name": "Seed surrender product",
                    "plan_type": plan_type,
                    "effective_from": date.today() - timedelta(days=3650),
                    "premium_frequencies": ["ANNUALLY"],
                    "is_active": True,
                },
            )
            policy.contract_snapshot = {
                **policy.contract_snapshot,
                "surrender_value_rate": "0.80",
                "plans": [{"product_id": str(product.pk), "product_code": product.code}],
            }
            policy.save(update_fields=["contract_snapshot"])
            for installment in range(1, 25):
                self._policy_commitment(policy, f"SURR-{installment:02d}", actor)
            setup = OLSurrenderSetup.objects.filter(
                is_active=True,
                product__isnull=True,
                plan__isnull=True,
            ).order_by("minimum_policy_months", "code").first()
            if setup is None:
                setup = OLSurrenderSetup.objects.create(
                    code=f"{SEED_PREFIX}-SURRENDER-SETUP",
                    name="Seed standard surrender",
                    effective_from=date.today() - timedelta(days=3650),
                    minimum_premiums_paid=1,
                    minimum_policy_months=1,
                    minimum_premium_paid_ratio=Decimal("100"),
                    surrender_charge_type="PERCENTAGE",
                    surrender_charge_value=Decimal("10"),
                    require_approval=False,
                    is_active=True,
                )
            surrender, _ = request_policy_surrender(policy.pk, actor=actor, as_of=date.today(), source_channel="API")
            requisition = surrender.payment_requisition
            surrender.status = SurrenderStatus.PAID
            surrender.save(update_fields=["status", "updated_at"])
            requisition.status = "PAID"
            requisition.save(update_fields=["status", "updated_at"])
            before = {"status": PolicyStatus.SURRENDER_PENDING}
            policy.status = PolicyStatus.SURRENDERED
            policy.contract_snapshot = {
                **policy.contract_snapshot,
                "surrender_payout": {
                    "request_number": surrender.request_number,
                    "net_value": str(surrender.net_surrender_value),
                    "paid_at": date.today().isoformat(),
                },
            }
            policy.save(update_fields=["status", "contract_snapshot"])
            self._audit_seed(policy, "PolicySurrenderPaid", actor, from_status=before["status"], reason="Seed payout requisition settled.")
        return Policy.objects.get(pk=policy.pk)

    def _matured_policy(self, actor):
        partner = self._partner(f"{SEED_PREFIX}-P-MAT", "Farida Matured")
        policy = self._issued_policy("MAT", partner, actor, policy_number=f"{SEED_PREFIX}-MATURED-001")
        if policy.status == PolicyStatus.ACTIVE:
            policy.maturity_date = date.today() - timedelta(days=1)
            policy.contract_snapshot = {**policy.contract_snapshot, "maturity_value": "50000000.00"}
            policy.save(update_fields=["maturity_date", "contract_snapshot"])
            claim, _ = create_maturity_claim(policy, as_of=date.today(), actor=actor, source_channel="BATCH")
            if claim.status != "APPROVED":
                from apps.ol_policies.services.maturity_service import approve_maturity_claim

                claim = approve_maturity_claim(claim.pk, documents_verified=True, actor=actor)
            pay_maturity_claim(claim.pk, payment_reference=f"{SEED_PREFIX}-MAT-PAY", actor=actor)
        return Policy.objects.get(pk=policy.pk)

    def _loan_policy(self, actor):
        partner = self._partner(f"{SEED_PREFIX}-P-LOAN", "Ghani Loan")
        policy = self._issued_policy("LOAN", partner, actor, policy_number=f"{SEED_PREFIX}-LOAN-001")
        if not policy.loans.filter(status="DISBURSED").exists():
            plan_type, _ = OLPlanType.objects.get_or_create(code=f"{SEED_PREFIX}-LOAN-PLAN", defaults={"name": "Seed loan plan", "is_active": True})
            product, _ = OLProduct.objects.get_or_create(
                code=f"{SEED_PREFIX}-LOAN-PRODUCT",
                defaults={
                    "name": "Seed loan product",
                    "plan_type": plan_type,
                    "effective_from": date.today() - timedelta(days=3650),
                    "premium_frequencies": ["ANNUALLY"],
                    "allow_loans": True,
                    "is_active": True,
                },
            )
            policy.contract_snapshot = {
                **policy.contract_snapshot,
                "cash_value": "1000000.00",
                "allow_loans": True,
                "plans": [{"product_id": str(product.pk), "product_code": product.code}],
            }
            policy.save(update_fields=["contract_snapshot"])
            OLLoanSystemSetup.objects.get_or_create(
                code=f"{SEED_PREFIX}-LOAN-SETUP",
                defaults={
                    "name": "Seed loan setup",
                    "product": product,
                    "effective_from": date.today() - timedelta(days=3650),
                    "allow_policy_loans": True,
                    "loan_basis": "CASH_VALUE",
                    "max_loan_percentage_of_cash_value": Decimal("50"),
                    "min_loan_amount": Decimal("10000"),
                    "max_loan_amount": Decimal("400000"),
                    "loan_currency": "TZS",
                    "repayment_options": ["LUMP_SUM"],
                    "require_approval": True,
                    "is_active": True,
                },
            )
            OLLoanInterestControl.objects.get_or_create(
                code=f"{SEED_PREFIX}-LOAN-INTEREST",
                defaults={
                    "name": "Seed loan interest",
                    "product": product,
                    "effective_from": date.today() - timedelta(days=3650),
                    "interest_rate": Decimal("10"),
                    "compounding_frequency": "ANNUAL",
                    "interest_calculation_basis": "ACTUAL_365",
                    "grace_period_days": 0,
                    "penalty_interest_rate": Decimal("0"),
                    "capitalize_interest": True,
                    "is_active": True,
                },
            )
            loan = request_policy_loan(policy.pk, amount=Decimal("100000"), reason="Seed active loan", actor=actor, as_of=date.today())
            approve_policy_loan(loan.pk, actor=actor, as_of=date.today())
            disburse_policy_loan(loan.pk, actor=actor, as_of=date.today())
        return Policy.objects.get(pk=policy.pk)

    def _cancelled_policy(self, actor):
        partner = self._partner(f"{SEED_PREFIX}-P-CANCEL", "Hassan Cancelled")
        policy = self._issued_policy("CANCEL", partner, actor, policy_number=f"{SEED_PREFIX}-CANCELLED-001", commencement_days=1)
        if policy.status == PolicyStatus.ACTIVE:
            policy.contract_snapshot = {**policy.contract_snapshot, "free_look_days": 30}
            policy.save(update_fields=["contract_snapshot"])
            self._policy_commitment(policy, "CANCEL", actor)
            cancel_policy(policy.pk, reason="Customer exercised free-look cancellation.", as_of=date.today(), actor=actor, source_channel="API")
        return Policy.objects.get(pk=policy.pk)

    def _paid_up_policy(self, actor):
        partner = self._partner(f"{SEED_PREFIX}-P-PAIDUP", "Imani Paid Up")
        policy = self._issued_policy(
            "PAIDUP",
            partner,
            actor,
            policy_number=f"{SEED_PREFIX}-PAID-UP-001",
            commencement_days=800,
        )
        if policy.status == PolicyStatus.ACTIVE:
            plan_type, _ = OLPlanType.objects.get_or_create(code=f"{SEED_PREFIX}-PAIDUP-PLAN", defaults={"name": "Seed paid-up plan", "is_active": True})
            legacy_product, _ = LegacyProduct.objects.get_or_create(
                code=f"{SEED_PREFIX}-PAIDUP-PRODUCT",
                defaults={"name": "Seed paid-up product", "is_active": True},
            )
            policy.contract_snapshot = {
                **policy.contract_snapshot,
                "plans": [{"product_id": str(legacy_product.pk), "product_code": legacy_product.code}],
            }
            policy.status = PolicyStatus.LAPSED
            policy.lapsed_at = date.today() - timedelta(days=5)
            policy.save(update_fields=["contract_snapshot", "status", "lapsed_at"])
            for installment in range(1, 25):
                self._policy_commitment(policy, f"PAIDUP-{installment:02d}", actor)
            OLPaidUpSetup.objects.get_or_create(
                code=f"{SEED_PREFIX}-PAIDUP-SETUP",
                defaults={
                    "name": "Seed paid-up setup",
                    "product": legacy_product,
                    "effective_from": date.today() - timedelta(days=3650),
                    "minimum_premiums_paid": 1,
                    "minimum_policy_months": 1,
                    "allow_paidup": True,
                    "is_active": True,
                },
            )
            OLPaidUpRate.objects.get_or_create(
                code=f"{SEED_PREFIX}-PAIDUP-RATE",
                defaults={
                    "name": "Seed paid-up rate",
                    "effective_from": date.today() - timedelta(days=3650),
                    "product": legacy_product,
                    "table_code": "SEED-PAIDUP",
                    "policy_year_from": 1,
                    "policy_year_to": 20,
                    "rate_factor": Decimal("0.60"),
                    "is_active": True,
                },
            )
            convert_policy_to_paid_up(policy.pk, as_of=date.today(), actor=actor, source_channel="API")
        return Policy.objects.get(pk=policy.pk)

    def _seed_parameters(self):
        OLGracePeriod.objects.get_or_create(
            code=f"{SEED_PREFIX}-GRACE",
            defaults={
                "name": "Seed annual grace",
                "effective_from": date.today() - timedelta(days=3650),
                "premium_frequency": "ANNUALLY",
                "grace_days": 5,
                "warning_days": 7,
                "pre_lapse_days": 8,
                "lapse_days": 10,
                "is_active": True,
            },
        )
        OLMaturityClaimSetup.objects.get_or_create(
            code=f"{SEED_PREFIX}-MATURITY-SETUP",
            defaults={
                "name": "Seed maturity setup",
                "effective_from": date.today() - timedelta(days=3650),
                "auto_create_maturity_claim": True,
                "days_before_maturity_to_initiate": 0,
                "default_payout_method": "BANK_TRANSFER",
                "require_documents": False,
                "require_approval": False,
                "maturity_claim_status_to_create": "REPORTED",
                "is_active": True,
            },
        )
        reinstatement_code = f"{SEED_PREFIX}-REINSTATEMENT"
        if not OLReinstatementWindow.objects.filter(code=reinstatement_code).exists() and not OLReinstatementWindow.objects.filter(is_active=True).exists():
            OLReinstatementWindow.objects.create(
                code=reinstatement_code,
                name="Seed 30-day reinstatement window",
                effective_from=date.today() - timedelta(days=3650),
                days_after_lapse=30,
                require_medical_underwriting=False,
                require_outstanding_premium_payment=True,
                interest_rate=Decimal("0"),
                penalty_rate=Decimal("0"),
                is_active=True,
            )

    def _failure_proofs(self, actor):
        failures = {}
        failures["issue_without_first_premium"] = self._capture_failure(
            "POLICY_FIRST_PREMIUM_NOT_POSTED", lambda: self._issue_without_premium(actor)
        )
        failures["reinstate_outside_window"] = self._capture_failure(
            "POLICY_LAPSED", lambda: self._reinstate_outside_window(actor)
        )
        failures["surrender_within_first_year"] = self._capture_failure(
            "POLICY_SURRENDER_BLOCKED", lambda: self._surrender_within_first_year(actor)
        )
        return failures

    def _capture_failure(self, expected_code, operation):
        try:
            with transaction.atomic():
                operation()
        except PolicyError as exc:
            return {"expected": expected_code, "error_code": exc.error_code, "message": str(exc)}
        raise RuntimeError(f"Failure proof did not fail with PolicyError {expected_code}.")

    def _issue_without_premium(self, actor):
        partner = self._partner(f"{SEED_PREFIX}-P-FAIL-ISSUE", "Failure Issuance")
        _, proposal = self._quotation_and_proposal("FAIL-ISSUE", partner, status="AWAITING_FIRST_PREMIUM")
        proposal.first_premium_commitment = None
        proposal.save(update_fields=["first_premium_commitment"])
        issue_policy_from_proposal(proposal.pk, actor=actor, source_channel="SEED")

    def _reinstate_outside_window(self, actor):
        partner = self._partner(f"{SEED_PREFIX}-P-FAIL-REIN", "Failure Reinstatement")
        policy = self._issued_policy("FAIL-REIN", partner, actor, policy_number=f"{SEED_PREFIX}-FAIL-REIN-001")
        policy.status = PolicyStatus.LAPSED
        policy.lapsed_at = date.today() - timedelta(days=3650)
        policy.save(update_fields=["status", "lapsed_at"])
        reinstate_policy(policy.pk, payment_amount=Decimal("999999"), as_of=date.today(), actor=actor, source_channel="SEED")

    def _surrender_within_first_year(self, actor):
        partner = self._partner(f"{SEED_PREFIX}-P-FAIL-SURR", "Failure Surrender")
        policy = self._issued_policy("FAIL-SURR", partner, actor, policy_number=f"{SEED_PREFIX}-FAIL-SURR-001", commencement_days=30)
        setup = OLSurrenderSetup.objects.filter(
            is_active=True,
            product__isnull=True,
            plan__isnull=True,
        ).order_by("minimum_policy_months", "code").first()
        if setup is None:
            setup = OLSurrenderSetup.objects.create(
                code=f"{SEED_PREFIX}-FAIL-SURRENDER-SETUP",
                name="Seed first-year surrender block",
                effective_from=date.today() - timedelta(days=3650),
                minimum_premiums_paid=1,
                minimum_policy_months=12,
                minimum_premium_paid_ratio=Decimal("100"),
                is_active=True,
            )
        request_policy_surrender(policy.pk, actor=actor, as_of=date.today(), source_channel="SEED")
