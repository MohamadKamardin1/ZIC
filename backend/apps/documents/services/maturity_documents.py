from __future__ import annotations

from decimal import Decimal, InvalidOperation
from uuid import UUID

from apps.ol_maturity_installments.models import InstallmentItemStatus, InstallmentPlanStatus


def _safe_document_text(value, fallback="-"):
    """Return a printable label and never leak a bare UUID into a document."""
    if value is None or value == "":
        return fallback
    if isinstance(value, UUID):
        return fallback
    try:
        UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return str(value)
    return fallback


def _money(value, currency="TZS"):
    try:
        return f"{Decimal(str(value or 0)):,.2f} {currency}"
    except (InvalidOperation, TypeError, ValueError):
        return f"0.00 {currency}"


def _maturity_watermark(plan, items):
    if plan.status == InstallmentPlanStatus.CANCELLED:
        return "CANCELLED"
    if any(item.status == InstallmentItemStatus.MISSED for item in items):
        return "MISSED PAYMENT"
    return ""


def _maturity_rows(items, currency):
    rows = []
    for item in items:
        rows.append(
            {
                "installment_number": item.installment_number,
                "due_date": item.due_date,
                "amount": _money(item.amount, currency),
                "status": _safe_document_text(
                    item.get_status_display() if hasattr(item, "get_status_display") else item.status
                ),
                "paid_date": item.paid_date,
                "payment_reference": _safe_document_text(item.payment_reference, "Not assigned"),
            }
        )
    return rows


def _maturity_base_context(plan, branding, template, title):
    currency = _safe_document_text(plan.currency, "TZS").upper()
    policy = plan.policy_ref
    partner = plan.partner
    items = list(plan.items.select_related("payment_requisition_ref", "paid_by").order_by("installment_number"))
    paid_amount = sum((item.amount for item in items if item.status == InstallmentItemStatus.PAID), Decimal("0"))
    total_payable = Decimal(plan.total_payable_amount or Decimal("0"))
    balance = total_payable - paid_amount
    watermark = _maturity_watermark(plan, items)
    policyholder_name = _safe_document_text(
        getattr(partner, "legal_name", None) or getattr(partner, "partner_number", None),
        "Not recorded",
    )
    agent = getattr(policy, "agent", None)
    agent_name = _safe_document_text(
        getattr(agent, "legal_name", None) or getattr(agent, "partner_number", None),
        "Not assigned",
    )
    status_display = _safe_document_text(
        plan.get_status_display() if hasattr(plan, "get_status_display") else plan.status,
        "Not recorded",
    )
    frequency_display = _safe_document_text(
        plan.get_frequency_display() if hasattr(plan, "get_frequency_display") else plan.frequency
    )
    signatures = [
        {"label": "Policyholder", "name": policyholder_name},
        {"label": "Agent / Intermediary", "name": agent_name},
        {
            "label": "Company Representative",
            "name": _safe_document_text(branding.get("company_name"), "Zanzibar Insurance Corporation"),
        },
    ]
    return {
        "document_title": title,
        "branding": branding,
        "template_version": template.version,
        "quote": {"status_watermark": watermark},
        "plan": {
            "number": _safe_document_text(plan.plan_number),
            "status": _safe_document_text(plan.status),
            "status_display": status_display,
            "frequency": _safe_document_text(plan.frequency),
            "frequency_display": frequency_display,
            "currency": currency,
            "start_date": plan.start_date,
            "end_date": plan.end_date,
            "installment_count": plan.installment_count,
        },
        "policy": {
            "number": _safe_document_text(getattr(policy, "policy_number", None), "Not recorded"),
            "product": _safe_document_text(getattr(policy, "product_plan_ref", None), "Not recorded"),
            "maturity_date": getattr(policy, "maturity_date", None),
        },
        "policyholder": {
            "name": policyholder_name,
            "number": _safe_document_text(getattr(partner, "partner_number", None), "Not recorded"),
        },
        "financial": {
            "total_maturity_value": _money(plan.total_maturity_value, currency),
            "total_payable_amount": _money(total_payable, currency),
            "paid_amount": _money(paid_amount, currency),
            "balance": _money(balance, currency),
        },
        "schedule": _maturity_rows(items, currency),
        "schedule_summary": {
            "installment_count": len(items),
            "total_amount": _money(total_payable, currency),
            "paid_amount": _money(paid_amount, currency),
            "balance": _money(balance, currency),
        },
        "signatures": signatures,
        "meta": {
            "plan_number": _safe_document_text(plan.plan_number),
            "policy_number": _safe_document_text(getattr(policy, "policy_number", None), "Not recorded"),
            "status": status_display,
            "currency": currency,
        },
    }


def maturity_schedule_context(source, branding, template):
    return _maturity_base_context(source, branding, template, "MATURITY SCHEDULE")


def maturity_payment_advice_context(source, branding, template):
    return _maturity_base_context(source, branding, template, "PAYMENT ADVICE")
