"""Installment schedule calculation engine driven by OL Product Rating parameters.

The engine consumes the Anticipated Endowment installment rate table
(``OLAnticipatedEndowmentInstallmentRate``) so the schedule stays fully
parameterized: each installment amount is ``Maturity Value * (Rate / 100)`` and
penny rounding is distributed so the total payable exactly equals the maturity
value. Every run is written to the central audit trail.
"""

import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db.models import Q
from django.utils import timezone

from apps.governance.services.audit_service import AuditService
from apps.ol_parameters.models import OLAnticipatedEndowmentInstallmentRate
from apps.ordinary_life.models import OLPlan, OLProduct

from ..errors import registry_error
from ..models import InstallmentFrequency

MONEY_QUANTUM = Decimal("0.01")
INSTALLMENT_TYPE = "ANTICIPATED_ENDOWMENT"
MAX_TERM_YEARS = 60

FREQUENCY_MONTHS = {
    InstallmentFrequency.SINGLE: 0,
    InstallmentFrequency.MONTHLY: 1,
    InstallmentFrequency.QUARTERLY: 3,
    InstallmentFrequency.HALF_YEARLY: 6,
    InstallmentFrequency.ANNUAL: 12,
}

FREQUENCY_ALIASES = {
    "ANNUALLY": "ANNUAL",
    "YEARLY": "ANNUAL",
    "SEMI_ANNUALLY": "HALF_YEARLY",
    "SEMI_ANNUAL": "HALF_YEARLY",
}


def _effective_queryset(queryset, on_date=None):
    on_date = on_date or timezone.localdate()
    return queryset.filter(is_active=True).filter(
        Q(effective_from__isnull=True) | Q(effective_from__lte=on_date),
        Q(effective_to__isnull=True) | Q(effective_to__gte=on_date),
    )


def _policy_product_codes(policy):
    code = (getattr(policy, "product_plan_ref", "") or "").strip().upper()
    snapshot = getattr(policy, "contract_snapshot", None)
    if not isinstance(snapshot, dict):
        snapshot = {}
    values = {code}
    for key in ("product_code", "plan_code", "product", "plan"):
        value = snapshot.get(key)
        if value:
            values.add(str(value).strip().upper())
    return values


def _resolve_product_plan(policy):
    product = None
    plan = None
    for code in _policy_product_codes(policy):
        if product is None:
            product = OLProduct.objects.filter(code__iexact=code, is_active=True).first()
        if plan is None:
            plan = OLPlan.objects.filter(code__iexact=code, is_active=True).first()
        if product and plan:
            break
    return product, plan


def _resolve_installment_rate(policy, *, frequency, term_years, on_date=None, currency=""):
    """Resolve the most specific active installment rate row for the policy.

    Scoring rewards an exact product+plan match over a product-only row, and an
    explicit term coverage over an unconstrained default row. Returns
    ``(rate_row, product, plan)`` or ``(None, product, plan)`` when no row
    applies, which the caller surfaces as a teachable PLAN_PARAMETER_MISSING.
    """
    on_date = on_date or timezone.localdate()
    product, plan = _resolve_product_plan(policy)
    if product is None:
        return None, product, plan

    queryset = _effective_queryset(
        OLAnticipatedEndowmentInstallmentRate.objects.select_related("product", "plan"),
        on_date,
    ).filter(installment_type=INSTALLMENT_TYPE, frequency=frequency)
    if currency:
        queryset = queryset.filter(Q(currency="") | Q(currency=currency))

    scored = []
    for row in queryset:
        if row.product_id != product.pk:
            continue
        if row.plan_id is not None and (plan is None or row.plan_id != plan.pk):
            continue
        score = 0
        if plan is not None and row.plan_id is not None and row.plan_id == plan.pk:
            score += 4
        if row.term_from is None and row.term_to is None:
            score += 1
        else:
            if row.term_from is not None and term_years < row.term_from:
                continue
            if row.term_to is not None and term_years > row.term_to:
                continue
            score += 2
        scored.append((score, row))

    if not scored:
        return None, product, plan
    scored.sort(key=lambda item: (item[0], item[1].effective_from or date.min), reverse=True)
    return scored[0][1], product, plan


def _coerce_money(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise registry_error("INSTALLMENT_INVALID_AMOUNT", details={"maturity_value": value}) from exc
    if amount < 0:
        raise registry_error("INSTALLMENT_INVALID_AMOUNT", details={"maturity_value": str(value)})
    return amount


def _coerce_term(term_years):
    try:
        term = int(term_years)
    except (TypeError, ValueError) as exc:
        raise registry_error("INSTALLMENT_INVALID_TERM", details={"term_years": term_years}) from exc
    if term < 1 or term > MAX_TERM_YEARS:
        raise registry_error("INSTALLMENT_INVALID_TERM", details={"term_years": term_years})
    return term


def _normalize_frequency(value):
    normalized = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    return FREQUENCY_ALIASES.get(normalized, normalized)


def _coerce_frequency(frequency):
    normalized = _normalize_frequency(frequency)
    if normalized not in InstallmentFrequency.values:
        raise registry_error(
            "INSTALLMENT_INVALID_FREQUENCY",
            details={"provided": frequency, "supported": list(InstallmentFrequency.values)},
        )
    return normalized


def _installment_count(frequency, term_years):
    if frequency == InstallmentFrequency.SINGLE:
        return 1
    months_between = FREQUENCY_MONTHS[frequency]
    return max(1, term_years * 12 // months_between)


def _add_months(day, months):
    month_index = day.year * 12 + (day.month - 1) + months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    last_day = calendar.monthrange(year, month)[1]
    return day.replace(year=year, month=month, day=min(day.day, last_day))


def _distribute_rounding(amounts, total):
    """Quantize each amount and spread any remaining pennies by largest remainder.

    Guarantees ``sum(result) == total`` whenever the rate is close enough that
    the remainder fits inside a single penny per installment.
    """
    rounded = [amount.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP) for amount in amounts]
    diff_pennies = int((total - sum(rounded)) * 100)
    if diff_pennies == 0:
        return rounded
    order = sorted(
        range(len(amounts)),
        key=lambda index: (amounts[index] % MONEY_QUANTUM, -index),
        reverse=True,
    )
    if diff_pennies > 0:
        for index in order[:diff_pennies]:
            rounded[index] += MONEY_QUANTUM
    else:
        for index in order[len(amounts) + diff_pennies :]:
            rounded[index] -= MONEY_QUANTUM
    return rounded


def _build_items(maturity_value, rate_factor, frequency, term_years, start_date):
    count = _installment_count(frequency, term_years)
    base_amount = maturity_value * (rate_factor / Decimal("100"))
    amounts = _distribute_rounding([base_amount] * count, maturity_value)
    if sum(amounts) != maturity_value:
        raise registry_error(
            "PLAN_CALCULATION_MISMATCH",
            details={
                "frequency": frequency,
                "term_years": term_years,
                "installment_count": count,
                "rate_factor": str(rate_factor),
                "calculated_total": str(sum(amounts)),
                "maturity_value": str(maturity_value),
            },
        )
    months_between = FREQUENCY_MONTHS[frequency]
    items = []
    for number in range(1, count + 1):
        offset = 0 if frequency == InstallmentFrequency.SINGLE else (number - 1) * months_between
        due_date = start_date if offset == 0 else _add_months(start_date, offset)
        items.append({"installment_number": number, "date": due_date, "amount": amounts[number - 1]})
    return items


def calculate_schedule(
    policy,
    maturity_value,
    frequency,
    term_years,
    *,
    start_date=None,
    actor=None,
    source_channel="API",
    on_date=None,
):
    """Validate inputs, resolve the rate table, and produce a reconciling schedule.

    Returns a rich dict with ``items`` (the ``{date, amount}`` list), the
    reconciliation totals, and the exact rate row used so callers can snapshot
    the calculation basis. Audits every run.
    """
    on_date = on_date or timezone.localdate()
    maturity_value = _coerce_money(maturity_value)
    term_years = _coerce_term(term_years)
    frequency = _coerce_frequency(frequency)

    if policy.maturity_date and policy.maturity_date > on_date:
        raise registry_error(
            "PLAN_POLICY_NOT_MATURED",
            details={
                "policy_number": policy.policy_number,
                "maturity_date": str(policy.maturity_date),
                "today": str(on_date),
            },
        )

    start_date = start_date or on_date
    if policy.maturity_date and start_date < policy.maturity_date:
        start_date = policy.maturity_date

    rate_row, product, plan = _resolve_installment_rate(
        policy,
        frequency=frequency,
        term_years=term_years,
        on_date=on_date,
        currency=policy.currency,
    )
    if rate_row is None:
        raise registry_error(
            "PLAN_PARAMETER_MISSING",
            details={
                "policy_number": policy.policy_number,
                "product": getattr(product, "code", None) or (policy.product_plan_ref or ""),
                "plan": getattr(plan, "code", None) or None,
                "frequency": frequency,
                "term_years": term_years,
                "on_date": str(on_date),
            },
        )

    items = _build_items(maturity_value, Decimal(rate_row.rate_factor), frequency, term_years, start_date)

    schedule = {
        "policy_number": policy.policy_number,
        "currency": policy.currency,
        "total_maturity_value": maturity_value,
        "total_payable_amount": sum(item["amount"] for item in items),
        "installment_count": len(items),
        "frequency": frequency,
        "frequency_matches_policy": _normalize_frequency(policy.premium_frequency) == frequency,
        "term_years": term_years,
        "start_date": start_date,
        "end_date": items[-1]["date"],
        "rate_used": {
            "code": rate_row.code,
            "rate_factor": str(rate_row.rate_factor),
            "product": product.code if product else None,
            "plan": plan.code if plan else None,
            "frequency": rate_row.frequency,
            "term_from": rate_row.term_from,
            "term_to": rate_row.term_to,
            "effective_from": rate_row.effective_from,
            "effective_to": rate_row.effective_to,
        },
        "parameters_used": ["OLAnticipatedEndowmentInstallmentRate"],
        "items": items,
    }

    AuditService.log(
        action_type="CALCULATE",
        entity_type="ol_maturity_installments.installment_schedule",
        entity_id=policy.pk,
        entity_repr=f"{policy.policy_number} — {frequency} — {len(items)} installments",
        before_state={},
        after_state={
            "policy_number": policy.policy_number,
            "frequency": frequency,
            "term_years": term_years,
            "installment_count": len(items),
            "total_maturity_value": str(maturity_value),
            "total_payable_amount": str(schedule["total_payable_amount"]),
            "start_date": str(start_date),
            "end_date": str(items[-1]["date"]),
            "rate_code": rate_row.code,
            "rate_factor": str(rate_row.rate_factor),
            "reconciled": str(schedule["total_payable_amount"] == maturity_value),
        },
        description=f"OL maturity installment schedule calculated for {policy.policy_number}.",
        actor=actor,
        reason="Installment schedule calculation run.",
        source_channel=source_channel,
        app_label="ol_maturity_installments",
        model_name="installment_schedule",
        object_id=str(policy.pk),
        object_repr=policy.policy_number,
    )
    return schedule


def generate_schedule(policy, maturity_value, frequency, term_years, **kwargs):
    """Public calculation contract: return the list of ``{date, amount}`` items."""
    result = calculate_schedule(policy, maturity_value, frequency, term_years, **kwargs)
    return result["items"]
