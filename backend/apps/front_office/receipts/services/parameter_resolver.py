"""Parameter-driven resolvers for Front Office Receipts.

Every configurable aspect of a receipt (payment modes, source modules, default
status, numbering format) is read from System Parameters / OL Parameters with a
documented fallback. The module never hardcodes a business rule that a
parameter catalog should own; when a catalog value is absent the resolvers
return explicit fallbacks or ``None`` so callers can raise ``RECEIPT_PARAMETER_MISSING``.
"""

from decimal import Decimal

from apps.system_parameters.services.config_service import ConfigurationService

DEFAULT_CURRENCY = "TZS"
DEFAULT_EXCHANGE_RATE = Decimal("1.000000")
NUMBERING_CODE = "RCT"

FALLBACK_PAYMENT_MODES = ["CASH", "BANK_TRANSFER", "CHEQUE", "M-PESA", "MOBILE_MONEY", "OTHER"]
FALLBACK_SOURCE_MODULES = ["OL_PROPOSAL", "OL_POLICY", "GROUP_CREDIT", "MANUAL", "OTHER"]
FALLBACK_STATUSES = ["DRAFT", "POSTED", "PARTIALLY_ALLOCATED", "FULLY_ALLOCATED", "REVERSED", "CANCELLED"]
FALLBACK_CURRENCIES = ["TZS", "USD", "KES"]


def option(value, label, **meta):
    """Reference-data option payload: ``{value, label, meta}``."""
    return {"value": value, "label": label, "meta": meta or {}}


def configured_payment_modes():
    """Payment modes from ``RECEIPT_PAYMENT_MODES`` parameter (JSON list)."""
    value = ConfigurationService.get_json_parameter("RECEIPT_PAYMENT_MODES", None)
    if isinstance(value, list) and value:
        return [str(item).strip().upper() for item in value if str(item).strip()]
    return list(FALLBACK_PAYMENT_MODES)


def configured_source_modules():
    value = ConfigurationService.get_json_parameter("RECEIPT_SOURCE_MODULES", None)
    if isinstance(value, list) and value:
        return [str(item).strip().upper() for item in value if str(item).strip()]
    return list(FALLBACK_SOURCE_MODULES)


def configured_statuses():
    value = ConfigurationService.get_json_parameter("RECEIPT_STATUSES", None)
    if isinstance(value, list) and value:
        return [str(item).strip().upper() for item in value if str(item).strip()]
    return list(FALLBACK_STATUSES)


def configured_currencies():
    """Currencies from ``RECEIPT_CURRENCIES`` parameter (JSON list)."""
    value = ConfigurationService.get_json_parameter("RECEIPT_CURRENCIES", None)
    if isinstance(value, list) and value:
        return [str(item).strip().upper() for item in value if str(item).strip()]
    return list(FALLBACK_CURRENCIES)


def is_valid_payment_mode(mode):
    return (mode or "").strip().upper() in set(configured_payment_modes())


def is_valid_source_module(value):
    return (value or "").strip().upper() in set(configured_source_modules())


def is_valid_status(value):
    return (value or "").strip().upper() in set(configured_statuses())


def default_currency():
    return ConfigurationService.get_str_parameter("RECEIPT_DEFAULT_CURRENCY", DEFAULT_CURRENCY).strip().upper()


def receipt_numbering_code():
    """Numbering configuration code resolved from System Parameters."""
    return ConfigurationService.get_str_parameter("RECEIPT_NUMBERING_CODE", NUMBERING_CODE)


def payment_mode_label(mode):
    """Human label for a payment mode (names, never codes, in API responses)."""
    labels = {
        "CASH": "Cash",
        "BANK_TRANSFER": "Bank Transfer",
        "CHEQUE": "Cheque",
        "M-PESA": "M-PESA",
        "MOBILE_MONEY": "Mobile Money",
        "OTHER": "Other",
    }
    return labels.get((mode or "").strip().upper(), mode or "")
