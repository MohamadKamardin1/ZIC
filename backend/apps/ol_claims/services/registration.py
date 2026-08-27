import hashlib
import json
from datetime import date

from django.db import IntegrityError, transaction

from apps.governance.services.audit_service import AuditService
from apps.ol_policies.models import Policy, PolicyMember

from ..errors import registry_error
from ..events import emit_claim_registered
from ..models import ClaimantType, OLClaim, OLClaimItem, OLClaimant
from .validation import _active_claim_type, calculate_max_claimable, validate_eligibility


class ClaimRegistrationService:
    """Create claims through one validated and retry-safe transaction."""

    @staticmethod
    def _fingerprint(*, policy_id, claim_type, claim_date, cause_of_claim, description, member_id, claimant_details, benefit_type):
        payload = {
            "policy_id": str(policy_id),
            "claim_type": str(claim_type).strip().upper(),
            "claim_date": claim_date.isoformat() if isinstance(claim_date, date) else str(claim_date),
            "cause_of_claim": str(cause_of_claim or "").strip(),
            "description": str(description or "").strip(),
            "member_id": str(member_id or ""),
            "claimant_details": claimant_details or {},
            "benefit_type": str(benefit_type or "").strip().upper(),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        return {"sha256": hashlib.sha256(encoded).hexdigest(), "payload": payload}

    @classmethod
    @transaction.atomic
    def register(
        cls,
        *,
        policy_id,
        claim_type,
        claim_date,
        cause_of_claim="",
        description="",
        member_id=None,
        claimant_details=None,
        benefit_type="",
        idempotency_key=None,
        actor=None,
        source_channel="API",
        request=None,
    ):
        key = str(idempotency_key or "").strip()
        if not key:
            raise registry_error("CLAIM_IDEMPOTENCY_REQUIRED")
        if len(key) > 64:
            raise registry_error(
                "CLAIM_IDEMPOTENCY_REQUIRED",
                message="The idempotency key is too long for claim registration.",
                field_errors={"X-Idempotency-Key": ["Use at most 64 characters."]},
                resolution_steps=[
                    "Send a unique X-Idempotency-Key containing no more than 64 characters.",
                    "Reuse that same key only for the same unchanged submission.",
                ],
            )

        policy = Policy.objects.select_for_update().select_related("partner").filter(pk=policy_id).first()
        if not policy:
            raise registry_error("CLAIM_POLICY_NOT_FOUND", details={"policy_id": str(policy_id)})

        details = claimant_details if isinstance(claimant_details, dict) else {}
        fingerprint = cls._fingerprint(
            policy_id=policy.pk,
            claim_type=claim_type,
            claim_date=claim_date,
            cause_of_claim=cause_of_claim,
            description=description,
            member_id=member_id,
            claimant_details=details,
            benefit_type=benefit_type,
        )
        existing = OLClaim.objects.filter(idempotency_key=key).first()
        if existing:
            if existing.idempotency_fingerprint.get("sha256") != fingerprint["sha256"]:
                raise registry_error("CLAIM_IDEMPOTENCY_CONFLICT", details={"claim_number": existing.claim_number})
            return existing, False

        member = None
        if member_id:
            member = PolicyMember.objects.filter(pk=member_id, policy=policy, is_active=True).first()
            if not member:
                raise registry_error(
                    "CLAIM_CLAIMANT_REQUIRED",
                    field_errors={"member_id": ["Select an active member from the selected policy."]},
                )
        elif not details.get("name") or not details.get("claimant_type"):
            raise registry_error(
                "CLAIM_CLAIMANT_REQUIRED",
                field_errors={
                    "claimant_details.name": ["Enter the claimant's full name."],
                    "claimant_details.claimant_type": ["Select Policyholder, Insured, or Dependent."],
                },
            )

        config = _active_claim_type(claim_type, claim_date)
        validate_eligibility(
            policy,
            member,
            config.code,
            claim_date,
            actor=actor,
            source_channel=source_channel,
        )
        computed_benefit_type = str(benefit_type or config.code).strip().upper()
        calculated_amount = calculate_max_claimable(policy, computed_benefit_type, claim_type=config.code)

        claim = OLClaim(
            policy_ref=policy,
            claim_type=config.code,
            claim_date=claim_date,
            cause_of_claim=str(cause_of_claim or "").strip(),
            description=str(description or "").strip(),
            registered_by=actor,
            created_by=actor,
            source_channel=source_channel,
            idempotency_key=key,
            idempotency_fingerprint=fingerprint,
        )
        claim.full_clean()
        try:
            claim.save(force_insert=True)
        except IntegrityError:
            existing = OLClaim.objects.filter(idempotency_key=key).first()
            if existing and existing.idempotency_fingerprint.get("sha256") == fingerprint["sha256"]:
                return existing, False
            raise

        if member:
            claimant_defaults = {
                "claimant_type": ClaimantType.INSURED,
                "relationship": member.member_relation,
                "name": member.name,
                "age": None,
                "gender": member.gender,
                "identity_number": "",
            }
        else:
            claimant_defaults = {
                "claimant_type": str(details.get("claimant_type", "")).strip().upper(),
                "relationship": str(details.get("relationship", "")).strip(),
                "name": str(details.get("name", "")).strip(),
                "identity_number": str(details.get("identity_number", "")).strip(),
                "age": details.get("age"),
                "gender": str(details.get("gender", "")).strip().upper(),
            }
        if claimant_defaults["claimant_type"] not in dict(ClaimantType.choices):
            raise registry_error(
                "CLAIM_CLAIMANT_REQUIRED",
                field_errors={"claimant_details.claimant_type": ["Choose a supported claimant type."]},
            )
        claimant = OLClaimant.objects.create(claim=claim, created_by=actor, **claimant_defaults)
        claim.claimant_ref = claimant
        claim.save(update_fields=["claimant_ref", "updated_at"])

        OLClaimItem.objects.create(
            claim=claim,
            benefit_type=computed_benefit_type,
            sum_assured=policy.sum_assured,
            calculated_amount=calculated_amount,
            created_by=actor,
        )

        waiver_requested = config.allow_waiver_of_premium and config.claim_category in {"DISABILITY", "CRITICAL_ILLNESS"}
        emit_claim_registered(
            claim,
            actor=actor,
            reason="Claim registered after parameter validation.",
            source_channel=source_channel,
            metadata={
                "claim_type": config.code,
                "claim_category": config.claim_category,
                "calculated_amount": str(calculated_amount),
                "waiver_of_premium_integration_requested": waiver_requested,
            },
        )
        AuditService.log_create(
            claim,
            actor=actor,
            request=request,
            reason="Claim registered through the validated OL Claims service.",
            source_channel=source_channel,
        )
        return claim, True
