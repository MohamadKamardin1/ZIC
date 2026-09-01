"""Installment payment processing and confirmation service.

Processing raises a Front Office disbursement requisition against the
policyholder's bank details and moves the item to PAYMENT_PENDING; a
confirmation (callback) marks the item PAID and completes the plan when every
installment has been paid. Both paths are idempotent and fully audited.
"""

from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from apps.front_office.models import FORequisition
from apps.governance.services.audit_service import AuditService

from ..errors import registry_error
from ..events import emit_installment_payment_due, emit_installment_plan_completed
from ..models import (
    InstallmentItemStatus,
    InstallmentPlanStatus,
    OLInstallmentItem,
    OLMaturityInstallmentPlan,
)

PROCESSABLE_ITEM_STATUSES = (
    InstallmentItemStatus.SCHEDULED,
    InstallmentItemStatus.PAYMENT_PENDING,
    InstallmentItemStatus.MISSED,
)
REQUISITION_DEPARTMENT = "MATURITY_INSTALLMENTS"
REQUISITION_STATUS = "PENDING"

BANK_DETAIL_KEYS = (
    "bank_name",
    "branch_name",
    "account_name",
    "account_number",
    "swift_code",
    "iban",
    "currency",
)


def _resolve_bank_account(partner):
    accounts = list(partner.bank_accounts.all())
    if not accounts:
        return None
    for account in accounts:
        if account.is_primary and account.is_verified:
            return account
    for account in accounts:
        if account.is_primary:
            return account
    for account in accounts:
        if account.is_verified:
            return account
    return accounts[0]


def _bank_snapshot(account):
    return {key: getattr(account, key, "") or "" for key in BANK_DETAIL_KEYS}


def _item_snapshot(item, requisition=None):
    return {
        "installment_number": item.installment_number,
        "status": item.status,
        "due_date": str(item.due_date),
        "amount": str(item.amount),
        "requisition_number": getattr(requisition, "requisition_number", "") if requisition else "",
        "requisition_status": getattr(requisition, "status", "") if requisition else "",
        "paid_date": str(item.paid_date) if item.paid_date else "",
    }


def _all_items_paid(plan):
    return not OLInstallmentItem.objects.filter(plan_ref=plan).exclude(status=InstallmentItemStatus.PAID).exists()


def _item_requisition(item):
    if not item.payment_requisition_ref_id:
        return None
    return FORequisition.objects.filter(pk=item.payment_requisition_ref_id).first()


@transaction.atomic
def process_item_payment(
    *,
    item_id,
    actor=None,
    source_channel="API",
    request=None,
):
    """Raise a Front Office requisition for a due, payable installment.

    Idempotent: replaying returns the existing requisition with ``created``
    False. Returns ``(item, requisition, created)``.
    """
    item = (
        OLInstallmentItem.objects.select_for_update()
        .select_related(
            "plan_ref",
            "plan_ref__policy_ref",
            "plan_ref__partner",
            "payment_requisition_ref",
        )
        .filter(pk=item_id)
        .first()
    )
    if item is None:
        raise registry_error("INSTALLMENT_ITEM_NOT_FOUND", details={"item_id": str(item_id)})

    if item.status not in PROCESSABLE_ITEM_STATUSES:
        raise registry_error(
            "INSTALLMENT_ITEM_INVALID_STATUS",
            details={
                "installment_number": item.installment_number,
                "current_status": item.status,
                "allowed": [status.value for status in PROCESSABLE_ITEM_STATUSES],
            },
        )

    today = timezone.localdate()
    if item.due_date and item.due_date > today:
        raise registry_error(
            "INSTALLMENT_PAYMENT_NOT_DUE",
            details={
                "installment_number": item.installment_number,
                "due_date": str(item.due_date),
                "today": str(today),
            },
        )

    existing = _item_requisition(item)
    if existing is not None:
        return item, existing, False

    partner = item.plan_ref.partner
    bank_account = _resolve_bank_account(partner)
    if bank_account is None:
        raise registry_error(
            "INSTALLMENT_BANK_DETAILS_MISSING",
            details={
                "policy_number": item.plan_ref.policy_ref.policy_number,
                "partner_number": partner.partner_number,
            },
        )

    requisition = FORequisition.objects.create(
        requisition_number=f"FO-MIP-{timezone.localdate():%Y%m%d}-{uuid4().hex[:10].upper()}",
        department=REQUISITION_DEPARTMENT,
        amount=item.amount,
        reason=(
            f"Maturity installment {item.installment_number} for policy "
            f"{item.plan_ref.policy_ref.policy_number} to {bank_account.account_name} "
            f"({bank_account.bank_name} {bank_account.account_number})."
        ),
        status=REQUISITION_STATUS,
    )

    before = _item_snapshot(item, None)
    item.payment_requisition_ref = requisition
    item.payment_bank_details = _bank_snapshot(bank_account)
    item.status = InstallmentItemStatus.PAYMENT_PENDING
    item.updated_by = actor
    item.save(
        update_fields=[
            "payment_requisition_ref",
            "payment_bank_details",
            "status",
            "updated_by",
            "updated_at",
        ]
    )
    after = _item_snapshot(item, requisition)

    emit_installment_payment_due(
        item.plan_ref,
        item=item,
        actor=actor,
        from_status=before["status"],
        to_status=item.status,
        reason=f"Front Office requisition {requisition.requisition_number} raised for installment {item.installment_number}.",
        source_channel=source_channel,
        metadata={
            "policy_number": item.plan_ref.policy_ref.policy_number,
            "installment_number": item.installment_number,
            "requisition_number": requisition.requisition_number,
            "amount": str(item.amount),
            "currency": item.plan_ref.currency,
            "bank_account": bank_account.account_name,
            "bank_name": bank_account.bank_name,
        },
    )
    AuditService.log(
        action_type="INSTALLMENT_PAYMENT_PROCESSED",
        entity_type="ol_maturity_installments.olinstallmentitem",
        entity_id=item.pk,
        entity_repr=f"{item.plan_ref.plan_number}: installment {item.installment_number}",
        before_state=before,
        after_state=after,
        description=f"Payment requisition {requisition.requisition_number} raised for installment {item.installment_number}.",
        actor=actor,
        reason="Installment disbursement processed through the Front Office seam.",
        source_channel=source_channel,
        request=request,
        app_label="ol_maturity_installments",
        model_name="olinstallmentitem",
        object_id=str(item.pk),
        object_repr=f"{item.plan_ref.plan_number}: installment {item.installment_number}",
    )
    return item, requisition, True


@transaction.atomic
def confirm_item_payment(
    *,
    item_id,
    actor=None,
    source_channel="API",
    request=None,
    paid_date=None,
):
    """Confirm a disbursed installment as PAID and complete the plan when done.

    Idempotent: replaying an already-paid item returns it unchanged. Returns
    ``(item, plan_completed, confirmed)``.
    """
    item = (
        OLInstallmentItem.objects.select_for_update()
        .select_related("plan_ref", "plan_ref__policy_ref", "payment_requisition_ref")
        .filter(pk=item_id)
        .first()
    )
    if item is None:
        raise registry_error("INSTALLMENT_ITEM_NOT_FOUND", details={"item_id": str(item_id)})

    if item.status == InstallmentItemStatus.PAID:
        return item, _all_items_paid(item.plan_ref), False

    if item.status != InstallmentItemStatus.PAYMENT_PENDING:
        raise registry_error(
            "INSTALLMENT_ITEM_INVALID_STATUS",
            details={
                "installment_number": item.installment_number,
                "current_status": item.status,
                "allowed": [InstallmentItemStatus.PAYMENT_PENDING.value],
                "message": "Only a payment-pending installment can be confirmed as paid.",
            },
        )

    plan = OLMaturityInstallmentPlan.objects.select_for_update().get(pk=item.plan_ref_id)
    before = _item_snapshot(item, item.payment_requisition_ref)
    paid_date = paid_date or timezone.localdate()
    item.status = InstallmentItemStatus.PAID
    item.paid_date = paid_date
    item.updated_by = actor
    item.save(update_fields=["status", "paid_date", "updated_by", "updated_at"])

    after = _item_snapshot(item, item.payment_requisition_ref)
    requisition = _item_requisition(item)
    if requisition:
        requisition.status = "COMPLETED"
        requisition.save(update_fields=["status", "updated_at"])
        after["requisition_status"] = requisition.status

    plan_completed = _all_items_paid(plan)
    if plan_completed and plan.status != InstallmentPlanStatus.COMPLETED:
        plan_before = {
            "status": plan.status,
            "completed_at": str(plan.completed_at) if plan.completed_at else "",
        }
        plan.status = InstallmentPlanStatus.COMPLETED
        plan.completed_at = timezone.now()
        plan.completed_by = actor
        plan.save(update_fields=["status", "completed_at", "completed_by", "updated_at"])
        emit_installment_plan_completed(
            plan,
            actor=actor,
            from_status=plan_before["status"],
            to_status=plan.status,
            reason="Every installment has been paid; the plan is now complete.",
            source_channel=source_channel,
            metadata={
                "policy_number": plan.policy_ref.policy_number,
                "plan_number": plan.plan_number,
                "completed_item": item.installment_number,
                "installment_count": plan.installment_count,
                "total_payable_amount": str(plan.total_payable_amount),
            },
        )

    AuditService.log(
        action_type="INSTALLMENT_PAYMENT_CONFIRMED",
        entity_type="ol_maturity_installments.olinstallmentitem",
        entity_id=item.pk,
        entity_repr=f"{item.plan_ref.plan_number}: installment {item.installment_number}",
        before_state=before,
        after_state={**after, "paid_date": str(paid_date)},
        description=(
            f"Installment {item.installment_number} confirmed paid on {paid_date} "
            f"against requisition {requisition.requisition_number if requisition else 'n/a'}."
        ),
        actor=actor,
        reason="Installment disbursement confirmed as paid by the Front Office callback.",
        source_channel=source_channel,
        request=request,
        app_label="ol_maturity_installments",
        model_name="olinstallmentitem",
        object_id=str(item.pk),
        object_repr=f"{item.plan_ref.plan_number}: installment {item.installment_number}",
    )
    return item, plan_completed, True
