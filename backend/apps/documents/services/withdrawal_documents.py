from decimal import Decimal, InvalidOperation


def _text(value, fallback="-"):
    if value in (None, ""):
        return fallback
    return str(value)


def _money(value, currency):
    try:
        return f"{Decimal(str(value or 0)):,.2f} {currency}"
    except (InvalidOperation, TypeError, ValueError):
        return f"0.00 {currency}"


def _partner_display(partner):
    if not partner:
        return "Not recorded"
    number = getattr(partner, "partner_number", "") or ""
    name = getattr(partner, "legal_name", "") or ""
    if not name:
        name = " ".join(
            value
            for value in (
                getattr(partner, "first_name", ""),
                getattr(partner, "other_name", ""),
                getattr(partner, "surname", ""),
            )
            if value
        )
    return " — ".join(part for part in (number, name) if part) or "Not recorded"


def withdrawal_statement_context(source, branding, template):
    currency = _text(getattr(source.policy, "currency", None), "TZS").upper()
    policy = source.policy
    partner = getattr(policy, "partner", None)
    agent = getattr(policy, "agent", None)
    status_code = _text(getattr(source, "status", None), "REQUESTED").upper()
    status_label = _text(source.get_status_display() if hasattr(source, "get_status_display") else status_code)
    fee = Decimal(source.amount or 0) - Decimal(source.net_amount or 0)
    cash_after = Decimal(source.cash_value_before or 0) - Decimal(source.amount or 0)
    watermark = status_code if status_code in {"CANCELLED", "REVERSED"} else ""
    policy_snapshot = policy.contract_snapshot if isinstance(getattr(policy, "contract_snapshot", None), dict) else {}
    policyholder = _partner_display(partner)
    agent_display = _partner_display(agent) if agent else "Not assigned"
    return {
        "document_title": "WITHDRAWAL STATEMENT",
        "branding": branding,
        "quote": {"status_watermark": watermark},
        "template_version": template.version,
        "status_watermark": watermark,
        "withdrawal": {
            "number": _text(source.request_number),
            "date": source.request_date,
            "status": status_label,
            "status_code": status_code,
            "policy_number": _text(policy.policy_number),
            "policyholder": policyholder,
            "product": _text(policy_snapshot.get("product_name") or policy_snapshot.get("plan_name") or policy.product_plan_ref),
            "currency": currency,
            "reason": _text(source.reason),
            "gross_amount": _money(source.amount, currency),
            "fee_amount": _money(fee, currency),
            "net_payout": _money(source.net_amount, currency),
            "cash_value_before": _money(source.cash_value_before, currency),
            "cash_value_after": _money(cash_after, currency),
            "loan_balance_before": _money(source.loan_balance_before, currency),
        },
        "policy": {
            "number": _text(policy.policy_number),
            "status": _text(policy.get_status_display() if hasattr(policy, "get_status_display") else policy.status),
            "currency": currency,
            "sum_assured": _money(policy.sum_assured, currency),
            "premium": _money(policy.premium_amount, currency),
            "maturity_date": policy.maturity_date,
        },
        "parties": {
            "policyholder": policyholder,
            "agent": agent_display,
            "company": _text(branding.get("company_name"), "Zanzibar Insurance Corporation"),
        },
        "financial": {
            "cash_value_before": _money(source.cash_value_before, currency),
            "gross_withdrawal": _money(source.amount, currency),
            "withdrawal_fee": _money(fee, currency),
            "net_payout": _money(source.net_amount, currency),
            "cash_value_after": _money(cash_after, currency),
            "loan_balance_before": _money(source.loan_balance_before, currency),
        },
        "signatures": [
            {"label": "Policyholder", "name": policyholder},
            {"label": "Agent / Intermediary", "name": agent_display},
            {"label": "Company Representative", "name": _text(branding.get("company_name"), "Zanzibar Insurance Corporation")},
        ],
    }
