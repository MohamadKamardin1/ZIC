"""Front Office Receipts — read-side work queue helpers.

Prompt 7: the list/work-queue filter pipeline, KPI aggregates, CSV column
contract, and the per-receipt audit timeline. Every aggregate respects the same
filters as the list endpoint so the queue totals always match the visible rows.
"""

from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.front_office.receipts.models import (
    Receipt,
    ReceiptAllocation,
    ReceiptDocument,
    ReceiptReversal,
    ReceiptStatus,
    ReceiptStatusHistory,
)

ZERO = Decimal("0.00")

# Prompt 7 list columns (also the CSV column order). Display names, never UUIDs.
LIST_COLUMNS = (
    "receipt_number",
    "receipt_date",
    "payer_display",
    "branch_display",
    "payment_mode_display",
    "currency_display",
    "receipt_amount",
    "allocated_amount",
    "unallocated_amount",
    "status",
    "source_module",
    "created_by_display",
    "posted_by_display",
    "created_at",
    "allowed_actions",
)

_ORDER_MAP = {
    "receipt_number": "receipt_number",
    "receipt_date": "receipt_date",
    "status": "status",
    "receipt_amount": "receipt_amount",
    "allocated_amount": "allocated_amount",
    "unallocated_amount": "unallocated_amount",
    "created_at": "created_at",
}

# Open statuses still carrying unallocated money; reversed/cancelled receipts are
# excluded from the total_unallocated KPI.
_OPEN_STATUSES = (
    ReceiptStatus.DRAFT,
    ReceiptStatus.POSTED,
    ReceiptStatus.PARTIALLY_ALLOCATED,
    ReceiptStatus.FULLY_ALLOCATED,
)


def _true(value):
    return str(value or "").strip().lower() in ("true", "1", "yes", "on")


def _dominant_currency(queryset):
    """Most common receipt currency for the set, so KPI cards can label amounts."""
    row = queryset.values("currency").annotate(count=Count("id")).order_by("-count").first()
    return row["currency"] if row and row.get("currency") else "TZS"


def filter_receipts(queryset, params):
    """Apply the list/KPI/export filter pipeline (status, branch, currency, ...).

    ``params`` is the request query dict. Unrecognised parameters are ignored.
    """
    status = params.get("status")
    if status:
        queryset = queryset.filter(status__iexact=status)
    branch = params.get("branch")
    if branch:
        queryset = queryset.filter(branch_id=branch)
    partner = params.get("partner")
    if partner:
        queryset = queryset.filter(partner_id=partner)
    payer = params.get("payer")
    if payer:
        queryset = queryset.filter(
            Q(payer_name__icontains=payer) | Q(partner_name_snapshot__icontains=payer)
        )
    source_module = params.get("source_module")
    if source_module:
        queryset = queryset.filter(source_module__iexact=source_module)
    currency = params.get("currency")
    if currency:
        queryset = queryset.filter(currency__iexact=currency)
    payment_mode = params.get("payment_mode")
    if payment_mode:
        queryset = queryset.filter(payment_mode__iexact=payment_mode)

    date_from = params.get("receipt_date_from") or params.get("date_from")
    if date_from:
        queryset = queryset.filter(receipt_date__gte=date_from)
    date_to = params.get("receipt_date_to") or params.get("date_to")
    if date_to:
        queryset = queryset.filter(receipt_date__lte=date_to)

    if _true(params.get("unallocated_only")):
        queryset = queryset.filter(unallocated_amount__gt=0)
    if _true(params.get("allocated_only")):
        queryset = queryset.filter(allocated_amount__gt=0)
    if _true(params.get("reversed_only")):
        queryset = queryset.filter(status=ReceiptStatus.REVERSED)

    search = params.get("search")
    if search:
        queryset = queryset.filter(
            Q(receipt_number__icontains=search)
            | Q(payer_name__icontains=search)
            | Q(partner_name_snapshot__icontains=search)
            | Q(payment_reference__icontains=search)
            | Q(source_reference_id__icontains=search)
        )
    return queryset


def apply_ordering(queryset, params):
    """Resolve the ``ordering`` parameter against the allow-list (default newest first)."""
    ordering = params.get("ordering", "-receipt_date")
    key = None
    if ordering.startswith("-"):
        key = _ORDER_MAP.get(ordering[1:])
        if key:
            ordering = f"-{key}"
    else:
        key = _ORDER_MAP.get(ordering)
        if key:
            ordering = key
    return queryset.order_by(ordering, "-created_at")


def receipt_kpis(queryset):
    """Work-queue aggregates over the filtered receipt set.

    ``total_unallocated`` sums the unallocated balance of open (non-reversed,
    non-cancelled) receipts; ``reversed_amount`` sums only reversed receipts.
    ``receipts_today``/``amount_received_today`` scope to the local calendar day
    and power the front-office dashboard KPI hook; ``unallocated_receipts`` and
    ``reversed_receipts`` are the open-balance and reversed counts. Amounts are
    quantized to two decimal places to match stored column scale.
    """
    def _money(value):
        return str((value or ZERO).quantize(Decimal("0.01")))

    today = timezone.localdate()
    today_queryset = queryset.filter(receipt_date=today)

    total_received_period = queryset.aggregate(value=Sum("receipt_amount"))["value"] or ZERO
    total_allocated_period = queryset.aggregate(value=Sum("allocated_amount"))["value"] or ZERO
    total_unallocated = (
        queryset.filter(status__in=_OPEN_STATUSES).aggregate(value=Sum("unallocated_amount"))["value"] or ZERO
    )
    reversed_amount = (
        queryset.filter(status=ReceiptStatus.REVERSED).aggregate(value=Sum("receipt_amount"))["value"] or ZERO
    )
    amount_received_today = today_queryset.aggregate(value=Sum("receipt_amount"))["value"] or ZERO
    currency = _dominant_currency(queryset)
    return {
        "total_received_period": _money(total_received_period),
        "total_allocated_period": _money(total_allocated_period),
        "total_unallocated": _money(total_unallocated),
        "receipt_count": queryset.count(),
        "reversed_amount": _money(reversed_amount),
        "receipts_today": today_queryset.count(),
        "amount_received_today": _money(amount_received_today),
        "unallocated_receipts": queryset.filter(
            status__in=_OPEN_STATUSES, unallocated_amount__gt=0
        ).count(),
        "reversed_receipts": queryset.filter(status=ReceiptStatus.REVERSED).count(),
        # camelCase/display aliases consumed by the web front-end KPI cards.
        "received_today": _money(amount_received_today),
        "allocated_in_period": _money(total_allocated_period),
        "unallocated_amount": _money(total_unallocated),
        "unallocated_receipt_count": queryset.filter(
            status__in=_OPEN_STATUSES, unallocated_amount__gt=0
        ).count(),
        "currency": currency,
    }


def _audit_summary(state, changed_fields):
    """Compact before/after summary for the timeline, from the audit snapshot."""
    if not isinstance(state, dict):
        return None
    if "status" in state and state.get("status"):
        return str(state["status"])
    pieces = []
    for field in changed_fields or []:
        value = state.get(field)
        if value not in (None, "", []):
            pieces.append(f"{field}: {value}")
    return ", ".join(pieces) if pieces else None


def _actor_display(actor):
    if actor is None:
        return None
    if hasattr(actor, "get_full_name"):
        full = actor.get_full_name() or ""
        if full:
            return full
    return getattr(actor, "username", None) or str(actor)


def audit_timeline(receipt):
    """Central audit entries for a receipt and its related records, newest first.

    Includes the receipt's own CREATE/UPDATE rows plus those of its allocations,
    reversals, documents, and status-history rows, so the detail view renders a
    single reconstructible timeline (actor, reason, changed fields).
    """
    from apps.governance.models import AuditLog

    query = Q(entity_type=Receipt._meta.model_name, object_id=str(receipt.pk))
    for model in (ReceiptAllocation, ReceiptReversal, ReceiptDocument, ReceiptStatusHistory):
        pks = list(model.objects.filter(receipt=receipt).values_list("pk", flat=True))
        if pks:
            query |= Q(model_name=model._meta.model_name, object_id__in=[str(pk) for pk in pks])

    entries = AuditLog.objects.filter(query).order_by("-timestamp", "-created_at")
    return [
        {
            "id": str(entry.pk),
            "action": entry.action_type,
            "entity": entry.model_name or entry.entity_type,
            "entity_repr": entry.object_repr or entry.entity_repr or "",
            "changed_fields": entry.changed_fields or [],
            "reason": entry.reason or "",
            "actor": _actor_display(entry.user),
            "actor_id": str(entry.user_id) if entry.user_id else None,
            "source_channel": entry.source_channel or "",
            "timestamp": entry.timestamp.isoformat(),
            # camelCase/display aliases consumed by the detail audit timeline.
            "actor_display": _actor_display(entry.user),
            "occurred_at": entry.timestamp.isoformat(),
            "before_summary": _audit_summary(entry.before_state, entry.changed_fields),
            "after_summary": _audit_summary(entry.after_state, entry.changed_fields),
        }
        for entry in entries
    ]
