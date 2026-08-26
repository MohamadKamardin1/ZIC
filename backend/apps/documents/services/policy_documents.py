from decimal import Decimal, InvalidOperation


def _safe(value, fallback="-"):
    if value in (None, ""):
        return fallback
    text = str(value)
    if len(text) >= 32:
        try:
            from uuid import UUID

            UUID(text)
            return fallback
        except (AttributeError, TypeError, ValueError):
            pass
    return text


def _money(value, currency):
    try:
        return f"{Decimal(str(value or 0)):,.2f} {currency}"
    except (InvalidOperation, TypeError, ValueError):
        return f"0.00 {currency}"


def _display(obj, *fields):
    if obj is None:
        return "-"
    for field in fields:
        value = getattr(obj, field, None)
        if value not in (None, ""):
            return _safe(value)
    return _safe(obj)


def _date(value):
    return value.isoformat() if hasattr(value, "isoformat") else _safe(value)


def _snapshot(source):
    return source.contract_snapshot if isinstance(source.contract_snapshot, dict) else {}


def _plan_rows(source, currency):
    snapshot = _snapshot(source)
    rows = snapshot.get("plans", [])
    if not isinstance(rows, list):
        rows = []
    if not rows:
        rows = [{"code": source.product_plan_ref, "name": source.product_plan_ref}]
    result = []
    for row in rows:
        if not isinstance(row, dict):
            row = {"code": row, "name": row}
        result.append(
            {
                "code": _safe(row.get("code") or row.get("plan_code") or source.product_plan_ref),
                "name": _safe(row.get("name") or row.get("plan_name") or row.get("product_name") or source.product_plan_ref),
                "product": _safe(row.get("product_name") or row.get("product_code")),
                "plan_type": _safe(row.get("plan_type") or row.get("plan_type_name")),
                "badges": row.get("badges", []) if isinstance(row.get("badges", []), list) else [],
                "term_years": row.get("term_years") or source.term_years,
                "payment_period_years": row.get("payment_period_years") or row.get("payment_period") or source.term_years,
                "premium_frequency": _safe(row.get("premium_frequency") or source.premium_frequency),
                "quote_basis": _safe(row.get("quote_basis")),
                "sum_assured": _money(row.get("sum_assured") or row.get("base_sum_assured") or source.sum_assured, currency),
                "estimated_maturity_value": _money(row.get("estimated_maturity_value") or row.get("maturity_value"), currency),
                "estimated_bonus_rate": _safe(row.get("estimated_bonus_rate")),
                "joint_life": _safe(row.get("joint_life_display") or row.get("joint_life"), "No"),
                "mortgage": _safe(row.get("mortgage_display") or row.get("mortgage"), "No"),
                "personal_accident": _safe(row.get("personal_accident_display") or row.get("personal_accident"), "No"),
                "premium_waiver": _safe(row.get("premium_waiver_display") or row.get("premium_waiver"), "No"),
            }
        )
    return result


def _premium_schedule(source, currency):
    snapshot = _snapshot(source)
    rows = snapshot.get("premium_schedule", snapshot.get("installment_schedule", []))
    if not isinstance(rows, list):
        rows = []
    if rows:
        return [
            {
                "number": row.get("installment_number", row.get("number", index + 1)) if isinstance(row, dict) else index + 1,
                "due_date": _date(row.get("due_date")) if isinstance(row, dict) else "-",
                "frequency": _safe(row.get("premium_frequency") or row.get("frequency") or source.premium_frequency) if isinstance(row, dict) else _safe(source.premium_frequency),
                "amount": _money(row.get("amount") or row.get("premium_amount"), currency) if isinstance(row, dict) else _money(source.premium_amount, currency),
            }
            for index, row in enumerate(rows)
        ]
    return [
        {
            "number": 1,
            "due_date": _date(source.risk_commencement_date),
            "frequency": _safe(source.premium_frequency),
            "amount": _money(source.premium_amount, currency),
        }
    ]


def _legal_clauses(source):
    snapshot = _snapshot(source)
    clauses = snapshot.get("legal_clauses", [])
    if isinstance(clauses, list) and clauses:
        return [_safe(clause) for clause in clauses]
    return [
        "This policy is governed by the approved Ordinary Life policy terms and conditions.",
        "Premiums are payable according to the premium schedule; cover may be affected by unpaid premiums and applicable grace-period rules.",
        "Any alteration to this policy must be approved and recorded as an immutable endorsement.",
        "This document is a policy record and should be retained with the policyholder's supporting documents.",
    ]


def _policy_context(source, branding, template, *, document_title):
    snapshot = _snapshot(source)
    currency = _safe(source.currency, "TZS").upper()
    partner = getattr(source, "partner", None)
    agent = getattr(source, "agent", None)
    members = [
        {
            "relation": _safe(member.member_relation),
            "name": _safe(member.name),
            "dob": _date(member.dob),
            "gender": _safe(member.gender),
            "benefit_amount": _money(member.benefit_amount, currency),
        }
        for member in source.members.filter(is_active=True).order_by("name")
    ]
    benefits = [
        {
            "benefit_type": _safe(benefit.benefit_type),
            "basis": _safe(benefit.calculation_basis),
            "amount": _money(benefit.amount, currency),
        }
        for benefit in source.benefits.order_by("benefit_type")
    ]
    riders = [
        {
            "code": _safe(rider.rider_code),
            "sum_assured": _money(rider.sum_assured, currency),
            "amount": _money(rider.amount, currency),
            "premium": _money(rider.premium, currency),
        }
        for rider in source.riders.order_by("rider_code")
    ]
    financial = snapshot.get("financial_summary", {}) if isinstance(snapshot.get("financial_summary", {}), dict) else {}
    return {
        "document_title": document_title,
        "template_version": template.version,
        "branding": branding,
        "quote": {"status_watermark": "DRAFT" if source.status == "DRAFT" else ("SURRENDERED" if source.status == "SURRENDERED" else "")},
        "policy": {
            "number": _safe(source.policy_number),
            "status": _safe(source.get_status_display()),
            "version": source.version,
            "issue_date": _date(source.risk_commencement_date),
            "risk_commencement_date": _date(source.risk_commencement_date),
            "maturity_date": _date(source.maturity_date),
            "currency": currency,
            "product_plan": _safe(source.product_plan_ref),
            "sum_assured": _money(source.sum_assured, currency),
            "premium_amount": _money(source.premium_amount, currency),
            "premium_frequency": _safe(source.premium_frequency),
            "term_years": source.term_years,
            "first_premium_receipt_ref": _safe(source.first_premium_receipt_ref),
        },
        "prospect": {
            "name": _display(partner, "legal_name", "display_name", "name"),
            "partner_number": _display(partner, "partner_number", "partner_code"),
            "identity_type": _display(partner, "identity_type", "identity_type_name"),
            "identity_number": _safe(getattr(partner, "national_id", None)),
            "date_of_birth": _date(getattr(partner, "date_of_birth", None)),
            "gender": _display(partner, "gender"),
            "phone": _display(partner, "phone", "mobile_number"),
            "email": _display(partner, "email"),
            "address": _display(partner, "address", "physical_address"),
        },
        "agent": {
            "name": _display(agent, "legal_name", "display_name", "name"),
            "code": _display(agent, "partner_number", "agent_code"),
        },
        "plans": _plan_rows(source, currency),
        "members": members,
        "riders": riders,
        "benefits": benefits,
        "premium_schedule": _premium_schedule(source, currency),
        "financial": {
            "base_premium": _money(financial.get("base_premium", source.premium_amount), currency),
            "rider_premium": _money(financial.get("rider_premium", sum((_safe_decimal(rider.premium) for rider in source.riders.all()), Decimal("0.00"))), currency),
            "total_premium": _money(financial.get("total_premium", source.premium_amount), currency),
            "currency": currency,
        },
        "legal_clauses": _legal_clauses(source),
        "signatures": ["Policyholder", "Agent / Intermediary", "Company Representative"],
    }


def _safe_decimal(value):
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def policy_contract_context(source, branding, template):
    return _policy_context(source, branding, template, document_title="POLICY CONTRACT")


def policy_schedule_context(source, branding, template):
    context = _policy_context(source, branding, template, document_title="SCHEDULE OF BENEFITS")
    context["quote"]["status_watermark"] = "DRAFT" if source.status == "DRAFT" else ("SURRENDERED" if source.status == "SURRENDERED" else "")
    return context
