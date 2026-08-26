"""Front Office Receipts — exchange rate resolution and staleness.

Cross-currency allocations either carry an explicit rate (source ``EXPLICIT``)
or resolve the most recent active rate for the receipt->target pair from the
``ExchangeRate`` table. Staleness is a warning only, gated by the optional
``RECEIPT_EXCHANGE_RATE_STALE_DAYS`` system parameter: when configured, a rate
older than that many days is flagged but never blocks a write (explicit rate
wins and is authoritative).
"""


from django.utils import timezone

from apps.front_office.receipts.models import ExchangeRate
from apps.system_parameters.services.config_service import ConfigurationService

STALE_DAYS_PARAM = "RECEIPT_EXCHANGE_RATE_STALE_DAYS"


def stale_days():
    try:
        return int(ConfigurationService.get_parameter(STALE_DAYS_PARAM, 0) or 0)
    except (TypeError, ValueError):
        return 0


def stale_rate_warning(rate, reference_date=None):
    """Warning when ``rate`` is older than the configured staleness window."""
    days = stale_days()
    if not days or days <= 0:
        return None
    reference = reference_date or timezone.localdate()
    age = (reference - rate.effective_date).days
    if age <= days:
        return None
    return (
        f"The exchange rate {rate.from_currency}/{rate.to_currency} is {age} days old "
        f"(effective {rate.effective_date.isoformat()}). Verify the rate before allocating."
    )


def resolve_rate(from_currency, to_currency, effective_date=None):
    """Resolve an active rate at/before ``effective_date`` (default today).

    Returns ``None`` when no active rate is on file, else a dict with ``rate``
    (Decimal), ``source``, ``effective_date``, and ``stale``/``warning``.
    """
    row = ExchangeRate.resolve(from_currency, to_currency, effective_date)
    if row is None:
        return None
    warning = stale_rate_warning(row)
    return {
        "rate": row.rate,
        "source": row.source,
        "effective_date": row.effective_date,
        "stale": warning is not None,
        "warning": warning,
    }


def lookup_payload(from_currency, to_currency, effective_date=None):
    """Serializable dict for the exchange-rate endpoint (or ``None``)."""
    resolved = resolve_rate(from_currency, to_currency, effective_date)
    if resolved is None:
        return None
    return {
        "from_currency": (from_currency or "").strip().upper(),
        "to_currency": (to_currency or "").strip().upper(),
        "rate": str(resolved["rate"]),
        "effective_date": resolved["effective_date"].isoformat(),
        "source": resolved["source"],
        "is_active": True,
        "stale": resolved["stale"],
        "warning": resolved["warning"],
    }
