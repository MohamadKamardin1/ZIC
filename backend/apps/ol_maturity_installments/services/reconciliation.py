"""Reconciliation and audit-consistency services.

Reconciliation verifies that the paid installments on a plan sum to the
maturity value within a configured tolerance; the audit-consistency utility
verifies that every non-initial status change is backed by an audit row and
that no item is orphaned. Both report pass/fail outcomes that can be traced
end-to-end through the audit log.
"""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from django.db import transaction

from apps.governance.models import AuditLog
from apps.governance.services.audit_service import AuditService

from ..errors import registry_error
from ..models import (
    InstallmentItemStatus,
    InstallmentPlanStatus,
    OLInstallmentItem,
    OLMaturityInstallmentPlan,
)

RECONCILIATION_TOLERANCE = Decimal("0.01")


def _money(value):
    return str((value or Decimal("0.00")).quantize(Decimal("0.01")))


def _decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise registry_error(
            "INSTALLMENT_INVALID_AMOUNT",
            message="The amount must be a valid numeric currency value.",
            field_errors={"amount": ["Enter a numeric amount using digits and a decimal point."]},
        ) from None


def _audited_status(log):
    return (log.after_state or {}).get("status", "")


@dataclass
class ReconciliationDiscrepancy:
    code: str
    message: str
    amount: str = ""
    expected: str = ""
    actual: str = ""
    item_numbers: list = field(default_factory=list)

    def to_dict(self):
        return {
            "code": self.code,
            "message": self.message,
            "amount": self.amount,
            "expected": self.expected,
            "actual": self.actual,
            "item_numbers": self.item_numbers,
        }


@dataclass
class ReconciliationReport:
    plan_id: str
    plan_number: str
    policy_number: str
    status: str
    maturity_value: str
    total_payable_amount: str
    paid_amount: str
    missing_amount: str
    paid_item_count: int
    total_item_count: int
    discrepancies: list = field(default_factory=list)

    def to_dict(self):
        return {
            "plan_id": self.plan_id,
            "plan_number": self.plan_number,
            "policy_number": self.policy_number,
            "status": self.status,
            "maturity_value": self.maturity_value,
            "total_payable_amount": self.total_payable_amount,
            "paid_amount": self.paid_amount,
            "missing_amount": self.missing_amount,
            "paid_item_count": self.paid_item_count,
            "total_item_count": self.total_item_count,
            "discrepancies": [item.to_dict() for item in self.discrepancies],
        }


@transaction.atomic
def validate_plan_reconciliation(
    *,
    plan_id,
    tolerance=None,
    actor=None,
    source_channel="API",
    request=None,
):
    """Reconcile a plan's paid installments against its maturity value.

    Sums every PAID item amount and compares the result with the plan's total
    payable amount (which the schedule guarantees equals the maturity value),
    flagging any shortfall, over-payment, or plan-total mismatch beyond the
    tolerance. Returns a pass/fail ``ReconciliationReport``.
    """
    plan = OLMaturityInstallmentPlan.objects.select_related("policy_ref", "partner").filter(pk=plan_id).first()
    if plan is None:
        raise registry_error("INSTALLMENT_PLAN_NOT_FOUND", details={"plan_id": str(plan_id)})

    if tolerance is not None:
        tol = _decimal(tolerance)
        if tol < 0:
            raise registry_error(
                "INSTALLMENT_INVALID_AMOUNT",
                message="Reconciliation tolerance must not be negative.",
                field_errors={"tolerance": ["Enter a non-negative tolerance amount."]},
            )
    else:
        tol = RECONCILIATION_TOLERANCE

    items = list(plan.items.order_by("installment_number"))
    paid_items = [item for item in items if item.status == InstallmentItemStatus.PAID]
    paid_sum = sum((item.amount for item in paid_items), Decimal("0.00"))
    expected = _decimal(plan.total_payable_amount)
    maturity = _decimal(plan.total_maturity_value)
    missing = expected - paid_sum

    discrepancies = []
    if abs(expected - maturity) > tol:
        discrepancies.append(
            ReconciliationDiscrepancy(
                code="PLAN_TOTAL_MISMATCH",
                message="The plan total payable differs from the policy maturity value.",
                amount=_money(expected - maturity),
                expected=_money(expected),
                actual=_money(maturity),
            )
        )
    if missing > tol:
        unpaid_numbers = [item.installment_number for item in items if item.status != InstallmentItemStatus.PAID]
        discrepancies.append(
            ReconciliationDiscrepancy(
                code="MISSING_PAYMENTS",
                message="One or more installments remain unpaid.",
                amount=_money(missing),
                expected=_money(expected),
                actual=_money(paid_sum),
                item_numbers=unpaid_numbers,
            )
        )
    if missing < -tol:
        discrepancies.append(
            ReconciliationDiscrepancy(
                code="OVER_PAYMENT",
                message="Paid installments exceed the plan total payable amount.",
                amount=_money(-missing),
                expected=_money(expected),
                actual=_money(paid_sum),
            )
        )

    report = ReconciliationReport(
        plan_id=str(plan.pk),
        plan_number=plan.plan_number,
        policy_number=plan.policy_ref.policy_number,
        status="PASS" if not discrepancies else "FAIL",
        maturity_value=_money(maturity),
        total_payable_amount=_money(expected),
        paid_amount=_money(paid_sum),
        missing_amount=_money(max(missing, Decimal("0.00"))),
        paid_item_count=len(paid_items),
        total_item_count=len(items),
        discrepancies=discrepancies,
    )

    AuditService.log(
        action_type="INSTALLMENT_RECONCILIATION_RUN",
        entity_type="ol_maturity_installments.olmaturityinstallmentplan",
        entity_id=plan.pk,
        entity_repr=plan.plan_number,
        before_state={},
        after_state=report.to_dict(),
        description=f"Reconciliation run for plan {plan.plan_number}: {report.status}.",
        actor=actor,
        action="INSTALLMENT_RECONCILIATION_RUN",
        app_label="ol_maturity_installments",
        model_name="olmaturityinstallmentplan",
        object_id=str(plan.pk),
        object_repr=plan.plan_number,
        reason="Financial reconciliation of paid installments against the maturity value.",
        source_channel=source_channel,
        request=request,
    )
    return report


@dataclass
class AuditFinding:
    code: str
    message: str
    entity_type: str
    entity_repr: str
    entity_id: str = ""
    expected_status: str = ""

    def to_dict(self):
        return {
            "code": self.code,
            "message": self.message,
            "entity_type": self.entity_type,
            "entity_repr": self.entity_repr,
            "entity_id": self.entity_id,
            "expected_status": self.expected_status,
        }


@dataclass
class AuditConsistencyReport:
    status: str
    checked_plans: int
    checked_items: int
    findings: list = field(default_factory=list)

    def to_dict(self):
        return {
            "status": self.status,
            "checked_plans": self.checked_plans,
            "checked_items": self.checked_items,
            "findings": [finding.to_dict() for finding in self.findings],
        }


@transaction.atomic
def validate_audit_consistency(
    *,
    plan_id=None,
    actor=None,
    source_channel="SYSTEM",
):
    """Verify the audit trail covers every status change end-to-end.

    For each plan (optionally scoped to one), confirms an audit row exists and
    reflects its current status; for each item, confirms any non-initial status
    (anything past SCHEDULED) is backed by an item-level audit row. Orphan items
    with no valid plan are flagged. Returns a pass/fail report.
    """
    plans_qs = OLMaturityInstallmentPlan.objects.select_related("policy_ref").order_by("plan_number")
    if plan_id:
        plans_qs = plans_qs.filter(pk=plan_id)

    findings = []
    checked_plans = 0
    checked_items = 0
    for plan in plans_qs:
        checked_plans += 1
        plan_audits = list(AuditLog.objects.filter(app_label="ol_maturity_installments", object_id=str(plan.pk)))
        if not plan_audits:
            findings.append(
                AuditFinding(
                    code="PLAN_MISSING_AUDIT",
                    message=f"Plan {plan.plan_number} has no audit trail.",
                    entity_type="plan",
                    entity_repr=plan.plan_number,
                    entity_id=str(plan.pk),
                    expected_status=plan.status,
                )
            )
        elif plan.status != InstallmentPlanStatus.CREATED and not any(
            _audited_status(log) == plan.status for log in plan_audits
        ):
            findings.append(
                AuditFinding(
                    code="PLAN_STATUS_NOT_AUDITED",
                    message=f"Plan {plan.plan_number} reached {plan.status} without a matching audit row.",
                    entity_type="plan",
                    entity_repr=plan.plan_number,
                    entity_id=str(plan.pk),
                    expected_status=plan.status,
                )
            )

        for item in plan.items.select_related("plan_ref").order_by("installment_number"):
            checked_items += 1
            if item.plan_ref_id is None:
                findings.append(
                    AuditFinding(
                        code="ORPHAN_ITEM",
                        message=f"Item {item.installment_number} has no parent plan.",
                        entity_type="item",
                        entity_repr=f"{plan.plan_number}: installment {item.installment_number}",
                        entity_id=str(item.pk),
                    )
                )
                continue
            if item.status == InstallmentItemStatus.SCHEDULED:
                continue
            item_audits = list(AuditLog.objects.filter(app_label="ol_maturity_installments", object_id=str(item.pk)))
            if not item_audits or not any(_audited_status(log) == item.status for log in item_audits):
                findings.append(
                    AuditFinding(
                        code="ITEM_STATUS_NOT_AUDITED",
                        message=f"Installment {item.installment_number} reached {item.status} without a matching audit row.",
                        entity_type="item",
                        entity_repr=f"{plan.plan_number}: installment {item.installment_number}",
                        entity_id=str(item.pk),
                        expected_status=item.status,
                    )
                )

    orphan_ids = set(OLInstallmentItem.objects.filter(plan_ref_id__isnull=True).values_list("pk", flat=True))
    orphan_ids |= set(
        OLInstallmentItem.objects.select_related("plan_ref")
        .filter(plan_ref_id__isnull=False, plan_ref__isnull=True)
        .values_list("pk", flat=True)
    )
    for orphan_pk in orphan_ids:
        findings.append(
            AuditFinding(
                code="ORPHAN_ITEM",
                message="An installment item exists without a valid parent plan.",
                entity_type="item",
                entity_repr="orphan item",
                entity_id=str(orphan_pk),
            )
        )

    return AuditConsistencyReport(
        status="PASS" if not findings else "FAIL",
        checked_plans=checked_plans,
        checked_items=checked_items,
        findings=findings,
    )
