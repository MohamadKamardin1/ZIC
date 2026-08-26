from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.db import transaction
from django.db.models import Q

from apps.front_office.models import FORequisition
from apps.governance.services.audit_service import AuditService
from apps.ol_parameters.models import OLMaturityClaimSetup
from apps.system_parameters.services.numbering_service import NumberingEngine

from ..errors import registry_error
from ..events import (
    POLICY_MATURITY_CLAIM_APPROVED,
    POLICY_MATURITY_CLAIM_CREATED,
    POLICY_MATURITY_PAID,
    emit_policy_loan_event,
)
from ..models import LoanStatus, MaturityClaim, MaturityClaimStatus, Policy, PolicyAuditLog, PolicyStatus

ACTIVE_LOAN_STATUSES = [LoanStatus.DISBURSED, LoanStatus.PARTIALLY_REPAID]


def _date(value, default=None):
    if value in (None, ""):
        return default or date.today()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise registry_error(
            "POLICY_NOT_MATURED",
            message="The maturity processing date must use YYYY-MM-DD format.",
            field_errors={"as_of": ["Enter a valid date in YYYY-MM-DD format."]},
        ) from None


def _decimal(value, default=Decimal("0.00")):
    if value in (None, ""):
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _scope(policy):
    snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
    plan = next((row for row in snapshot.get("plans", []) if isinstance(row, dict)), {})
    return plan.get("product_id"), plan.get("plan_id"), plan.get("product_code"), plan.get("plan_code")


def _setup(policy, as_of):
    product_id, plan_id, product_code, plan_code = _scope(policy)
    queryset = OLMaturityClaimSetup.objects.filter(is_active=True)
    if product_id:
        queryset = queryset.filter(Q(product_id=product_id) | Q(product__isnull=True))
    elif product_code:
        queryset = queryset.filter(Q(product__code=product_code) | Q(product__isnull=True))
    if plan_id:
        queryset = queryset.filter(Q(plan_id=plan_id) | Q(plan__isnull=True))
    elif plan_code:
        queryset = queryset.filter(Q(plan__code=plan_code) | Q(plan__isnull=True))
    return queryset.filter(
        Q(effective_from__isnull=True) | Q(effective_from__lte=as_of),
        Q(effective_to__isnull=True) | Q(effective_to__gte=as_of),
    ).order_by("-effective_from", "code").first()


def _loan_deduction(policy):
    return sum(
        (
            _decimal(loan.outstanding_principal) + _decimal(loan.outstanding_interest)
            for loan in policy.loans.filter(status__in=ACTIVE_LOAN_STATUSES)
        ),
        Decimal("0.00"),
    )


def _maturity_value(policy):
    snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
    return _decimal(
        snapshot.get("maturity_value", snapshot.get("estimated_maturity_value", snapshot.get("sum_assured", policy.sum_assured))),
        _decimal(policy.sum_assured),
    )


def _requisition_number():
    try:
        value = NumberingEngine.generate_number("FO_REQUISITION", FORequisition, field_name="requisition_number")
        if value:
            return value
    except Exception:
        pass
    return f"MAT-{date.today():%Y%m%d}-{uuid4().hex[:10].upper()}"


def _create_requisition(claim):
    return FORequisition.objects.create(
        requisition_number=_requisition_number(),
        department="OL_MATURITY_CLAIMS",
        amount=claim.net_payout,
        reason=f"Maturity payout for {claim.claim_number} / {claim.policy.policy_number}.",
        status="PENDING",
    )


def _snapshot(policy):
    return {
        "status": policy.status,
        "maturity_date": policy.maturity_date.isoformat(),
        "contract_snapshot": policy.contract_snapshot,
    }


def _record(policy, *, event_type, before, reason, actor=None, request=None, source_channel="SYSTEM", event_code=None, metadata=None):
    after = AuditService.snapshot(policy)
    PolicyAuditLog.objects.create(
        policy=policy,
        actor=actor,
        event_type=event_type,
        from_status=before.get("status", ""),
        to_status=policy.status,
        before_snapshot=before,
        after_snapshot=after,
        reason=reason,
        source_channel=source_channel,
        correlation_id=getattr(request, "request_id", "") if request else "",
    )
    AuditService.log_action(
        event_type.upper(),
        policy,
        actor=actor,
        request=request,
        before_state=before,
        after_state=after,
        changed_fields=["status", "contract_snapshot"],
        reason=reason,
        source_channel=source_channel,
    )
    if event_code:
        emit_policy_loan_event(
            event_code,
            policy,
            actor=actor,
            from_status=before.get("status", ""),
            reason=reason,
            source_channel=source_channel,
            metadata=metadata,
        )


@transaction.atomic
def create_maturity_claim(policy, *, as_of=None, actor=None, request=None, source_channel="BATCH"):
    as_of = _date(as_of)
    policy = Policy.objects.select_for_update().filter(pk=policy.pk).first()
    if policy is None:
        from ..errors import not_found

        raise not_found()
    existing = policy.maturity_claims.exclude(status=MaturityClaimStatus.DECLINED).first()
    if existing:
        return existing, False
    if policy.status != PolicyStatus.ACTIVE or policy.maturity_date > as_of:
        return None, False
    setup = _setup(policy, as_of)
    if setup is None or not setup.auto_create_maturity_claim:
        return None, False
    maturity_value = _maturity_value(policy)
    loan_deduction = _loan_deduction(policy)
    net_payout = max(Decimal("0.00"), maturity_value - loan_deduction).quantize(Decimal("0.01"))
    claim_status = MaturityClaimStatus.PENDING_DOCUMENTS if setup.require_documents else (
        MaturityClaimStatus.PENDING_APPROVAL if setup.require_approval else MaturityClaimStatus.APPROVED
    )
    before = _snapshot(policy)
    policy.status = PolicyStatus.MATURED_PENDING_PAYMENT
    policy.updated_by = actor
    policy.save(update_fields=["status", "updated_by", "updated_at"])
    claim = MaturityClaim.objects.create(
        policy=policy,
        claim_date=as_of,
        maturity_value=maturity_value,
        loan_deduction=loan_deduction,
        net_payout=net_payout,
        payout_method=setup.default_payout_method,
        status=claim_status,
        approval_required=setup.require_approval,
        documents_required=setup.require_documents,
        documents_verified=not setup.require_documents,
        reason=f"Maturity claim initiated for policy {policy.policy_number}.",
        created_by=actor,
        updated_by=actor,
    )
    if claim_status == MaturityClaimStatus.APPROVED:
        claim.payment_requisition = _create_requisition(claim)
        claim.save(update_fields=["payment_requisition", "updated_by", "updated_at"])
    reason = f"Maturity claim {claim.claim_number} created for {net_payout} {policy.currency}."
    _record(
        policy,
        event_type="PolicyMaturityClaimCreated",
        before=before,
        reason=reason,
        actor=actor,
        request=request,
        source_channel=source_channel,
        event_code=POLICY_MATURITY_CLAIM_CREATED,
        metadata={"claim_number": claim.claim_number, "net_payout": str(net_payout)},
    )
    return claim, True


@transaction.atomic
def approve_maturity_claim(claim_id, *, documents_verified=False, actor=None, request=None, source_channel="API"):
    claim = MaturityClaim.objects.select_for_update().select_related("policy").filter(pk=claim_id).first()
    if claim is None:
        raise registry_error("POLICY_NOT_MATURED", message="The requested maturity claim was not found.")
    if claim.documents_required and not (documents_verified or claim.documents_verified):
        raise registry_error(
            "POLICY_NOT_MATURED",
            message="Required maturity documents must be verified before approval.",
            field_errors={"documents_verified": ["Confirm that all required maturity documents are verified."]},
        )
    if claim.status == MaturityClaimStatus.APPROVED:
        return claim
    if claim.status != MaturityClaimStatus.PENDING_APPROVAL and claim.status != MaturityClaimStatus.PENDING_DOCUMENTS:
        raise registry_error("POLICY_INVALID_STATUS", message=f"Maturity claim status {claim.status} cannot be approved.")
    claim.documents_verified = True
    claim.status = MaturityClaimStatus.APPROVED
    claim.payment_requisition = claim.payment_requisition or _create_requisition(claim)
    claim.updated_by = actor
    claim.save(update_fields=["documents_verified", "status", "payment_requisition", "updated_by", "updated_at"])
    reason = f"Maturity claim {claim.claim_number} approved for payout."
    _record(
        claim.policy,
        event_type="PolicyMaturityClaimApproved",
        before={"status": PolicyStatus.MATURED_PENDING_PAYMENT},
        reason=reason,
        actor=actor,
        request=request,
        source_channel=source_channel,
        event_code=POLICY_MATURITY_CLAIM_APPROVED,
        metadata={"claim_number": claim.claim_number, "requisition_number": claim.payment_requisition.requisition_number},
    )
    return claim


@transaction.atomic
def pay_maturity_claim(claim_id, *, payment_reference="", actor=None, request=None, source_channel="API"):
    claim = MaturityClaim.objects.select_for_update().select_related("policy", "payment_requisition").filter(pk=claim_id).first()
    if claim is None:
        raise registry_error("POLICY_NOT_MATURED", message="The requested maturity claim was not found.")
    if claim.status != MaturityClaimStatus.APPROVED:
        raise registry_error("POLICY_INVALID_STATUS", message="Only an approved maturity claim can be paid.")
    payment_reference = (payment_reference or "").strip()
    if not payment_reference:
        raise registry_error(
            "POLICY_NOT_MATURED",
            message="A payment reference is required to complete maturity payout.",
            field_errors={"payment_reference": ["Enter the bank or payment reference."]},
        )
    before = _snapshot(claim.policy)
    claim.status = MaturityClaimStatus.PAID
    claim.payment_reference = payment_reference
    claim.updated_by = actor
    claim.save(update_fields=["status", "payment_reference", "updated_by", "updated_at"])
    if claim.payment_requisition:
        claim.payment_requisition.status = "PAID"
        claim.payment_requisition.save(update_fields=["status", "updated_at"])
    policy = claim.policy
    policy.status = PolicyStatus.MATURED
    policy.updated_by = actor
    policy.save(update_fields=["status", "updated_by", "updated_at"])
    reason = f"Maturity claim {claim.claim_number} paid with reference {payment_reference}."
    _record(
        policy,
        event_type="PolicyMaturityPaid",
        before=before,
        reason=reason,
        actor=actor,
        request=request,
        source_channel=source_channel,
        event_code=POLICY_MATURITY_PAID,
        metadata={"claim_number": claim.claim_number, "payment_reference": payment_reference},
    )
    return claim


def process_policy_maturity(*, as_of=None, actor=None, source_channel="BATCH"):
    as_of = _date(as_of)
    processed = 0
    created = 0
    skipped = 0
    for policy in Policy.objects.filter(status=PolicyStatus.ACTIVE, maturity_date__lte=as_of).iterator():
        processed += 1
        _claim, was_created = create_maturity_claim(policy, as_of=as_of, actor=actor, source_channel=source_channel)
        if was_created:
            created += 1
        else:
            skipped += 1
    return {"processed": processed, "created": created, "skipped": skipped}
