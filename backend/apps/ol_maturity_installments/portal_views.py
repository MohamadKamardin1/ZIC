"""Partner portal for maturity installment plans.

Strictly read-only and scoped to the caller's visible partners: partners see
only their own plans (by number or id) with a sanitized, customer-safe payload.
No internal actions or error details are exposed.
"""

from decimal import Decimal
from uuid import UUID

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import InstallmentItemStatus, OLMaturityInstallmentPlan

ZERO = Decimal("0.00")
PENDING_ITEM_STATUSES = (InstallmentItemStatus.SCHEDULED, InstallmentItemStatus.PAYMENT_PENDING)


def _portal_error(message, status_code=404):
    return Response(
        {
            "success": False,
            "status_code": status_code,
            "error_code": "PORTAL_RESOURCE_NOT_FOUND",
            "code": "PORTAL_RESOURCE_NOT_FOUND",
            "message": message,
            "resolution_steps": ["Confirm that the installment plan belongs to your linked partner profile."],
        },
        status=status_code,
    )


def _money(value):
    return f"{Decimal(str(value or 0)).quantize(Decimal('0.01')):,.2f}"


def _schedule_rows(plan):
    return [
        {
            "installment_number": item.installment_number,
            "due_date": str(item.due_date),
            "amount": _money(item.amount),
            "status": item.get_status_display(),
            "paid_date": str(item.paid_date) if item.paid_date else "",
            "payment_reference": item.payment_reference or "",
        }
        for item in plan.items.all()
    ]


def _portal_payload(plan, *, detail=False):
    paid = sum(
        (Decimal(item.amount) for item in plan.items.all() if item.status == InstallmentItemStatus.PAID), ZERO
    )
    total = Decimal(plan.total_payable_amount)
    balance = max(ZERO, total - paid)
    next_due = next(
        (
            item.due_date
            for item in plan.items.all()
            if item.status in PENDING_ITEM_STATUSES
        ),
        None,
    )
    policy = plan.policy_ref
    payload = {
        "plan_number": plan.plan_number,
        "policy_number": getattr(policy, "policy_number", "Not recorded"),
        "policyholder": _portal_name(plan),
        "status": plan.status,
        "status_display": plan.get_status_display(),
        "currency": plan.currency,
        "frequency": plan.frequency,
        "total_amount": _money(total),
        "paid_amount": _money(paid),
        "balance": _money(balance),
        "total_installments": plan.installment_count,
        "paid_installments": sum(1 for item in plan.items.all() if item.status == InstallmentItemStatus.PAID),
        "start_date": str(plan.start_date),
        "end_date": str(plan.end_date),
        "next_due_date": str(next_due) if next_due else "",
        "linked_claim_number": plan.maturity_claim_ref.claim_number if plan.maturity_claim_ref_id else "",
    }
    if detail:
        payload["schedule"] = _schedule_rows(plan)
    return payload


def _portal_name(plan):
    return (
        getattr(plan.partner, "legal_name", "")
        or getattr(plan.partner, "partner_number", "")
        or "Policyholder"
    )


def _scoped_queryset(user):
    return (
        OLMaturityInstallmentPlan.objects.filter(partner__in=user.visible_partners())
        .select_related("partner", "policy_ref", "maturity_claim_ref")
        .prefetch_related("items")
    )


class OLMaturityInstallmentPortalListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plans = _scoped_queryset(request.user).order_by("-created_at", "plan_number")
        return Response(
            {
                "success": True,
                "data": {
                    "count": plans.count(),
                    "results": [_portal_payload(plan) for plan in plans],
                },
            }
        )


class OLMaturityInstallmentPortalDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, plan_id):
        plan = _scoped_queryset(request.user).filter(plan_number=str(plan_id)).first()
        if plan is None:
            try:
                plan_uuid = UUID(str(plan_id))
            except (TypeError, ValueError, AttributeError):
                plan_uuid = None
            if plan_uuid is not None:
                plan = _scoped_queryset(request.user).filter(pk=plan_uuid).first()
        if plan is None:
            return _portal_error("The requested installment plan is not available in your partner portal.")
        return Response({"success": True, "data": _portal_payload(plan, detail=True)})
