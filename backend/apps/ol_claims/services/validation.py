from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.utils import timezone

from apps.governance.services.audit_service import AuditService
from apps.ol_parameters.models import OLClaimReason, OLClaimType, OLGracePeriod
from apps.ol_policies.models import Policy, PolicyMember

from ..errors import registry_error
from ..models import ClaimStatus, OLClaim


MONEY_QUANTUM = Decimal("0.01")


def _effective_queryset(queryset, on_date=None):
    on_date = on_date or timezone.localdate()
    return queryset.filter(is_active=True).filter(
        Q(effective_from__isnull=True) | Q(effective_from__lte=on_date),
        Q(effective_to__isnull=True) | Q(effective_to__gte=on_date),
    )


def _audit_check(*, policy, check, passed, actor=None, source_channel="API", details=None):
    result = "passed" if passed else "failed"
    description = f"OL claim eligibility check {check} {result} for {policy.policy_number}."
    AuditService.log(
        action_type="VALIDATE",
        entity_type="ol_claims.claim_validation",
        entity_id=policy.pk,
        entity_repr=policy.policy_number,
        before_state={},
        after_state={
            "check": check,
            "passed": passed,
            "policy_number": policy.policy_number,
            "details": details or {},
        },
        description=description,
        actor=actor,
        reason=description,
        source_channel=source_channel,
        app_label="ol_claims",
        model_name="claim_validation",
        object_id=str(policy.pk),
        object_repr=policy.policy_number,
    )


def _active_claim_type(claim_type, on_date=None):
    code = getattr(claim_type, "code", claim_type)
    code = str(code or "").strip().upper()
    config = _effective_queryset(OLClaimType.objects).filter(code__iexact=code).first()
    if not config:
        raise registry_error(
            "CLAIM_TYPE_NOT_CONFIGURED",
            details={"claim_type": code},
        )
    return config


def _candidate_grace_periods(policy, on_date):
    try:
        from apps.ordinary_life.models import OLPlan
        from apps.ol_parameters.models import OLProduct

        product = OLProduct.objects.filter(code=policy.product_plan_ref).first()
        plan = OLPlan.objects.filter(code=policy.product_plan_ref).first()
    except (ImportError, AttributeError):  # pragma: no cover - defensive across legacy installs
        product = None
        plan = None

    candidates = list(
        _effective_queryset(OLGracePeriod.objects.select_related("product", "plan"), on_date)
    )
    scored = []
    for config in candidates:
        score = 0
        if config.product_id:
            if not product or config.product_id != product.pk:
                continue
            score += 4
        if config.plan_id:
            if not plan or config.plan_id != plan.pk:
                continue
            score += 4
        frequency = (config.premium_frequency or "").strip().upper()
        if frequency:
            if frequency != (policy.premium_frequency or "").strip().upper():
                continue
            score += 2
        scored.append((score, config))
    return [config for _score, config in sorted(scored, key=lambda item: item[0], reverse=True)]


def _policy_product_codes(policy):
    code = (policy.product_plan_ref or "").strip().upper()
    snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
    values = {code}
    for key in ("product_code", "plan_code", "product", "plan"):
        value = snapshot.get(key)
        if value:
            values.add(str(value).strip().upper())
    return values


def _check_product_compatibility(policy, claim_type_config, *, actor=None, source_channel="API"):
    rules = claim_type_config.payable_to_rules if isinstance(claim_type_config.payable_to_rules, dict) else {}
    policy_codes = _policy_product_codes(policy)
    allowed_codes = rules.get("allowed_product_codes") or rules.get("product_codes") or []
    if isinstance(allowed_codes, str):
        allowed_codes = [allowed_codes]
    allowed_codes = {str(value).strip().upper() for value in allowed_codes if str(value).strip()}
    if allowed_codes and not policy_codes.intersection(allowed_codes):
        _audit_check(
            policy=policy,
            check="product_compatibility",
            passed=False,
            actor=actor,
            source_channel=source_channel,
            details={"claim_type": claim_type_config.code, "allowed_product_codes": sorted(allowed_codes)},
        )
        raise registry_error(
            "CLAIM_BENEFIT_NOT_COVERED",
            details={"claim_type": claim_type_config.code, "policy_product": policy.product_plan_ref},
        )

    required_benefits = rules.get("required_benefit_types") or rules.get("required_benefits") or []
    if isinstance(required_benefits, str):
        required_benefits = [required_benefits]
    required_benefits = {str(value).strip().upper() for value in required_benefits if str(value).strip()}
    if required_benefits:
        policy_benefits = {
            str(value).strip().upper()
            for value in policy.benefits.values_list("benefit_type", flat=True)
        }
        policy_benefits.update(
            str(value).strip().upper()
            for value in policy.riders.values_list("rider_code", flat=True)
        )
        if not required_benefits.intersection(policy_benefits):
            _audit_check(
                policy=policy,
                check="benefit_compatibility",
                passed=False,
                actor=actor,
                source_channel=source_channel,
                details={"required_benefits": sorted(required_benefits)},
            )
            raise registry_error(
                "CLAIM_BENEFIT_NOT_COVERED",
                details={"claim_type": claim_type_config.code, "required_benefits": sorted(required_benefits)},
            )

    _audit_check(
        policy=policy,
        check="product_compatibility",
        passed=True,
        actor=actor,
        source_channel=source_channel,
        details={"claim_type": claim_type_config.code},
    )
    return True


def _member_name(member):
    return str(getattr(member, "name", member) or "").strip().casefold()


def _check_duplicate(policy, member, claim_type_config, claim_date, *, actor=None, source_channel="API"):
    rule = (claim_type_config.duplicate_check_rule or "NONE").strip().upper()
    if rule == "NONE":
        _audit_check(policy=policy, check="duplicate", passed=True, actor=actor, source_channel=source_channel, details={"rule": rule})
        return False

    claims = OLClaim.objects.filter(policy_ref=policy, status=ClaimStatus.SETTLED, claim_type=claim_type_config.code)
    if member is not None:
        claimant_name = _member_name(member)
        if claimant_name:
            claims = claims.filter(
                Q(claimant_ref__name__iexact=claimant_name)
                | Q(claimants__name__iexact=claimant_name)
            )
    if rule == "POLICY_AND_REASON":
        reason = str(getattr(member, "claim_reason", "") or "").strip()
        if reason:
            claims = claims.filter(cause_of_claim__iexact=reason)
    elif rule == "POLICY_AND_EVENT_DATE":
        claims = claims.filter(claim_date=claim_date)

    duplicate = claims.exists()
    _audit_check(
        policy=policy,
        check="duplicate",
        passed=not duplicate,
        actor=actor,
        source_channel=source_channel,
        details={"rule": rule, "claim_type": claim_type_config.code},
    )
    if duplicate:
        raise registry_error(
            "CLAIM_DUPLICATE",
            details={"claim_type": claim_type_config.code, "duplicate_rule": rule},
        )
    return False


def validate_eligibility(policy, member, claim_type, claim_date, *, actor=None, source_channel="API"):
    """Validate registration eligibility using current OL Claim Setup parameters."""
    if not isinstance(policy, Policy):
        policy = Policy.objects.select_related("partner").get(pk=policy)
    if not isinstance(claim_date, date):
        raise registry_error(
            "CLAIM_INVALID_DATE",
            field_errors={"claim_date": ["Enter a valid claim date."]},
        )
    config = _active_claim_type(claim_type, claim_date)

    policy_status = (policy.status or "").strip().upper()
    status_allowed = policy_status in {"ACTIVE", "PAID_UP"}
    if policy_status == "LAPSED":
        grace_period = next(iter(_candidate_grace_periods(policy, claim_date)), None)
        days_lapsed = (claim_date - policy.lapsed_at).days if policy.lapsed_at else None
        status_allowed = bool(grace_period and days_lapsed is not None and 0 <= days_lapsed <= grace_period.grace_days)
        status_details = {
            "status": policy_status,
            "grace_days": grace_period.grace_days if grace_period else None,
            "days_lapsed": days_lapsed,
        }
    else:
        grace_period = None
        status_details = {"status": policy_status}
    _audit_check(policy=policy, check="policy_status", passed=status_allowed, actor=actor, source_channel=source_channel, details=status_details)
    if not status_allowed:
        raise registry_error("CLAIM_POLICY_INACTIVE", details=status_details)

    start_date = policy.risk_commencement_date
    waiting_days = config.waiting_period_days or 0
    waiting_end = start_date + timedelta(days=waiting_days)
    waiting_passed = claim_date >= waiting_end
    _audit_check(
        policy=policy,
        check="waiting_period",
        passed=waiting_passed,
        actor=actor,
        source_channel=source_channel,
        details={"claim_type": config.code, "waiting_period_days": waiting_days, "eligible_from": waiting_end.isoformat()},
    )
    if not waiting_passed:
        raise registry_error(
            "CLAIM_WAITING_PERIOD_ACTIVE",
            details={"claim_type": config.code, "eligible_from": waiting_end.isoformat(), "waiting_period_days": waiting_days},
        )

    _check_product_compatibility(policy, config, actor=actor, source_channel=source_channel)
    _check_duplicate(policy, member, config, claim_date, actor=actor, source_channel=source_channel)
    return {
        "eligible": True,
        "claim_type": config.code,
        "claim_type_display": config.name,
        "claim_category": config.claim_category,
        "calculation_basis": config.calculation_basis,
        "waiting_period_days": waiting_days,
        "require_documents": list(config.require_documents or []),
        "require_approval": config.require_approval,
        "allow_waiver_of_premium": config.allow_waiver_of_premium,
        "grace_period_days": grace_period.grace_days if grace_period else 0,
    }


def _decimal(value, *, field_name):
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise registry_error(
            "CLAIM_BENEFIT_NOT_COVERED",
            message=f"The configured value for {field_name} is not a valid amount.",
            details={"field": field_name},
        ) from exc


def calculate_max_claimable(policy, benefit_type, *, claim_type=None):
    """Calculate the theoretical maximum from the configured claim basis."""
    if not isinstance(policy, Policy):
        policy = Policy.objects.get(pk=policy)
    config = _active_claim_type(claim_type or benefit_type)
    rules = config.payable_to_rules if isinstance(config.payable_to_rules, dict) else {}
    basis = (config.calculation_basis or "").strip().upper()

    if basis == "SUM_ASSURED":
        amount = _decimal(policy.sum_assured, field_name="sum_assured")
    elif basis == "CASH_VALUE":
        snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
        amount = _decimal(
            snapshot.get("cash_value", snapshot.get("current_cash_value", 0)),
            field_name="cash_value",
        )
    elif basis == "BENEFIT_AMOUNT":
        requested = str(benefit_type or "").strip().upper()
        benefit = policy.benefits.filter(benefit_type__iexact=requested).first()
        if benefit is None:
            benefit = policy.benefits.first()
        if benefit is None:
            raise registry_error(
                "CLAIM_BENEFIT_NOT_COVERED",
                details={"benefit_type": requested, "claim_type": config.code},
            )
        amount = _decimal(benefit.amount, field_name="benefit_amount")
    elif basis == "FIXED_AMOUNT":
        amount = _decimal(rules.get("fixed_amount", rules.get("amount", 0)), field_name="fixed_amount")
    elif basis == "PERCENTAGE":
        percentage = _decimal(rules.get("percentage", rules.get("ratio", 100)), field_name="percentage")
        amount = _decimal(policy.sum_assured, field_name="sum_assured") * percentage / Decimal("100")
    else:
        amount = _decimal(rules.get("max_amount", rules.get("maximum_amount", 0)), field_name="max_amount")

    configured_cap = rules.get("maximum_amount", rules.get("max_amount"))
    if configured_cap not in (None, ""):
        amount = min(amount, _decimal(configured_cap, field_name="maximum_amount"))
    if amount < 0:
        amount = Decimal("0")
    return amount.quantize(MONEY_QUANTUM)
