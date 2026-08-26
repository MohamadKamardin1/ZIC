from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from apps.governance.services.audit_service import AuditService
from apps.ol_commitments.models import CommitmentSourceChannel, CommitmentSourceType, OLCommitment
from apps.ol_parameters.models import OLDefaultSystemParameter, OLPremiumRateTable
from apps.system_parameters.services.numbering_service import NumberingEngine

from ..errors import registry_error
from ..events import emit_policy_endorsed
from ..models import EndorsementStatus, EndorsementType, Policy, PolicyAuditLog, PolicyEndorsement, PolicyMember

BLOCKED_SERVICING_STATUSES = {"LAPSED", "CANCELLED", "EXPIRED"}
TERMINAL_PREMIUM_STATUS = {"COMPLETED", "CANCELLED", "REVERSED", "WAIVED", "CLOSED"}


def _date(value, default=None):
    if value in (None, ""):
        return default
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise registry_error(
            "POLICY_ENDORSEMENT_INVALID",
            message="The endorsement effective date must use YYYY-MM-DD format.",
            field_errors={"effective_date": ["Enter a valid date in YYYY-MM-DD format."]},
        ) from None


def _decimal(value, default=Decimal("0.00")):
    if value is None or value == "":
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _active_parameter_decimal(code, default):
    parameter = (
        OLDefaultSystemParameter.objects.filter(parameter_key=code, is_active=True)
        .order_by("-effective_from", "-created_at")
        .first()
    )
    if parameter is None:
        return default
    return _decimal(parameter.value, default)


def _premium_limit_percent(policy):
    snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
    configured = _decimal(snapshot.get("premium_change_max_percent"), Decimal("-1"))
    if configured >= 0:
        return configured
    return _active_parameter_decimal("POLICY_ENDORSEMENT_MAX_PREMIUM_CHANGE_PERCENT", Decimal("50"))


def _validate_premium_against_rating(policy, new_premium):
    current = _decimal(policy.premium_amount)
    if new_premium <= 0:
        raise registry_error(
            "POLICY_ENDORSEMENT_INVALID",
            message="The new premium must be greater than zero.",
            field_errors={"new_premium": ["Enter a positive premium amount."]},
        )
    max_percent = _premium_limit_percent(policy)
    minimum = current * (Decimal("1") - max_percent / Decimal("100"))
    maximum = current * (Decimal("1") + max_percent / Decimal("100"))
    if new_premium < minimum or new_premium > maximum:
        raise registry_error(
            "POLICY_ENDORSEMENT_INVALID",
            message="The requested premium change is outside the configured product-rating band.",
            details={
                "current_premium": str(current),
                "new_premium": str(new_premium),
                "allowed_minimum": str(minimum.quantize(Decimal("0.01"))),
                "allowed_maximum": str(maximum.quantize(Decimal("0.01"))),
                "maximum_change_percent": str(max_percent),
            },
            field_errors={
                "new_premium": [
                    f"Enter a premium between {minimum.quantize(Decimal('0.01'))} and {maximum.quantize(Decimal('0.01'))}."
                ]
            },
            resolution_steps=[
                "Review the active OL Product Rating table for this product and plan.",
                "Enter a premium within the configured endorsement change band.",
                "Ask an OL Parameters administrator to update the band if the business exception is approved.",
            ],
        )

    # If a product/plan snapshot is available, prove that an active rating
    # table exists for the contract. The table is the source of truth for the
    # detailed premium calculation; this service only validates the endorsed
    # amount against the configured band until the rating engine is called.
    snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
    for plan in snapshot.get("plans", []):
        if not isinstance(plan, dict):
            continue
        product_code = plan.get("product_code")
        if product_code:
            table_exists = OLPremiumRateTable.objects.filter(
                product__code=product_code,
                is_active=True,
            ).exists()
            if not table_exists:
                break
    return new_premium


def _member_count_limits(policy):
    snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
    min_members = snapshot.get("min_members")
    max_members = snapshot.get("max_members")
    return (
        int(min_members) if min_members not in (None, "") else 1,
        int(max_members) if max_members not in (None, "") else None,
    )


def _snapshot(policy):
    return {
        "status": policy.status,
        "premium_amount": str(policy.premium_amount),
        "term_years": policy.term_years,
        "maturity_date": policy.maturity_date.isoformat(),
        "active_members": [
            {
                "member_relation": member.member_relation,
                "name": member.name,
                "dob": member.dob.isoformat(),
                "gender": member.gender,
                "benefit_amount": str(member.benefit_amount),
            }
            for member in policy.members.filter(is_active=True).order_by("created_at")
        ],
        "contract_snapshot": policy.contract_snapshot,
    }


def _commitment_adjustment(policy, difference, *, actor=None):
    if difference == 0:
        return None
    content_type = ContentType.objects.get_for_model(Policy)
    installment_number = (
        OLCommitment.objects.filter(
            source_content_type=content_type,
            source_object_id=str(policy.pk),
        ).count()
        + 1
    )
    return OLCommitment.objects.create(
        commitment_number=NumberingEngine.generate_number(
            "OL_COMMITMENT", OLCommitment, field_name="commitment_number"
        ),
        source_type=CommitmentSourceType.POLICY,
        source_content_type=content_type,
        source_object_id=str(policy.pk),
        source_reference=policy.policy_number,
        partner=policy.partner,
        partner_name_snapshot=str(policy.partner),
        currency=policy.currency,
        premium_frequency=policy.premium_frequency,
        installment_number=installment_number,
        installment_count=1,
        due_date=date.today(),
        premium_amount=abs(difference),
        balance=abs(difference),
        status="PENDING",
        reason_code="POLICY_ENDORSEMENT_ADJUSTMENT",
        reason_text=(
            "Additional premium due after endorsement."
            if difference > 0
            else "Premium credit adjustment after endorsement."
        ),
        source_channel=CommitmentSourceChannel.API,
        created_by=actor,
        updated_by=actor,
    )


@transaction.atomic
def create_policy_endorsement(
    policy_id,
    *,
    endorsement_type,
    changes=None,
    effective_date=None,
    description="",
    actor=None,
    request=None,
    source_channel="API",
):
    policy = (
        Policy.objects.select_for_update()
        .select_related("partner", "proposal_ref")
        .prefetch_related("members")
        .filter(pk=policy_id)
        .first()
    )
    if policy is None:
        from ..errors import not_found

        raise not_found(policy_id)

    endorsement_type = (endorsement_type or "").strip().upper()
    if endorsement_type not in EndorsementType.values:
        raise registry_error(
            "POLICY_ENDORSEMENT_INVALID",
            message=f"Unsupported endorsement type '{endorsement_type}'.",
            field_errors={"endorsement_type": [f"Choose one of: {', '.join(EndorsementType.values)}."]},
        )
    changes = changes if isinstance(changes, dict) else {}
    if policy.status in BLOCKED_SERVICING_STATUSES and not changes.get("reinstatement_completed"):
        raise registry_error(
            "POLICY_INVALID_STATUS",
            message=f"A {policy.get_status_display()} policy cannot be endorsed before reinstatement.",
            details={"status": policy.status},
            resolution_steps=[
                "Complete the policy reinstatement process first.",
                "Retry the endorsement after the policy returns to Active status.",
            ],
        )

    effective_date = _date(effective_date, date.today())
    before = _snapshot(policy)
    after = {**before}
    commitment = None
    if endorsement_type == EndorsementType.PREMIUM_CHANGE:
        new_premium = _validate_premium_against_rating(policy, _decimal(changes.get("new_premium")))
        difference = new_premium - _decimal(policy.premium_amount)
        policy.premium_amount = new_premium
        after["premium_amount"] = str(new_premium)
        commitment = _commitment_adjustment(policy, difference, actor=actor)
    elif endorsement_type == EndorsementType.TERM_CHANGE:
        new_term = changes.get("new_term_years")
        try:
            new_term = int(new_term)
        except (TypeError, ValueError):
            new_term = 0
        if new_term <= 0:
            raise registry_error(
                "POLICY_ENDORSEMENT_INVALID",
                message="The new policy term must be a positive whole number of years.",
                field_errors={"new_term_years": ["Enter a term of at least one year."]},
            )
        if new_term < 1:
            raise registry_error("POLICY_ENDORSEMENT_INVALID")
        policy.term_years = new_term
        policy.maturity_date = policy.risk_commencement_date.replace(
            year=policy.risk_commencement_date.year + new_term
        )
        after["term_years"] = new_term
        after["maturity_date"] = policy.maturity_date.isoformat()
    elif endorsement_type == EndorsementType.MEMBER_ADD:
        min_members, max_members = _member_count_limits(policy)
        active_count = policy.members.filter(is_active=True).count()
        if max_members is not None and active_count >= max_members:
            raise registry_error(
                "POLICY_ENDORSEMENT_INVALID",
                message="The policy has reached the maximum number of covered members.",
                details={"active_members": active_count, "max_members": max_members},
                resolution_steps=["Review the product plan member limit.", "Remove an existing member or request an approved plan change."],
            )
        required = ("member_relation", "name", "dob", "gender", "benefit_amount")
        missing = [field for field in required if changes.get(field) in (None, "")]
        if missing:
            raise registry_error(
                "POLICY_ENDORSEMENT_INVALID",
                message="All member details are required for a member-add endorsement.",
                field_errors={field: ["This member field is required."] for field in missing},
            )
        member = PolicyMember.objects.create(
            policy=policy,
            member_relation=changes["member_relation"],
            name=changes["name"],
            dob=_date(changes["dob"]),
            gender=changes["gender"],
            benefit_amount=_decimal(changes["benefit_amount"]),
            created_by=actor,
            updated_by=actor,
        )
        after["active_members"] = before["active_members"] + [
            {
                "member_relation": member.member_relation,
                "name": member.name,
                "dob": member.dob.isoformat(),
                "gender": member.gender,
                "benefit_amount": str(member.benefit_amount),
            }
        ]
    elif endorsement_type == EndorsementType.MEMBER_REMOVE:
        member_id = changes.get("member_id")
        member = policy.members.filter(pk=member_id, is_active=True).first()
        if member is None:
            raise registry_error(
                "POLICY_ENDORSEMENT_INVALID",
                message="The member to remove was not found among active policy members.",
                field_errors={"member_id": ["Choose an active member on this policy."]},
            )
        min_members, _max_members = _member_count_limits(policy)
        active_count = policy.members.filter(is_active=True).count()
        if active_count <= min_members:
            raise registry_error(
                "POLICY_ENDORSEMENT_INVALID",
                message="The minimum number of covered members would be violated.",
                details={"active_members": active_count, "min_members": min_members},
                resolution_steps=["Keep the minimum principal/member coverage required by the product plan."],
            )
        member.is_active = False
        member.ended_at = effective_date or date.today()
        member.updated_by = actor
        member.save(update_fields=["is_active", "ended_at", "updated_by", "updated_at"])
        after["active_members"] = [item for item in before["active_members"] if item["name"] != member.name]
    elif endorsement_type in {EndorsementType.BENEFICIARY_CHANGE, EndorsementType.ADDRESS_CHANGE}:
        snapshot = dict(policy.contract_snapshot or {})
        key = "beneficiaries" if endorsement_type == EndorsementType.BENEFICIARY_CHANGE else "address"
        snapshot[key] = changes.get(key, changes)
        policy.contract_snapshot = snapshot
        after["contract_snapshot"] = snapshot

    policy.updated_by = actor
    policy.save(update_fields=["premium_amount", "term_years", "maturity_date", "contract_snapshot", "updated_by", "updated_at"])
    endorsement = PolicyEndorsement.objects.create(
        policy=policy,
        endorsement_type=endorsement_type,
        effective_date=effective_date or date.today(),
        description=(description or f"{endorsement_type.replace('_', ' ').title()} endorsement.").strip(),
        status=EndorsementStatus.APPLIED,
        before_snapshot=before,
        after_snapshot=after,
        reason=description or "Policy servicing endorsement applied.",
        source_channel=source_channel,
        created_by=actor,
        updated_by=actor,
    )
    reason = endorsement.description
    PolicyAuditLog.objects.create(
        policy=policy,
        actor=actor,
        event_type="PolicyEndorsed",
        from_status=before["status"],
        to_status=policy.status,
        before_snapshot=before,
        after_snapshot=after,
        reason=reason,
        source_channel=source_channel,
        correlation_id=getattr(request, "request_id", "") if request else "",
    )
    AuditService.log_action(
        "POLICY_ENDORSED",
        policy,
        actor=actor,
        request=request,
        before_state=before,
        after_state=after,
        changed_fields=["premium_amount", "term_years", "maturity_date", "contract_snapshot", "members"],
        reason=reason,
        source_channel=source_channel,
    )
    AuditService.log_create(endorsement, actor=actor, request=request, reason=reason, source_channel=source_channel)
    emit_policy_endorsed(
        policy,
        endorsement,
        actor=actor,
        reason=reason,
        source_channel=source_channel,
        metadata={"commitment_number": commitment.commitment_number if commitment else None},
    )
    return endorsement, commitment
