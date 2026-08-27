import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand, call_command
from django.db import transaction

from apps.common.models import DomainEvent
from apps.governance.services.audit_service import AuditService
from apps.ol_parameters.models import OLClaimType
from apps.ol_policies.models import LoanStatus, Policy

from ...errors import ClaimError
from ...events import (
    emit_claim_assessed,
    emit_claim_cancelled,
    emit_claim_medical_required,
    emit_claim_rejected,
    emit_claim_registered,
    emit_claim_settled,
)
from ...models import ClaimMedicalStatus, ClaimStatus, ClaimantType, OLClaim, OLClaimDocument, OLClaimItem, OLClaimant
from ...services.assessment import assess_claim
from ...services.loan_offset import apply_loan_offset
from ...services.validation import validate_eligibility


SEED_PREFIX = "OL-CLAIM-SEED"


class Command(BaseCommand):
    help = "Seed exactly ten realistic, idempotent OL Claims scenarios and prove key failure paths."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", help="Print one machine-readable JSON result.")

    def handle(self, *args, **options):
        actor = self._seed_actor()
        with transaction.atomic():
            if not Policy.objects.filter(policy_number="OL-SEED-ACTIVE-001").exists():
                call_command("seed_ol_policy_scenarios", verbosity=0)
            self._seed_claim_types()
            policies = self._policy_map()
            claims = self._seed_claims(policies, actor)
            self._apply_loan_scenario(claims["08-loan-offset"], policies["loan"], actor)
            proofs = self._failure_proofs(policies, claims, actor)

        result = {
            "command": "seed_ol_claim_scenarios",
            "claim_count": len(claims),
            "seeded_claim_numbers": {key: claim.claim_number for key, claim in claims.items()},
            "states": {key: claim.status for key, claim in claims.items()},
            "loan_offset": self._loan_offset_result(claims["08-loan-offset"]),
            "failure_proofs": proofs,
            "idempotent": True,
        }
        if options["json"]:
            self.stdout.write(json.dumps(result, sort_keys=True, default=str))
            return
        self.stdout.write(self.style.SUCCESS(f"Seeded/reused exactly {len(claims)} OL Claims scenarios."))
        for key, claim in claims.items():
            self.stdout.write(f"  {claim.claim_number}: {claim.status}")
        offset = result["loan_offset"]
        if offset:
            self.stdout.write(f"Loan offset: {offset['offset_amount']} {offset['currency']}; net {offset['net_payout']} {offset['currency']}")
        self.stdout.write("Failure proofs:")
        for key, proof in proofs.items():
            self.stdout.write(f"  {key}: {proof['error_code']} — {proof['message']}")
        self.stdout.write(self.style.SUCCESS("The seed is idempotent; rerunning it reuses the same ten claim numbers."))

    def _seed_actor(self):
        User = get_user_model()
        actor, _ = User.objects.get_or_create(
            username="ol_claim_seed_operator",
            defaults={
                "email": "ol.claim.seed@zic.tz",
                "first_name": "OL Claims",
                "last_name": "Seed Operator",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        changed = []
        if not actor.is_staff:
            actor.is_staff = True
            changed.append("is_staff")
        if not actor.is_superuser:
            actor.is_superuser = True
            changed.append("is_superuser")
        if changed:
            actor.save(update_fields=changed)
        return actor

    def _seed_claim_types(self):
        today = date.today()
        definitions = [
            ("DEATH_CLAIM", "Death Claim", "DEATH", 0, ["DEATH_CERTIFICATE"], False, "POLICY_AND_TYPE"),
            ("CRITICAL_ILLNESS_CLAIM", "Critical Illness Claim", "CRITICAL_ILLNESS", 0, ["MEDICAL_REPORT"], False, "NONE"),
            ("PENDING_MEDICAL_CLAIM", "Pending Medical Claim", "DEATH", 0, ["DEATH_CERTIFICATE", "MEDICAL_REPORT"], False, "NONE"),
            ("WAITING_PERIOD_CLAIM", "Waiting Period Claim", "DEATH", 365, ["DEATH_CERTIFICATE"], False, "NONE"),
            ("WAIVER_OF_PREMIUM_CLAIM", "Waiver of Premium Claim", "DISABILITY", 0, ["MEDICAL_REPORT"], True, "NONE"),
        ]
        for code, name, category, waiting_days, documents, waiver, duplicate_rule in definitions:
            OLClaimType.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "claim_category": category,
                    "calculation_basis": "SUM_ASSURED",
                    "duplicate_check_rule": duplicate_rule,
                    "waiting_period_days": waiting_days,
                    "payable_to_rules": {},
                    "allow_waiver_of_premium": waiver,
                    "require_documents": documents,
                    "require_approval": False,
                    "effective_from": today - timedelta(days=3650),
                    "effective_to": None,
                    "is_active": True,
                },
            )

    def _policy_map(self):
        numbers = {
            "active": f"OL-SEED-ACTIVE-001",
            "loan": f"OL-SEED-LOAN-001",
            "cancelled": f"OL-SEED-CANCELLED-001",
        }
        policies = {key: Policy.objects.filter(policy_number=value).first() for key, value in numbers.items()}
        fallback = Policy.objects.order_by("policy_number").first()
        if fallback is None:
            raise RuntimeError("The OL policy scenario seeder did not create a policy.")
        policies["active"] = policies["active"] or fallback
        policies["loan"] = policies["loan"] or policies["active"]
        policies["cancelled"] = policies["cancelled"] or policies["active"]
        return policies

    def _seed_claims(self, policies, actor):
        scenario_specs = [
            ("01-death-full", "DEATH_CLAIM", policies["active"], ClaimStatus.SETTLED, "Full death benefit settlement", Decimal("50000000.00"), Decimal("50000000.00"), ClaimMedicalStatus.NONE, False, 0, ["DEATH_CERTIFICATE"]),
            ("02-critical-illness-partial", "CRITICAL_ILLNESS_CLAIM", policies["active"], ClaimStatus.SETTLED, "Partial critical illness benefit", Decimal("50000000.00"), Decimal("12500000.00"), ClaimMedicalStatus.CLEARED, False, 0, ["MEDICAL_REPORT"]),
            ("03-pending-medical", "PENDING_MEDICAL_CLAIM", policies["active"], ClaimStatus.PENDING_MEDICAL, "Medical evidence is under review", Decimal("50000000.00"), None, ClaimMedicalStatus.PENDING, False, 0, []),
            ("04-rejected-missing-docs", "DEATH_CLAIM", policies["active"], ClaimStatus.REJECTED, "Mandatory evidence was not supplied", Decimal("50000000.00"), None, ClaimMedicalStatus.NONE, False, 0, []),
            ("05-rejected-waiting-period", "WAITING_PERIOD_CLAIM", policies["active"], ClaimStatus.REJECTED, "Claim event fell inside the configured waiting period", Decimal("50000000.00"), None, ClaimMedicalStatus.NONE, False, 0, []),
            ("06-duplicate-blocked", "DEATH_CLAIM", policies["active"], ClaimStatus.REJECTED, "Duplicate claim blocked by policy and claim type rule", Decimal("50000000.00"), None, ClaimMedicalStatus.NONE, False, 0, []),
            ("07-fraud-flagged", "CRITICAL_ILLNESS_CLAIM", policies["active"], ClaimStatus.ASSESSED, "Claim requires enhanced fraud review", Decimal("50000000.00"), Decimal("10000000.00"), ClaimMedicalStatus.CLEARED, True, 0, ["MEDICAL_REPORT"]),
            ("08-loan-offset", "DEATH_CLAIM", policies["loan"], ClaimStatus.SETTLED, "Death settlement with policy loan offset", Decimal("50000000.00"), Decimal("35000000.00"), ClaimMedicalStatus.NONE, False, 0, ["DEATH_CERTIFICATE"]),
            ("09-waiver-of-premium", "WAIVER_OF_PREMIUM_CLAIM", policies["active"], ClaimStatus.ASSESSED, "Waiver of premium approved for 180 days", Decimal("50000000.00"), Decimal("5000000.00"), ClaimMedicalStatus.CLEARED, False, 180, ["MEDICAL_REPORT"]),
            ("10-cancelled", "DEATH_CLAIM", policies["cancelled"], ClaimStatus.CANCELLED, "Claim cancelled at policyholder request", Decimal("50000000.00"), None, ClaimMedicalStatus.NONE, False, 0, []),
        ]
        claims = {}
        for suffix, claim_type, policy, status, description, sum_assured, approved_amount, medical_status, fraud_flag, waiver_days, documents in scenario_specs:
            claims[suffix] = self._upsert_claim(
                suffix=suffix,
                claim_type=claim_type,
                policy=policy,
                status=status,
                description=description,
                sum_assured=sum_assured,
                approved_amount=approved_amount,
                medical_status=medical_status,
                fraud_flag=fraud_flag,
                waiver_days=waiver_days,
                documents=documents,
                actor=actor,
            )
        return claims

    def _upsert_claim(self, *, suffix, claim_type, policy, status, description, sum_assured, approved_amount, medical_status, fraud_flag, waiver_days, documents, actor):
        claim_number = f"{SEED_PREFIX}-{suffix.upper()}"
        claim, created = OLClaim.objects.get_or_create(
            claim_number=claim_number,
            defaults={
                "policy_ref": policy,
                "claim_type": claim_type,
                "claim_date": date.today() - timedelta(days=30),
                "admitted_date": date.today() - timedelta(days=29),
                "status": status,
                "cause_of_claim": description,
                "description": description,
                "assessment_notes": description,
                "fraud_flag": fraud_flag,
                "fraud_flag_reason": "Enhanced fraud review required by the seed scenario." if fraud_flag else "",
                "waiver_of_premium_days": waiver_days,
                "waiver_of_premium_until": date.today() + timedelta(days=waiver_days) if waiver_days else None,
                "waiver_of_premium_applied": bool(waiver_days),
                "medical_status": medical_status,
                "registered_by": actor,
                "admitted_by": actor,
                "source_channel": "BATCH",
                "idempotency_key": f"{SEED_PREFIX}:{suffix}"[:64],
                "idempotency_fingerprint": {"seed_scenario": suffix},
                "settled_date": date.today() - timedelta(days=1) if status == ClaimStatus.SETTLED else None,
                "settlement_amount": approved_amount if status == ClaimStatus.SETTLED else None,
                "payment_reference": f"{SEED_PREFIX}-PAY-{suffix.upper()}" if status == ClaimStatus.SETTLED else "",
            },
        )
        if created:
            claim.full_clean()
            claim.save()
            AuditService.log_create(
                claim,
                actor=actor,
                reason=f"Seeded OL Claims scenario: {description}.",
                source_channel="BATCH",
            )
        else:
            changed = []
            for field, value in {
                "policy_ref": policy,
                "status": status,
                "description": description,
                "cause_of_claim": description,
                "assessment_notes": description,
                "medical_status": medical_status,
                "fraud_flag": fraud_flag,
                "fraud_flag_reason": "Enhanced fraud review required by the seed scenario." if fraud_flag else "",
                "waiver_of_premium_days": waiver_days,
                "waiver_of_premium_applied": bool(waiver_days),
            }.items():
                if getattr(claim, field) != value:
                    setattr(claim, field, value)
                    changed.append(field)
            if changed:
                changed.append("updated_at")
                claim.save(update_fields=changed)
        claimant, _ = OLClaimant.objects.get_or_create(
            claim=claim,
            claimant_type=ClaimantType.INSURED,
            defaults={
                "relationship": "Principal member",
                "name": getattr(policy.partner, "legal_name", "Seed policyholder"),
                "identity_number": f"NIDA-{suffix.upper()}",
                "age": 38,
                "gender": "FEMALE",
                "created_by": actor,
            },
        )
        if claim.claimant_ref_id != claimant.pk:
            claim.claimant_ref = claimant
            claim.save(update_fields=["claimant_ref", "updated_at"])
        item, _ = OLClaimItem.objects.get_or_create(
            claim=claim,
            benefit_type="DEATH_BENEFIT" if claim_type != "WAIVER_OF_PREMIUM_CLAIM" else "PREMIUM_WAIVER",
            defaults={
                "sum_assured": sum_assured,
                "calculated_amount": sum_assured,
                "approved_amount": approved_amount,
                "created_by": actor,
            },
        )
        if item.approved_amount != approved_amount:
            item.approved_amount = approved_amount
            item.save(update_fields=["approved_amount", "updated_at"])
        for document_type in documents:
            OLClaimDocument.objects.get_or_create(
                claim=claim,
                document_type=document_type,
                defaults={
                    "file_reference": f"seed/claims/{suffix}/{document_type.lower()}.pdf",
                    "mandatory_flag": True,
                    "uploaded_by": actor,
                    "created_by": actor,
                },
            )
        self._emit_once(claim, "ClaimRegistered", emit_claim_registered, actor=actor, reason="Seed scenario registered.")
        if status in {ClaimStatus.ASSESSED, ClaimStatus.SETTLED}:
            self._emit_once(claim, "ClaimAssessed", emit_claim_assessed, actor=actor, reason=description, metadata={"seed_scenario": suffix})
        if status == ClaimStatus.PENDING_MEDICAL:
            self._emit_once(claim, "ClaimMedicalRequired", emit_claim_medical_required, actor=actor, reason=description)
        if status == ClaimStatus.REJECTED:
            self._emit_once(claim, "ClaimRejected", emit_claim_rejected, actor=actor, reason=description)
        if status == ClaimStatus.CANCELLED:
            self._emit_once(claim, "ClaimCancelled", emit_claim_cancelled, actor=actor, reason=description)
        if status == ClaimStatus.SETTLED:
            self._emit_once(claim, "ClaimSettled", emit_claim_settled, actor=actor, reason=description, metadata={"payment_reference": claim.payment_reference})
        return claim

    def _emit_once(self, claim, event_type, emitter, **kwargs):
        if not DomainEvent.objects.filter(event_type=event_type, aggregate_id=str(claim.pk)).exists():
            emitter(claim, source_channel="BATCH", **kwargs)

    def _apply_loan_scenario(self, claim, policy, actor):
        from apps.ol_policies.models import PolicyLoan

        loan, _ = PolicyLoan.objects.get_or_create(
            loan_number=f"{SEED_PREFIX}-LOAN-001",
            defaults={
                "policy": policy,
                "requested_at": date.today() - timedelta(days=120),
                "approved_at": date.today() - timedelta(days=115),
                "disbursed_at": date.today() - timedelta(days=110),
                "last_interest_date": date.today() - timedelta(days=1),
                "principal_amount": Decimal("4000000.00"),
                "outstanding_principal": Decimal("4000000.00"),
                "outstanding_interest": Decimal("250000.00"),
                "interest_rate": Decimal("0.12000000"),
                "currency": policy.currency,
                "status": LoanStatus.DISBURSED,
                "approval_required": False,
                "repayment_options": ["LUMP_SUM"],
                "reason": "Seed claim loan-offset balance.",
                "created_by": actor,
                "updated_by": actor,
            },
        )
        if loan.policy_id != policy.pk:
            loan.policy = policy
            loan.save(update_fields=["policy", "updated_at"])
        if not getattr(claim, "loan_offset", None):
            apply_loan_offset(
                claim.pk,
                actor=actor,
                source_channel="BATCH",
                reason="Seeded loan offset scenario applied at settlement.",
            )

    def _loan_offset_result(self, claim):
        from ...models import OLClaimLoanOffset

        offset = OLClaimLoanOffset.objects.select_related("loan").filter(claim=claim).first()
        if not offset:
            return None
        return {
            "claim_number": claim.claim_number,
            "loan_number": offset.loan.loan_number,
            "offset_amount": str(offset.offset_amount),
            "net_payout": str(offset.net_payout),
            "currency": claim.policy_ref.currency,
            "status": offset.status,
        }

    def _failure_proofs(self, policies, claims, actor):
        proofs = {}
        inactive = policies["active"]
        original_status = inactive.status
        inactive.status = "CANCELLED"
        try:
            proofs["inactive_policy"] = self._capture(
                "CLAIM_POLICY_INACTIVE",
                lambda: validate_eligibility(inactive, None, "DEATH_CLAIM", date.today(), actor=actor, source_channel="BATCH"),
            )
        finally:
            inactive.status = original_status
        proofs["duplicate_claim"] = self._capture(
            "CLAIM_DUPLICATE",
            lambda: validate_eligibility(policies["active"], None, "DEATH_CLAIM", date.today(), actor=actor, source_channel="BATCH"),
        )
        proofs["waiting_period_violation"] = self._capture(
            "CLAIM_WAITING_PERIOD_ACTIVE",
            lambda: validate_eligibility(policies["active"], None, "WAITING_PERIOD_CLAIM", date(2026, 4, 1), actor=actor, source_channel="BATCH"),
        )
        def exceed_limit():
            claim = claims["01-death-full"]
            with transaction.atomic():
                original_status = claim.status
                claim.status = ClaimStatus.ASSESSMENT
                claim.save(update_fields=["status", "updated_at"])
                try:
                    assess_claim(
                        claim.pk,
                        assessed_amount=Decimal("999999999.00"),
                        assessment_notes="Seeded amount-limit failure proof.",
                        actor=actor,
                        source_channel="BATCH",
                    )
                finally:
                    claim.status = original_status
                    claim.save(update_fields=["status", "updated_at"])
        proofs["amount_exceeds_limit"] = self._capture("CLAIM_ASSESSMENT_AMOUNT_INVALID", exceed_limit)
        return proofs

    def _capture(self, expected_code, operation):
        try:
            operation()
        except ClaimError as exc:
            if exc.error_code != expected_code:
                raise RuntimeError(f"Expected {expected_code}, received {exc.error_code}.")
            return {"passed": True, "expected": expected_code, "error_code": exc.error_code, "message": str(exc)}
        raise RuntimeError(f"Failure proof did not fail with ClaimError {expected_code}.")
