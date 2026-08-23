"""Proposal listing: filters, ordering, KPIs, and CSV row source.

Table-first: every filter is applied to the queryset before pagination/export so
the list, CSV, and KPI endpoints stay consistent with the same contract.
"""

from datetime import date, timedelta

from django.db.models import Prefetch, Q

from apps.ol_proposals.models import OLProposal, OLProposalPlanConfig
from apps.ol_proposals.services import parameter_resolver

TERMINAL_FALLBACK = ("CANCELLED", "EXPIRED", "CONVERTED")

ORDERABLE_FIELDS = {"proposal_number", "created_at", "updated_at", "expiry_date", "status"}


def _terminal_statuses():
    return set(parameter_resolver.terminal_proposal_statuses() or TERMINAL_FALLBACK)


def _parse_bool(value):
    if value is None:
        return None
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def base_list_queryset():
    selected = Prefetch(
        "plan_configs",
        queryset=OLProposalPlanConfig.objects.filter(is_selected=True).select_related(
            "plan", "product_version__product"
        ),
    )
    return OLProposal.objects.select_related(
        "quotation", "partner", "agent_partner", "employer_partner", "first_premium_commitment"
    ).prefetch_related(selected)


def apply_list_filters(queryset, params):
    """Apply the shared list/export filter contract from query parameters."""
    status = params.get("status")
    if status:
        queryset = queryset.filter(status__iexact=status)

    product = params.get("product")
    if product:
        queryset = queryset.filter(
            Q(plan_configs__product_version__product__code__iexact=product)
            | Q(plan_configs__product_version__product__pk=product)
        )

    agent = params.get("agent")
    if agent:
        queryset = queryset.filter(agent_partner_id=agent)

    has_employer = _parse_bool(params.get("has_employer"))
    if has_employer is not None:
        queryset = queryset.filter(employer_partner__isnull=not has_employer)

    expiry_from = params.get("expiry_from")
    if expiry_from:
        queryset = queryset.filter(expiry_date__gte=expiry_from)
    expiry_to = params.get("expiry_to")
    if expiry_to:
        queryset = queryset.filter(expiry_date__lte=expiry_to)

    payment_ready = _parse_bool(params.get("payment_ready"))
    if payment_ready is not None:
        queryset = queryset.filter(payment_ready=payment_ready)

    first_premium_posted = _parse_bool(params.get("first_premium_posted"))
    if first_premium_posted is not None:
        posted = Q(first_premium_commitment__status="COMPLETED", first_premium_commitment__balance__lte=0)
        queryset = queryset.filter(posted) if first_premium_posted else queryset.exclude(posted)

    search = params.get("search")
    if search:
        queryset = queryset.filter(
            Q(proposal_number__icontains=search)
            | Q(partner_name_snapshot__icontains=search)
            | Q(agent_name_snapshot__icontains=search)
            | Q(quotation__quote_number__icontains=search)
            | Q(members__identity_number__icontains=search)
            | Q(members__full_name_snapshot__icontains=search)
        ).distinct()
    return queryset


def order_queryset(queryset, ordering=None):
    ordering = (ordering or "-created_at") or "-created_at"
    direction = ""
    key = ordering
    if key.startswith("-"):
        direction, key = "-", key[1:]
    if key not in ORDERABLE_FIELDS:
        direction, key = "-", "created_at"
    return queryset.order_by(f"{direction}{key}", "-created_at")


def proposal_kpis(*, period_from=None, period_to=None, expiring_soon_days=None, as_of=None):
    """Return register KPIs. Converted-in-period honors optional date bounds."""
    today = as_of or date.today()
    try:
        days = max(0, int(expiring_soon_days if expiring_soon_days is not None else 30))
    except (TypeError, ValueError):
        days = 30

    base = OLProposal.objects.all()
    terminal = _terminal_statuses()

    converted = base.filter(status="CONVERTED")
    if period_from:
        converted = converted.filter(created_at__date__gte=period_from)
    if period_to:
        converted = converted.filter(created_at__date__lte=period_to)

    expiring_soon = (
        base.filter(
            expiry_date__isnull=False,
            expiry_date__gte=today,
            expiry_date__lte=today + timedelta(days=days),
        ).exclude(status__in=terminal)
    )

    return {
        "total_proposals": base.count(),
        "pending_underwriting": base.filter(status="PENDING_UNDERWRITING").count(),
        "payment_ready": base.filter(status="PAYMENT_READY").count(),
        "awaiting_first_premium": base.filter(status="AWAITING_FIRST_PREMIUM").count(),
        "converted": base.filter(status="CONVERTED").count(),
        "converted_in_period": converted.count(),
        "expiring_soon": expiring_soon.count(),
        "cancelled": base.filter(status="CANCELLED").count(),
        "expired": base.filter(status="EXPIRED").count(),
    }


def iter_csv_rows(serialized_rows):
    """Emit flat CSV rows from list-serialized data (names, never UUIDs)."""
    for row in serialized_rows:
        yield [
            row["proposal_number"],
            row["policyholder"],
            row["agent"],
            row["employer"],
            row["product"],
            row["plan"],
            row["total_premium"],
            row["currency"],
            row["status"],
            row["payment_ready"],
            row["first_premium_posted"],
            row["expiry_date"] or "",
            row["created_at"],
        ]