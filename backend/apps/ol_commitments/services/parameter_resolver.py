"""Parameter-driven resolvers for OL Commitments.

Everything that shapes a commitment (initial status, grace/lapse envelope,
notification schedule) is read exclusively from the OL Parameters catalogs in
``apps.ol_parameters``. Nothing here is hardcoded; when a catalog is empty the
resolvers return explicit ``None``/empty results so the calling layer can raise
the structured ``PARAMETER_MISSING`` error with navigation guidance.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import Q

from apps.ol_parameters.models import OLCommitmentStatus, OLGracePeriod

COMMITMENT_SCOPE = "COMMITMENT"


def _as_of(value):
    return value or date.today()


def _within_effect(queryset, as_of):
    day = _as_of(as_of)
    return queryset.filter(
        Q(effective_from__isnull=True) | Q(effective_from__lte=day),
        Q(effective_to__isnull=True) | Q(effective_to__gte=day),
    )


def default_commitment_status(as_of=None) -> str | None:
    """Return the initial commitment status code from the parameter catalog.

    Resolution: first active ``COMMITMENT``-scoped status by ``display_order``
    then ``code``. Falls back to any active commitment status when no
    COMMITMENT-scoped row exists. Returns ``None`` when the catalog is empty
    (callers raise ``PARAMETER_MISSING``).
    """
    queryset = _within_effect(OLCommitmentStatus.objects.filter(is_active=True), as_of)
    scoped = queryset.filter(applies_to__iexact=COMMITMENT_SCOPE).order_by("display_order", "code")
    status = scoped.first() or queryset.order_by("display_order", "code").first()
    return status.code if status else None


def is_valid_commitment_status(code, as_of=None) -> bool:
    """Return whether ``code`` is a currently valid commitment status parameter."""
    code = (code or "").strip().upper()
    if not code:
        return False
    queryset = _within_effect(OLCommitmentStatus.objects.filter(is_active=True), as_of)
    return queryset.filter(code__iexact=code).exists()


def is_terminal_commitment_status(code, as_of=None) -> bool:
    """Return whether ``code`` is flagged terminal in the parameter catalog."""
    code = (code or "").strip().upper()
    queryset = _within_effect(OLCommitmentStatus.objects.filter(is_active=True, code__iexact=code), as_of)
    status = queryset.order_by("display_order", "code").first()
    return bool(status and status.is_terminal)


@dataclass
class GraceEnvelope:
    grace_days: int = 0
    warning_days: int = 0
    pre_lapse_days: int = 0
    lapse_days: int = 0
    grace_date: date | None = None
    warning_date: date | None = None
    pre_lapse_date: date | None = None
    lapse_date: date | None = None
    minimum_due_amount: Decimal | None = None


def resolve_grace_period(product=None, plan=None, premium_frequency="", as_of=None):
    """Resolve the most specific active ``OLGracePeriod`` row for a scope.

    Resolution order (most specific first); unmatched rows are skipped:
    1. product + plan + frequency
    2. plan + frequency (product unset)
    3. product + frequency (plan unset)
    4. frequency only
    5. global row (product, plan, frequency all unset)
    """
    day = _as_of(as_of)
    product_id = getattr(product, "pk", product)
    plan_id = getattr(plan, "pk", plan)
    frequency = (premium_frequency or "").strip().upper()

    queryset = _within_effect(OLGracePeriod.objects.filter(is_active=True), day)
    if product_id:
        queryset = queryset.filter(Q(product_id=product_id) | Q(product__isnull=True))
    if plan_id:
        queryset = queryset.filter(Q(plan_id=plan_id) | Q(plan__isnull=True))
    if frequency:
        queryset = queryset.filter(Q(premium_frequency__iexact=frequency) | Q(premium_frequency=""))

    scored = []
    for row in queryset:
        row_frequency = (row.premium_frequency or "").strip().upper()
        score = (
            0 if (row.product_id == product_id and product_id) else (1 if product_id else 2),
            0 if (row.plan_id == plan_id and plan_id) else (1 if plan_id else 2),
            0 if row_frequency == frequency and frequency else (1 if frequency else 2),
        )
        scored.append((score, row))

    if not scored:
        return None
    scored.sort(key=lambda item: (item[0][0], item[0][1], item[0][2], item[1].code))
    return scored[0][1]


def compute_grace_envelope(due_date, product=None, plan=None, premium_frequency="", as_of=None) -> GraceEnvelope:
    """Compute the grace/warning/pre-lapse/lapse envelope for a due date."""
    if due_date is None:
        return GraceEnvelope()
    row = resolve_grace_period(product, plan, premium_frequency, as_of)
    envelope = GraceEnvelope(grace_days=0)
    if row is None:
        return envelope
    from datetime import timedelta

    envelope.grace_days = row.grace_days or 0
    envelope.warning_days = row.warning_days or 0
    envelope.pre_lapse_days = row.pre_lapse_days or 0
    envelope.lapse_days = row.lapse_days or 0
    envelope.minimum_due_amount = row.minimum_due_amount
    envelope.grace_date = due_date + timedelta(days=envelope.grace_days)
    envelope.warning_date = due_date + timedelta(days=envelope.warning_days)
    envelope.pre_lapse_date = due_date + timedelta(days=envelope.pre_lapse_days)
    envelope.lapse_date = due_date + timedelta(days=envelope.lapse_days)
    return envelope
