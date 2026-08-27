from __future__ import annotations

import base64
import hashlib
import logging
import mimetypes
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from django.apps import apps
from django.conf import settings
from django.core import signing
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader

from apps.governance.services.audit_service import AuditService
from apps.system_parameters.services.config_service import ConfigurationService

from ..models import DocumentInstance, DocumentTemplate
from .policy_documents import policy_contract_context, policy_schedule_context
from .withdrawal_documents import withdrawal_statement_context

logger = logging.getLogger(__name__)


class DocumentEngineError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str | None = None, resolution_steps: list[str] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code or "DOCUMENT_ERROR"
        self.resolution_steps = resolution_steps or []


@dataclass(frozen=True)
class DocumentTypeDefinition:
    document_type: str
    source_app_label: str
    source_model: str
    template_code: str
    layout_template_path: str
    permission: str
    context_builder: Callable[[Any, dict[str, Any], DocumentTemplate], dict[str, Any]]
    title: str
    variables_schema: dict[str, Any]
    status: str = "READY"
    pending_message: str = ""


@dataclass(frozen=True)
class CompanyBranding:
    logo_url: str
    company_name: str
    address: str
    phone: str
    email: str
    registration_number: str
    footer_legal_text: str
    accent_colors: dict[str, str]
    version: int = 0

    @classmethod
    def resolve(cls, reference: str = "COMPANY_BRANDING") -> CompanyBranding:
        prefix = (reference or "COMPANY_BRANDING").strip().upper()
        from ..models import BrandingConfiguration

        default_colors = {
            "primary": "#183a91",
            "accent": "#d94754",
            "table_header": "#edf1f4",
        }
        configured = BrandingConfiguration.objects.filter(code=prefix, is_active=True).order_by("-version").first()
        if configured is not None:
            logo_value = configured.logo_file.name if configured.logo_file else ""
            if logo_value:
                logo_url = cls._logo_source(logo_value)
            else:
                fallback = Path(settings.BASE_DIR) / "apps" / "documents" / "static" / "documents" / "zic_logo.png"
                logo_url = cls._logo_source(str(fallback)) if fallback.exists() else ""
            configured_colors = configured.accent_colors if isinstance(configured.accent_colors, dict) else {}
            return cls(
                logo_url=logo_url,
                company_name=configured.company_name,
                address=configured.address,
                phone=configured.phone,
                email=configured.email,
                registration_number=configured.registration_number,
                footer_legal_text=configured.footer_legal_text,
                accent_colors={**default_colors, **configured_colors},
                version=configured.version,
            )

        def value(suffix: str, default: Any = ""):
            from apps.system_parameters.models import SystemParameter

            candidates = [f"{prefix}_{suffix}", suffix, f"BRANDING_{suffix}"]
            for code in candidates:
                result = ConfigurationService.get_parameter(code, None)
                if result not in (None, ""):
                    return result
                parameter = SystemParameter.objects.filter(code=code, is_active=True).first()
                if parameter is not None and parameter.value_type == "FILE" and parameter.file_value:
                    return parameter.file_value.name
            return default

        logo_value = value("LOGO_FILE", "")
        logo_url = cls._logo_source(logo_value) if logo_value else ""
        if not logo_url:
            fallback = Path(settings.BASE_DIR) / "apps" / "documents" / "static" / "documents" / "zic_logo.png"
            logo_url = cls._logo_source(str(fallback)) if fallback.exists() else ""
        colors = value("ACCENT_COLORS", {})
        if not isinstance(colors, dict):
            colors = {}
        return cls(
            logo_url=logo_url,
            company_name=str(value("COMPANY_NAME", "Zanzibar Insurance Corporation")),
            address=str(value("ADDRESS", "Bima House, Mlandege Road, Zanzibar City")),
            phone=str(value("PHONE", "+255 659 072 500")),
            email=str(value("EMAIL", "info@zic.co.tz")),
            registration_number=str(value("REGISTRATION_NUMBER", "")),
            footer_legal_text=str(value("FOOTER_LEGAL_TEXT", "This document is system generated.")),
            accent_colors={
                "primary": str(colors.get("primary", "#183a91")),
                "accent": str(colors.get("accent", "#d94754")),
                "table_header": str(colors.get("table_header", "#edf1f4")),
            },
        )

    @staticmethod
    def _logo_source(value: str) -> str:
        if not value:
            return ""
        path = Path(str(value))
        if not path.exists():
            try:
                path = Path(default_storage.path(str(value)))
            except Exception:
                try:
                    return default_storage.url(str(value))
                except Exception:
                    return str(value)
        try:
            mime_type = mimetypes.guess_type(str(path))[0] or "image/png"
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            return f"data:{mime_type};base64,{encoded}"
        except (OSError, ValueError):
            return str(value)

    def as_context(self) -> dict[str, Any]:
        return {
            "logo_url": self.logo_url,
            "company_name": self.company_name,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "registration_number": self.registration_number,
            "footer_legal_text": self.footer_legal_text,
            "accent_colors": self.accent_colors,
            "version": self.version,
        }


class DocumentTypeRegistry:
    _definitions: dict[str, DocumentTypeDefinition] = {}

    @classmethod
    def register(cls, definition: DocumentTypeDefinition):
        normalized = definition.document_type.strip().upper()
        cls._definitions[normalized] = DocumentTypeDefinition(
            **{**definition.__dict__, "document_type": normalized}
        )

    @classmethod
    def get(cls, document_type: str) -> DocumentTypeDefinition:
        definition = cls._definitions.get((document_type or "").strip().upper())
        if definition is None:
            raise DocumentEngineError(
                f"Document type '{document_type}' is not registered.",
                status_code=404,
            )
        return definition

    @classmethod
    def for_instance(cls, instance: DocumentInstance) -> DocumentTypeDefinition:
        definition = cls.get(instance.document_type)
        if (
            definition.source_app_label != instance.source_app_label
            or definition.source_model != instance.source_model
        ):
            raise DocumentEngineError("The document source type is not registered.", status_code=403)
        return definition

    @classmethod
    def choices(cls) -> list[str]:
        return sorted(cls._definitions)

    @classmethod
    def definitions(cls):
        return tuple(cls._definitions.values())


def _number_to_words(number: int) -> str:
    ones = (
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
        "eighteen", "nineteen",
    )
    tens = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")

    def under_thousand(value: int) -> str:
        words = []
        if value >= 100:
            words.extend([ones[value // 100], "hundred"])
            value %= 100
            if value:
                words.append("and")
        if value >= 20:
            words.append(tens[value // 10])
            if value % 10:
                words.append(ones[value % 10])
        elif value:
            words.append(ones[value])
        return " ".join(words)

    if number < 0:
        return f"minus {_number_to_words(abs(number))}"
    if number < 1000:
        return under_thousand(number)
    groups = ((1_000_000_000, "billion"), (1_000_000, "million"), (1000, "thousand"))
    words = []
    remainder = number
    for divisor, label in groups:
        if remainder >= divisor:
            quotient, remainder = divmod(remainder, divisor)
            words.append(under_thousand(quotient) if quotient < 1000 else _number_to_words(quotient))
            words.append(label)
    if remainder:
        if words:
            words.append("and")
        words.append(under_thousand(remainder))
    return " ".join(words) or "zero"


def _amount_in_words(value, currency: str) -> str:
    try:
        amount = Decimal(str(value or 0)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return "Amount unavailable"
    major = int(abs(amount))
    minor = int((abs(amount) - major) * 100)
    currency_names = {"TZS": "Tanzanian shillings", "USD": "US dollars", "KES": "Kenyan shillings"}
    major_words = f"{_number_to_words(major)} {currency_names.get(currency, currency)}"
    if minor:
        return f"{major_words} and {_number_to_words(minor)} cents"
    return major_words


def _yes_no(value) -> str:
    if isinstance(value, str):
        return "Yes" if value.strip().upper() in {"YES", "TRUE", "1", "Y"} else "No"
    return "Yes" if bool(value) else "No"


def _quotation_funds(source, currency, money):
    rows = []
    for allocation in source.fund_allocations.filter(is_selected=True).select_related(
        "fund__fund_type", "plan_configuration__plan"
    ):
        fund = allocation.fund
        rows.append(
            {
                "code": getattr(fund, "code", ""),
                "name": getattr(fund, "name", ""),
                "fund_type": getattr(getattr(fund, "fund_type", None), "name", ""),
                "risk_profile": getattr(getattr(fund, "fund_type", None), "risk_profile", ""),
                "currency": getattr(fund, "currency", currency),
                "valuation_frequency": getattr(fund, "valuation_frequency", ""),
                "plan_name": getattr(getattr(getattr(allocation, "plan_configuration", None), "plan", None), "name", ""),
                "allocation_percentage": str(allocation.allocation_percentage),
                "allocation_amount": money(allocation.allocation_amount, currency),
            }
        )
    return rows


def _quotation_projections(source, currency, money):
    try:
        summary = source.financial_summary
    except Exception:
        summary = None
    raw_rows = getattr(summary, "projections", []) if summary is not None else []
    rows = []
    if not isinstance(raw_rows, list):
        return rows
    aliases = {
        "premiums_paid": ("premiums_paid", "premium_paid", "premium"),
        "bonuses": ("bonuses", "bonus", "estimated_bonus"),
        "surrender_value": ("surrender_value", "cash_surrender_value", "surrender"),
        "paid_up_value": ("paid_up_value", "paidup_value", "paid_up"),
    }
    for raw in raw_rows:
        if not isinstance(raw, dict):
            continue
        def first(keys, row=raw):
            return next((row[key] for key in keys if row.get(key) not in (None, "")), None)
        rows.append(
            {
                "policy_year": raw.get("policy_year", raw.get("year", "")),
                "premiums_paid": money(first(aliases["premiums_paid"]), currency),
                "bonuses": money(first(aliases["bonuses"]), currency),
                "surrender_value": money(first(aliases["surrender_value"]), currency),
                "paid_up_value": money(first(aliases["paid_up_value"]), currency),
            }
        )
    return rows


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


def _proposal_context(source, branding: dict[str, Any], template: DocumentTemplate):
    quotation = source.quotation
    context = _quotation_context(quotation, branding, template)
    if not context.get("plans") and isinstance(source.plans_snapshot, list):
        context["plans"] = [
            {
                "code": _safe_document_text(item.get("code") or item.get("plan_code")) if isinstance(item, dict) else "-",
                "name": _safe_document_text(item.get("name") or item.get("plan_name")) if isinstance(item, dict) else "-",
                "description": _safe_document_text(item.get("description")) if isinstance(item, dict) else "-",
                "policy_term": item.get("term_years") or item.get("policy_term") if isinstance(item, dict) else "-",
                "payment_period": item.get("payment_period_years") if isinstance(item, dict) else "-",
                "payment_frequency": item.get("payment_frequency") if isinstance(item, dict) else "-",
                "quote_basis": item.get("quote_basis") if isinstance(item, dict) else "-",
                "sum_assured": item.get("sum_assured") or item.get("base_sum_assured") if isinstance(item, dict) else "-",
                "estimated_maturity_value": item.get("estimated_maturity_value") if isinstance(item, dict) else "-",
                "badges": item.get("badges", []) if isinstance(item, dict) and isinstance(item.get("badges", []), list) else [],
            }
            for item in source.plans_snapshot
        ]
    snapshot_financial = source.financial_summary_snapshot if isinstance(source.financial_summary_snapshot, dict) else {}
    context["financial"].update({
        key: value for key, value in snapshot_financial.items()
        if key in {"total_sum_assured", "base_premium", "total_rider_premium", "total_loading", "total_discount", "total_tax", "total_premium", "estimated_maturity_value"}
        and value not in (None, "")
    })
    context["document_title"] = "PROPOSAL SUMMARY"
    context["proposal"] = {
        "number": _safe_document_text(source.proposal_number),
        "status": _safe_document_text(source.get_status_display() if hasattr(source, "get_status_display") else source.status),
        "quotation_number": _safe_document_text(getattr(quotation, "quote_number", None)),
        "quotation_version": getattr(quotation, "current_version_number", 1),
        "created_at": source.created_at,
        "created_by": DocumentEngine.user_display(source.created_by),
    }
    context["underwriting"] = {
        "status": _safe_document_text(source.status),
        "note": "Subject to underwriting review and approval requirements.",
    }
    return context


def _commitment_context(source, branding: dict[str, Any], template: DocumentTemplate):
    from apps.ol_quotations.services.document_service import QuotationDocumentService

    currency = _safe_document_text(source.currency, "TZS").upper()
    money = QuotationDocumentService._money
    partner_name = source.partner_name_snapshot or _safe_document_text(getattr(source, "partner", None))
    product_name = source.product_name_snapshot or _safe_document_text(getattr(source, "product", None))
    plan_name = source.plan_name_snapshot or _safe_document_text(getattr(source, "plan", None))
    allocations = []
    for allocation in source.allocations.select_related("allocated_by").all():
        allocations.append(
            {
                "receipt_reference": _safe_document_text(allocation.receipt_reference),
                "amount": money(allocation.amount, currency),
                "payment_mode": _safe_document_text(allocation.payment_mode),
                "currency": _safe_document_text(allocation.currency, currency),
                "exchange_rate": _safe_document_text(allocation.exchange_rate),
                "allocated_at": allocation.allocated_at,
                "allocated_by": DocumentEngine.user_display(allocation.allocated_by),
                "reason": _safe_document_text(allocation.reason),
            }
        )
    return {
        "document_title": "COMMITMENT STATEMENT",
        "branding": branding,
        "template_version": template.version,
        "status_watermark": "DRAFT" if str(source.status).upper() == "DRAFT" else "",
        "commitment": {
            "number": _safe_document_text(source.commitment_number),
            "source_type": _safe_document_text(source.get_source_type_display() if hasattr(source, "get_source_type_display") else source.source_type),
            "source_reference": _safe_document_text(source.source_reference),
            "partner_name": _safe_document_text(partner_name),
            "product_name": _safe_document_text(product_name),
            "plan_name": _safe_document_text(plan_name),
            "currency": currency,
            "premium_frequency": _safe_document_text(source.premium_frequency),
            "installment_number": source.installment_number,
            "installment_count": source.installment_count,
            "due_date": source.due_date,
            "grace_date": source.grace_date,
            "lapse_date": source.lapse_date,
            "status": _safe_document_text(source.get_status_display() if hasattr(source, "get_status_display") else source.status),
            "approval_required": "Yes" if source.approval_required else "No",
            "reason": _safe_document_text(source.reason_text),
        },
        "meta": {
            "commitment_number": _safe_document_text(source.commitment_number),
            "source_reference": _safe_document_text(source.source_reference),
            "due_date": source.due_date,
            "currency": currency,
        },
        "financial": {
            "premium_amount": money(source.premium_amount, currency),
            "amount_paid": money(source.amount_paid, currency),
            "amount_waived": money(source.amount_waived, currency),
            "balance": money(source.balance, currency),
        },
        "allocations": allocations,
    }


def _quotation_context(source, branding: dict[str, Any], template: DocumentTemplate):
    from collections import defaultdict
    from types import SimpleNamespace

    from apps.ol_quotations.services.document_service import QuotationDocumentService

    # Reuse quotation domain aggregation; the shared engine owns layout, PDF,
    # storage, provenance, and access for every module.
    legacy_template = SimpleNamespace(layout_variables={})
    context = QuotationDocumentService.build_context(source, legacy_template)
    money = QuotationDocumentService._money
    currency = source.currency
    agent = source.agent or source.agent_partner
    location_master = getattr(source, "location_master", None)
    branch = getattr(location_master, "branch", None) if location_master else None
    agent_code = (
        getattr(agent, "employee_number", None)
        or getattr(agent, "agent_code", None)
        or getattr(agent, "partner_number", None)
        or getattr(agent, "code", None)
        or ""
    )
    expiry_date = source.expiry_date
    if expiry_date is None and source.quote_date:
        validity_days = ConfigurationService.get_int_parameter("OL_QUOTATION_DEFAULT_EXPIRY_DAYS", 30)
        expiry_date = source.quote_date + timedelta(days=validity_days)
    context["quote"].update(
        {
            "expiry_date": expiry_date.isoformat() if isinstance(expiry_date, date) else expiry_date,
            "status_watermark": "DRAFT" if source.status == "DRAFT" else "",
            "location": getattr(location_master, "name", "") or source.location or "-",
            "branch": getattr(branch, "name", "") or "-",
            "terms_reference": (source.metadata or {}).get("terms_reference", "OL Standard Terms and Conditions"),
        }
    )
    context["meta"] = {
        "quote_date": context["quote"].get("quote_date", "-"),
        "expiry_date": context["quote"].get("expiry_date", "-"),
        "currency": currency,
        "agent_name": context["agent"].get("name", "Not assigned"),
        "agent_code": agent_code or "-",
        "location": context["quote"]["location"],
        "branch": context["quote"]["branch"],
    }
    context["agent"]["code"] = agent_code or "-"

    product = source.product
    plan_type = getattr(getattr(product, "plan_type", None), "name", "") or getattr(getattr(product, "plan_type", None), "code", "")
    rider_totals = defaultdict(lambda: Decimal("0"))
    for selection in source.rider_selections.filter(is_selected=True):
        rider_totals[selection.plan_configuration_id] += selection.premium_amount or Decimal("0")
    enriched_plans = []
    for config in source.plan_configurations.filter(is_selected=True).select_related("plan", "product_version__product"):
        row = next((item for item in context["plans"] if item.get("id") == str(config.pk)), {})
        rules = config.coverage_rules if isinstance(config.coverage_rules, dict) else {}
        badges = []
        if rules.get("with_profit") or rules.get("with_profits") or "profit" in plan_type.lower():
            badges.append("With Profit")
        if config.joint_life or rules.get("joint_life"):
            badges.append("Joint Life")
        if getattr(product, "investment_linked", False) or rules.get("investment_linked"):
            badges.append("Investment Linked")
        enriched_plans.append(
            {
                **row,
                "code": getattr(config.plan, "code", "") or row.get("code", "PLAN"),
                "name": getattr(config.plan, "name", "") or row.get("name", "Plan"),
                "description": getattr(config.plan, "description", "") or row.get("description", ""),
                "sub_product": config.sub_product_code or "-",
                "plan_type": plan_type or "-",
                "badges": badges,
                "policy_term": config.term_years,
                "payment_period": config.payment_period_years or config.term_years,
                "payment_frequency": config.premium_frequency,
                "quote_basis": config.quote_basis,
                "sum_assured": money(config.base_sum_assured, currency),
                "base_sum_assured": money(config.base_sum_assured, currency),
                "estimated_maturity_value": money(config.estimated_maturity_value, currency),
                "estimated_bonus_rate": config.estimated_bonus_rate,
                "joint_life_display": _yes_no(config.joint_life),
                "mortgage_display": _yes_no(config.mortgage),
                "personal_accident_display": _yes_no(config.personal_accident),
                "premium_waiver_display": _yes_no(config.premium_waiver),
                "basic_premium": money(config.premium_amount, currency),
                "rider_premium": money(rider_totals[config.pk], currency),
                "gross_premium": money((config.premium_amount or Decimal("0")) + rider_totals[config.pk], currency),
            }
        )
    context["plans"] = enriched_plans
    context["funds"] = _quotation_funds(source, currency, money)
    context["projections"] = _quotation_projections(source, currency, money)

    try:
        summary = source.financial_summary
    except Exception:
        summary = None
    total_premium = getattr(summary, "total_premium", None) if summary else source.total_premium
    if total_premium is None:
        total_premium = sum((config.premium_amount or Decimal("0") for config in source.plan_configurations.filter(is_selected=True)), Decimal("0"))
    frequency_totals = defaultdict(lambda: Decimal("0"))
    for config in source.plan_configurations.filter(is_selected=True):
        frequency_totals[config.premium_frequency] += config.premium_amount or Decimal("0")
    premium_rows = []
    for frequency, amount in sorted(frequency_totals.items()):
        premium_rows.append({"frequency": frequency, "figures": money(amount, currency), "words": _amount_in_words(amount, currency)})
    if not premium_rows:
        premium_rows.append({"frequency": "Total premium", "figures": money(total_premium, currency), "words": _amount_in_words(total_premium, currency)})
    context["financial"].update(
        {
            "total_benefit_premium": money(getattr(summary, "total_benefit_premium", None), currency) if summary else "-",
            "installment_charge": money(getattr(summary, "installment_charge", None), currency) if summary else "-",
            "premium_per_frequency": premium_rows,
            "premium_in_words": _amount_in_words(total_premium, currency),
        }
    )
    context["validity"] = {
        "days": context["quote"].get("validity_days", 30),
        "expiry_date": context["quote"].get("expiry_date", "-"),
        "terms_reference": context["quote"].get("terms_reference", "OL Standard Terms and Conditions"),
    }
    context["branding"] = branding
    context["document_title"] = "QUOTATION"
    context["template_version"] = template.version
    return context


def _receipt_context(source, branding: dict[str, Any], template: DocumentTemplate):
    amount = getattr(source, "amount", Decimal("0")) or Decimal("0")
    currency = _safe_document_text(getattr(source, "currency", None), "TZS").upper()
    status = _safe_document_text(getattr(source, "status", None), "COMPLETED")
    payment_method = _safe_document_text(getattr(source, "payment_method", None), "-")
    reference = _safe_document_text(getattr(source, "reference", None), "-")
    receipt_date = getattr(source, "payment_date", None)
    return {
        "document_title": "RECEIPT",
        "branding": branding,
        "template_version": template.version,
        "status_watermark": status if status in {"REVERSED", "CANCELLED"} else "",
        "receipt": {
            "number": _safe_document_text(getattr(source, "receipt_number", None)),
            "date": receipt_date,
            "amount": QuotationDocumentServiceMoney.format(amount, currency),
            "currency": currency,
            "payment_method": payment_method,
            "reference": reference,
            "status": status,
        },
        "meta": {
            "receipt_number": _safe_document_text(getattr(source, "receipt_number", None)),
            "receipt_date": receipt_date,
            "currency": currency,
            "payment_method": payment_method,
            "reference": reference,
        },
        "financial": {
            "amount": QuotationDocumentServiceMoney.format(amount, currency),
            "amount_in_words": _amount_in_words(amount, currency),
        },
    }


def _loan_schedule_rows(source, currency, money):
    rows = []
    for item in source.schedules.all():
        amount_due = (item.principal_due or Decimal("0")) + (item.interest_due or Decimal("0")) + (item.penalty_due or Decimal("0"))
        rows.append(
            {
                "installment_number": item.installment_number,
                "due_date": item.due_date,
                "principal_due": money(item.principal_due, currency),
                "interest_due": money(item.interest_due, currency),
                "penalty_due": money(item.penalty_due, currency),
                "amount_due": money(amount_due, currency),
                "amount_paid": money(item.amount_paid, currency),
                "balance": money(item.balance, currency),
                "status": _safe_document_text(item.get_status_display() if hasattr(item, "get_status_display") else item.status),
            }
        )
    return rows


def _loan_document_context(source, branding: dict[str, Any], template: DocumentTemplate):
    currency = _safe_document_text(source.currency, "TZS").upper()
    money = QuotationDocumentServiceMoney.format
    policy = source.policy_ref
    partner = source.partner
    agent = getattr(policy, "agent", None)
    schedule = _loan_schedule_rows(source, currency, money)
    principal = source.principal_amount or Decimal("0")
    interest_rate = source.interest_rate or Decimal("0")
    policy_snapshot = policy.contract_snapshot if isinstance(getattr(policy, "contract_snapshot", None), dict) else {}
    partner_name = _safe_document_text(getattr(partner, "legal_name", None) or getattr(partner, "partner_number", None), "Not recorded")
    agent_name = _safe_document_text(getattr(agent, "legal_name", None) or getattr(agent, "partner_number", None), "Not assigned")
    policy_number = _safe_document_text(getattr(policy, "policy_number", None), "Not recorded")
    product_name = _safe_document_text(
        policy_snapshot.get("product_name") or policy_snapshot.get("plan_name") or getattr(policy, "product_plan_ref", None),
        "Not recorded",
    )
    status = _safe_document_text(source.get_status_display() if hasattr(source, "get_status_display") else source.status)
    status_code = str(source.status or "").upper()
    parties = {
        "policyholder": partner_name,
        "partner_number": _safe_document_text(getattr(partner, "partner_number", None), "-"),
        "agent": agent_name,
        "agent_number": _safe_document_text(getattr(agent, "partner_number", None), "-"),
        "company": _safe_document_text(branding.get("company_name"), "Zanzibar Insurance Corporation"),
    }
    policy_context = {
        "number": policy_number,
        "status": _safe_document_text(getattr(policy, "get_status_display", lambda: getattr(policy, "status", ""))()),
        "product": product_name,
        "currency": currency,
        "sum_assured": money(getattr(policy, "sum_assured", Decimal("0")), currency),
        "premium": money(getattr(policy, "premium_amount", Decimal("0")), currency),
        "premium_frequency": _safe_document_text(getattr(policy, "premium_frequency", None), "-"),
        "term_years": getattr(policy, "term_years", "-"),
        "risk_commencement_date": getattr(policy, "risk_commencement_date", None),
        "maturity_date": getattr(policy, "maturity_date", None),
    }
    schedule_total = sum((item.principal_due or Decimal("0")) + (item.interest_due or Decimal("0")) + (item.penalty_due or Decimal("0")) for item in source.schedules.all())
    schedule_paid = sum((item.amount_paid or Decimal("0")) for item in source.schedules.all())
    schedule_summary = {
        "installment_count": len(schedule),
        "total_due": money(schedule_total, currency),
        "total_paid": money(schedule_paid, currency),
        "outstanding": money(source.outstanding_balance, currency),
    }
    loan_context = {
        "number": _safe_document_text(source.loan_number),
        "status": status,
        "status_code": status_code,
        "policy_number": policy_number,
        "policyholder": partner_name,
        "currency": currency,
        "principal": money(principal, currency),
        "disbursed_amount": money(source.disbursed_amount, currency),
        "interest_rate": f"{interest_rate * Decimal('100'):.2f}%",
        "term_months": source.term_months,
        "compounding_frequency": _safe_document_text(source.compounding_frequency),
        "repayment_mode": _safe_document_text(source.repayment_mode, "-"),
        "disbursement_date": source.disbursement_date,
        "maturity_date": source.maturity_date,
        "total_repaid": money(source.total_repaid, currency),
        "outstanding_balance": money(source.outstanding_balance, currency),
        "reason": _safe_document_text(source.reason, "-"),
    }
    signatures = [
        {"label": "Policyholder / Borrower", "name": partner_name},
        {"label": "Agent / Intermediary", "name": agent_name},
        {"label": "Company Representative", "name": _safe_document_text(branding.get("company_name"), "Zanzibar Insurance Corporation")},
    ]
    return {
        "document_title": "LOAN AGREEMENT" if template.document_type == "OL_LOAN_AGREEMENT" else "LOAN REPAYMENT SCHEDULE",
        "branding": branding,
        "template_version": template.version,
        "quote": {"status_watermark": status_code if status_code in {"DEFAULTED", "SETTLED"} else ""},
        "loan": loan_context,
        "policy": policy_context,
        "parties": parties,
        "principal": loan_context["principal"],
        "interest_rate": loan_context["interest_rate"],
        "term": f"{source.term_months} months",
        "schedule": schedule,
        "schedule_summary": schedule_summary,
        "signatures": signatures,
        "financial": {
            "principal": loan_context["principal"],
            "disbursed_amount": loan_context["disbursed_amount"],
            "total_repaid": loan_context["total_repaid"],
            "outstanding_balance": loan_context["outstanding_balance"],
        },
    }


def _loan_agreement_context(source, branding: dict[str, Any], template: DocumentTemplate):
    return _loan_document_context(source, branding, template)


def _loan_schedule_context(source, branding: dict[str, Any], template: DocumentTemplate):
    return _loan_document_context(source, branding, template)


class QuotationDocumentServiceMoney:
    @staticmethod
    def format(value, currency):
        try:
            return f"{Decimal(str(value or 0)):,.2f} {currency}"
        except (InvalidOperation, TypeError, ValueError):
            return f"0.00 {currency}"


DocumentTypeRegistry.register(
    DocumentTypeDefinition(
        document_type="OL_QUOTATION",
        source_app_label="ol_quotations",
        source_model="olquotation",
        template_code="OL_QUOTATION_UNIFIED",
        layout_template_path="documents/ol_quotation.html",
        permission="ol_quotations.print",
        context_builder=_quotation_context,
        title="Ordinary Life Quotation",
        variables_schema={
            "quote": "object",
            "prospect": "object",
            "plans": "array",
            "riders": "array",
            "benefits": "array",
            "installments": "array",
            "financial": "object",
            "agent": "object",
            "branding": "object",
        },
    )
)

DocumentTypeRegistry.register(
    DocumentTypeDefinition(
        document_type="PROPOSAL_SUMMARY",
        source_app_label="ol_proposals",
        source_model="olproposal",
        template_code="PROPOSAL_SUMMARY_UNIFIED",
        layout_template_path="documents/proposal_summary.html",
        permission="ol_proposals.print",
        context_builder=_proposal_context,
        title="Proposal Summary",
        variables_schema={
            "proposal": "object",
            "quote": "object",
            "prospect": "object",
            "plans": "array",
            "financial": "object",
            "branding": "object",
        },
    )
)

DocumentTypeRegistry.register(
    DocumentTypeDefinition(
        document_type="COMMITMENT_STATEMENT",
        source_app_label="ol_commitments",
        source_model="olcommitment",
        template_code="COMMITMENT_STATEMENT_UNIFIED",
        layout_template_path="documents/commitment_statement.html",
        permission="ol_commitments.view",
        context_builder=_commitment_context,
        title="Commitment Statement",
        variables_schema={
            "commitment": "object",
            "meta": "object",
            "financial": "object",
            "allocations": "array",
            "branding": "object",
        },
    )
)

DocumentTypeRegistry.register(
    DocumentTypeDefinition(
        document_type="RECEIPT",
        source_app_label="front_office",
        source_model="foreceipt",
        template_code="RECEIPT_UNIFIED",
        layout_template_path="documents/receipt.html",
        permission="front_office.receipts.print",
        context_builder=_receipt_context,
        title="Receipt",
        variables_schema={
            "receipt": "object",
            "meta": "object",
            "financial": "object",
            "branding": "object",
        },
    )
)

DocumentTypeRegistry.register(
    DocumentTypeDefinition(
        document_type="POLICY_CONTRACT",
        source_app_label="ol_policies",
        source_model="policy",
        template_code="POLICY_CONTRACT_UNIFIED",
        layout_template_path="documents/policy_contract.html",
        permission="ol_policies.print",
        context_builder=policy_contract_context,
        title="Policy Contract",
        variables_schema={
            "policy": "object",
            "prospect": "object",
            "agent": "object",
            "plans": "array",
            "members": "array",
            "benefits": "array",
            "riders": "array",
            "premium_schedule": "array",
            "financial": "object",
            "legal_clauses": "array",
            "signatures": "array",
            "branding": "object",
            "quote": "object",
        },
    )
)

DocumentTypeRegistry.register(
    DocumentTypeDefinition(
        document_type="POLICY_SCHEDULE",
        source_app_label="ol_policies",
        source_model="policy",
        template_code="POLICY_SCHEDULE_UNIFIED",
        layout_template_path="documents/policy_schedule.html",
        permission="ol_policies.print",
        context_builder=policy_schedule_context,
        title="Schedule of Benefits",
        variables_schema={
            "policy": "object",
            "prospect": "object",
            "plans": "array",
            "members": "array",
            "benefits": "array",
            "riders": "array",
            "branding": "object",
            "quote": "object",
        },
    )
)


DocumentTypeRegistry.register(
    DocumentTypeDefinition(
        document_type="OL_LOAN_AGREEMENT",
        source_app_label="ol_loans",
        source_model="olloan",
        template_code="OL_LOAN_AGREEMENT_UNIFIED",
        layout_template_path="documents/ol_loan_agreement.html",
        permission="ol_loans.print",
        context_builder=_loan_agreement_context,
        title="OL Loan Agreement",
        variables_schema={
            "loan": "object",
            "policy": "object",
            "parties": "object",
            "principal": "string",
            "interest_rate": "string",
            "term": "string",
            "schedule": "array",
            "signatures": "array",
            "branding": "object",
        },
    )
)

DocumentTypeRegistry.register(
    DocumentTypeDefinition(
        document_type="OL_LOAN_SCHEDULE",
        source_app_label="ol_loans",
        source_model="olloan",
        template_code="OL_LOAN_SCHEDULE_UNIFIED",
        layout_template_path="documents/ol_loan_schedule.html",
        permission="ol_loans.print",
        context_builder=_loan_schedule_context,
        title="OL Loan Repayment Schedule",
        variables_schema={
            "loan": "object",
            "policy": "object",
            "parties": "object",
            "schedule": "array",
            "schedule_summary": "object",
            "signatures": "array",
            "branding": "object",
        },
    )
)


DocumentTypeRegistry.register(
    DocumentTypeDefinition(
        document_type="OL_WITHDRAWAL_STATEMENT",
        source_app_label="ol_policies",
        source_model="withdrawalrequest",
        template_code="OL_WITHDRAWAL_STATEMENT_UNIFIED",
        layout_template_path="documents/ol_withdrawal_statement.html",
        permission="ol_withdrawals.print",
        context_builder=withdrawal_statement_context,
        title="Withdrawal Statement",
        variables_schema={
            "withdrawal": "object",
            "policy": "object",
            "parties": "object",
            "financial": "object",
            "signatures": "array",
            "branding": "object",
        },
    )
)


for _pending_document_type, _pending_title in (
    ("DISCHARGE_VOUCHER", "Discharge Voucher"),
    ("COMMISSION_STATEMENT", "Commission Statement"),
    ("DEBIT_NOTE", "Debit Note"),
    ("PREMIUM_STATEMENT", "Premium Statement"),
):
    DocumentTypeRegistry.register(
        DocumentTypeDefinition(
            document_type=_pending_document_type,
            source_app_label="documents",
            source_model="pending",
            template_code=f"{_pending_document_type}_PENDING",
            layout_template_path="documents/pending.html",
            permission="documents.render",
            context_builder=lambda source, branding, template: {},
            title=_pending_title,
            variables_schema={},
            status="TEMPLATE_PENDING",
            pending_message=f"The {_pending_title} template is not configured yet. Contact System Parameters to activate an approved template.",
        )
    )


class DocumentEngine:
    TICKET_PURPOSE = "zic.documents.download.v1"
    TICKET_SALT = "zic.documents.download.v1"
    TICKET_MAX_AGE_SECONDS = 300

    @classmethod
    def has_permission(cls, actor, permission_code: str) -> bool:
        if not actor or not getattr(actor, "is_authenticated", False):
            return False
        if getattr(actor, "is_superuser", False):
            return True
        if permission_code == "ol_quotations.print":
            from apps.ol_quotations.permissions import has_quotation_permission

            return has_quotation_permission(actor, "print")
        if permission_code == "ol_proposals.print":
            # Proposals inherit the quotation hand-off access contract until a
            # dedicated proposal permission catalog is introduced.
            from apps.ol_quotations.permissions import has_quotation_permission

            return has_quotation_permission(actor, "print")
        if permission_code == "ol_policies.print":
            from apps.ol_policies.permissions import has_ol_policy_permission

            return has_ol_policy_permission(actor, "print")
        if permission_code == "ol_withdrawals.print":
            if hasattr(actor, "has_permission") and actor.has_permission("ol_withdrawals.print"):
                return True
            if hasattr(actor, "has_module_permission"):
                if actor.has_module_permission("ol_withdrawals", "PRINT"):
                    return True
            from apps.ol_policies.permissions import has_ol_policy_permission

            return has_ol_policy_permission(actor, "print")
        if permission_code == "ol_commitments.view":
            from apps.ol_commitments.permissions import has_ol_commitment_permission

            return has_ol_commitment_permission(actor, "view")
        if permission_code == "ol_loans.print":
            from apps.ol_loans.permissions import has_ol_loan_permission

            return has_ol_loan_permission(actor, "print")
        if permission_code == "front_office.receipts.print":
            if hasattr(actor, "has_permission") and actor.has_permission("front_office.receipts.print"):
                return True
            if hasattr(actor, "has_module_permission"):
                return actor.has_module_permission("front_office.receipts", "PRINT") or actor.has_module_permission("front_office", "PRINT")
            return False
        if hasattr(actor, "has_permission") and actor.has_permission(permission_code):
            return True
        if "." in permission_code and hasattr(actor, "has_module_permission"):
            module, action = permission_code.rsplit(".", 1)
            return actor.has_module_permission(module, action.upper())
        return False

    @classmethod
    def source_model(cls, definition: DocumentTypeDefinition):
        return apps.get_model(definition.source_app_label, definition.source_model)

    @classmethod
    def resolve_source(cls, definition, object_id):
        try:
            return cls.source_model(definition).objects.get(pk=object_id)
        except (ValueError, cls.source_model(definition).DoesNotExist) as exc:
            raise DocumentEngineError("The requested source transaction was not found.", 404) from exc

    @classmethod
    def in_scope(cls, actor, source) -> bool:
        if getattr(actor, "is_superuser", False):
            return True
        partner_id = getattr(source, "partner_id", None)
        if partner_id is None:
            quotation = getattr(source, "quotation", None)
            partner_id = getattr(quotation, "partner_id", None) if quotation is not None else None
        if partner_id is None:
            policy = getattr(source, "policy", None)
            partner_id = getattr(policy, "partner_id", None) if policy is not None else None
        if partner_id is None:
            return True
        if hasattr(actor, "can_access_partner"):
            return actor.can_access_partner(partner_id)
        return False

    @classmethod
    def ensure_access(cls, actor, definition, source):
        if not cls.has_permission(actor, definition.permission):
            raise DocumentEngineError(
                f"You do not have permission to render {definition.title} documents.",
                status_code=403,
            )
        if not cls.in_scope(actor, source):
            raise DocumentEngineError("You are not allowed to access this source transaction.", 403)

    @classmethod
    def template_for(cls, definition, as_of=None):
        template = (
            DocumentTemplate.objects.filter(
                code=definition.template_code,
                document_type=definition.document_type,
                is_active=True,
            )
            .order_by("-version")
            .first()
        )
        if template is None:
            raise DocumentEngineError(
                f"No active template is configured for {definition.title}.",
                status_code=409,
                code="TEMPLATE_NOT_FOUND",
                resolution_steps=[
                    "Open System Parameters > Document Templates.",
                    f"Activate an approved {definition.title} template, then retry the document action.",
                ],
            )
        try:
            template.clean()
        except Exception as exc:
            raise DocumentEngineError(
                f"The active {definition.title} template is invalid.",
                status_code=409,
                code="TEMPLATE_INVALID",
                resolution_steps=["Correct the active template configuration in System Parameters.", "Retry document generation."],
            ) from exc
        return template

    @classmethod
    def _validate_context(cls, context: dict[str, Any], schema: dict[str, Any]):
        if not isinstance(schema, dict):
            raise DocumentEngineError("Document template variables schema must be a JSON object.", 400)
        missing = []
        invalid = []
        for raw_name, specification in schema.items():
            name = str(raw_name)
            optional = name.endswith("?")
            field_name = name[:-1] if optional else name
            required = not optional
            expected = specification
            if isinstance(specification, dict):
                required = bool(specification.get("required", required))
                expected = specification.get("type", "any")
            if field_name not in context:
                if required:
                    missing.append(field_name)
                continue
            value = context[field_name]
            if value is None and not required:
                continue
            if expected == "object" and not isinstance(value, dict):
                invalid.append(f"{field_name} must be an object")
            elif expected == "array" and not isinstance(value, list):
                invalid.append(f"{field_name} must be an array")
            elif expected == "string" and not isinstance(value, str):
                invalid.append(f"{field_name} must be a string")
        if missing or invalid:
            details = []
            if missing:
                details.append("missing variables: " + ", ".join(missing))
            details.extend(invalid)
            raise DocumentEngineError("Document template variables are invalid (" + "; ".join(details) + ").", 400)

    @classmethod
    def _render_pdf(cls, html: str) -> tuple[bytes, int]:
        try:
            from weasyprint import HTML

            pdf = HTML(string=html, base_url=str(settings.BASE_DIR)).write_pdf()
            page_count = len(PdfReader(BytesIO(pdf)).pages)
            return pdf, max(page_count, 1)
        except DocumentEngineError:
            raise
        except Exception as exc:
            logger.exception("Document PDF rendering failed", extra={"document_failure": "pdf_render"})
            raise DocumentEngineError(
                "The PDF engine could not render this document.",
                status_code=500,
                code="DOCUMENT_RENDER_FAILED",
                resolution_steps=["Confirm the document template and branding are configured.", "Retry the document action.", "If the issue persists, contact System Administration with the correlation ID."],
            ) from exc

    @classmethod
    def _correlation_id(cls, request=None) -> str:
        if request is None:
            return ""
        return str(
            request.headers.get("X-Correlation-ID")
            or request.headers.get("X-Request-ID")
            or ""
        )[:100]

    @classmethod
    def render(cls, *, document_type, object_id, actor, request=None) -> DocumentInstance:
        definition = DocumentTypeRegistry.get(document_type)
        if definition.status == "TEMPLATE_PENDING":
            raise DocumentEngineError(
                definition.pending_message or f"{definition.title} template is not configured.",
                status_code=409,
                code="TEMPLATE_PENDING",
            )
        source = cls.resolve_source(definition, object_id)
        cls.ensure_access(actor, definition, source)
        template = cls.template_for(definition)
        try:
            branding = CompanyBranding.resolve(template.branding_config_reference).as_context()
            context = definition.context_builder(source, branding, template)
            context.update(
                {
                    "document_type": definition.document_type,
                    "source_type": f"{definition.source_app_label}.{definition.source_model}",
                    "source_object_id": str(source.pk),
                    "generated_at": timezone.now(),
                    "generated_by_name": cls.user_display(actor),
                }
            )
            cls._validate_context(context, template.variables_schema or definition.variables_schema)
            html = render_to_string(template.layout_template_path, context)
            pdf, page_count = cls._render_pdf(html)
            digest = hashlib.sha256(pdf).hexdigest()
            stamp = timezone.now().strftime("%Y%m%d%H%M%S%f")
            prefix = f"documents/{definition.document_type.lower()}/{source.pk}/{stamp}-{digest[:12]}"
            preview_reference = default_storage.save(
                f"{prefix}.html",
                ContentFile(html.encode("utf-8"), name=f"{prefix}.html"),
            )
            file_reference = default_storage.save(
                f"{prefix}.pdf",
                ContentFile(pdf, name=f"{prefix}.pdf"),
            )
        except DocumentEngineError:
            raise
        except Exception as exc:
            logger.exception(
                "Unified document render or storage failed",
                extra={"correlation_id": cls._correlation_id(request), "document_type": definition.document_type, "source_object_id": str(source.pk)},
            )
            raise DocumentEngineError(
                "The document could not be rendered or stored.",
                status_code=500,
                code="DOCUMENT_RENDER_FAILED",
                resolution_steps=[
                    "Confirm the active template and company branding are configured.",
                    "Retry the document action.",
                    "If the issue persists, contact System Administration with the correlation ID.",
                ],
            ) from exc
        instance = DocumentInstance.objects.create(
            document_type=definition.document_type,
            source_app_label=definition.source_app_label,
            source_model=definition.source_model,
            source_object_id=str(source.pk),
            template=template,
            template_version=template.version,
            file_reference=file_reference,
            preview_reference=preview_reference,
            generated_by=actor,
            generated_at=timezone.now(),
            correlation_id=cls._correlation_id(request),
            page_count=page_count,
            checksum=digest,
            mime_type="application/pdf",
            status="GENERATED",
            metadata={
                "source_type": f"{definition.source_app_label}.{definition.source_model}",
                "source_object_id": str(source.pk),
                "template_code": template.code,
                "template_version": template.version,
                "variables": definition.variables_schema,
                "branding_config_reference": template.branding_config_reference,
                "branding_version": branding.get("version", 0),
            },
        )
        AuditService.log_action(
            action="DOCUMENT_GENERATED",
            instance=instance,
            actor=actor,
            request=request,
            after_state={
                "document_id": str(instance.pk),
                "source_type": instance.source_type,
                "source_object_id": instance.source_object_id,
                "template_version": instance.template_version,
                "checksum": instance.checksum,
            },
            reason="Unified document rendered and stored.",
            source_channel="API",
        )
        return instance

    @classmethod
    def _signer(cls):
        return signing.TimestampSigner(key=settings.SECRET_KEY, salt=cls.TICKET_SALT)

    @classmethod
    def issue_download_ticket(cls, instance, actor, request=None) -> tuple[str, datetime]:
        definition = DocumentTypeRegistry.for_instance(instance)
        source = cls.resolve_source(definition, instance.source_object_id)
        cls.ensure_access(actor, definition, source)
        expires_at = timezone.now() + timedelta(seconds=cls.TICKET_MAX_AGE_SECONDS)
        payload = {
            "v": 1,
            "purpose": cls.TICKET_PURPOSE,
            "instance_id": str(instance.pk),
            "source_type": instance.source_type,
            "source_object_id": instance.source_object_id,
            "user_id": str(actor.pk),
            "format": "pdf",
        }
        ticket = cls._signer().sign_object(payload)
        AuditService.log_action(
            action="DOCUMENT_TICKET_ISSUED",
            instance=instance,
            actor=actor,
            request=request,
            after_state={"expires_at": expires_at.isoformat(), "format": "pdf"},
            reason="Short-lived unified document download ticket issued.",
            source_channel="API",
        )
        return ticket, expires_at

    @classmethod
    def validate_ticket(cls, ticket: str, instance: DocumentInstance, request=None):
        if not ticket or len(ticket) > 4096:
            raise DocumentEngineError("The document download ticket is missing or invalid.", 403)
        try:
            payload = cls._signer().unsign_object(ticket, max_age=cls.TICKET_MAX_AGE_SECONDS)
        except signing.SignatureExpired as exc:
            raise DocumentEngineError("The document download ticket has expired. Generate a new link.", 403) from exc
        except signing.BadSignature as exc:
            raise DocumentEngineError("The document download ticket is invalid.", 403) from exc
        if not isinstance(payload, dict) or payload.get("purpose") != cls.TICKET_PURPOSE or payload.get("v") != 1:
            raise DocumentEngineError("The document download ticket is invalid for this resource.", 403)
        if payload.get("format") != "pdf" or str(payload.get("instance_id")) != str(instance.pk):
            raise DocumentEngineError("The document download ticket does not match this document.", 403)
        if payload.get("source_type") != instance.source_type or str(payload.get("source_object_id")) != str(instance.source_object_id):
            raise DocumentEngineError("The document download ticket does not match its source transaction.", 403)
        try:
            UUID(str(payload["user_id"]))
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise DocumentEngineError("The document download ticket is invalid.", 403) from exc
        owner = apps.get_model("users", "User").objects.filter(
            pk=payload["user_id"],
            is_active=True,
            status="ACTIVE",
        ).first()
        if owner is None:
            raise DocumentEngineError("The document ticket owner is no longer active.", 403)
        if getattr(request, "user", None) is not None and getattr(request.user, "is_authenticated", False):
            if request.user.pk != owner.pk:
                raise DocumentEngineError("This document ticket belongs to another user.", 403)
        return owner, payload

    @classmethod
    def protected_url(cls, instance, request=None, signed=False, actor=None):
        path = reverse("v1:documents:download", kwargs={"pk": instance.pk})
        if signed:
            ticket, expires_at = cls.issue_download_ticket(instance, actor, request)
            path = f"{path}?{urlencode({'ticket': ticket})}"
            return (request.build_absolute_uri(path) if request is not None else path), expires_at
        return request.build_absolute_uri(path) if request is not None else path

    @classmethod
    def preview_url(cls, instance, request=None):
        path = reverse("v1:documents:preview", kwargs={"pk": instance.pk})
        return request.build_absolute_uri(path) if request is not None else path

    @classmethod
    def stream(cls, *, instance, actor=None, request=None, ticket=None, format_name="pdf"):
        format_name = (format_name or "pdf").strip().lower()
        if format_name not in {"pdf", "html"}:
            raise DocumentEngineError("Unsupported document format.", 400)
        definition = DocumentTypeRegistry.for_instance(instance)
        source = cls.resolve_source(definition, instance.source_object_id)
        via_ticket = bool(ticket)
        if via_ticket:
            ticket_owner, _payload = cls.validate_ticket(ticket, instance, request)
            actor = ticket_owner
            cls.ensure_access(actor, definition, source)
        else:
            if not actor or not getattr(actor, "is_authenticated", False):
                raise DocumentEngineError("Authentication credentials were not provided.", 401)
            cls.ensure_access(actor, definition, source)
        reference = instance.preview_reference if format_name == "html" else instance.file_reference
        if not reference or not default_storage.exists(reference):
            raise Http404("The requested document is no longer available.")
        try:
            handle = default_storage.open(reference, "rb")
        except FileNotFoundError as exc:
            raise Http404("The requested document is no longer available.") from exc
        content_type = "text/html; charset=utf-8" if format_name == "html" else instance.mime_type
        response = FileResponse(handle, content_type=content_type)
        response["Content-Disposition"] = f"inline; filename=document-{instance.pk}.{'html' if format_name == 'html' else 'pdf'}"
        response["Cache-Control"] = "private, no-store, max-age=0"
        response["Pragma"] = "no-cache"
        response["X-Content-Type-Options"] = "nosniff"
        AuditService.log_action(
            action="DOCUMENT_TICKET_DOWNLOADED" if via_ticket else ("DOCUMENT_PREVIEWED" if format_name == "html" else "DOCUMENT_DOWNLOADED"),
            instance=instance,
            actor=actor,
            request=request,
            before_state={"format": format_name},
            after_state={"format": format_name, "source_type": instance.source_type},
            reason="Unified document accessed through a protected stream.",
            source_channel="API",
        )
        return response

    @classmethod
    def payload(cls, instance, request=None, actor=None, signed=True):
        signed_url = None
        expires_at = None
        if signed and actor is not None:
            signed_url, expires_at = cls.protected_url(instance, request, signed=True, actor=actor)
        return {
            "id": str(instance.pk),
            "document_type": instance.document_type,
            "source_type": instance.source_type,
            "source_object_id": instance.source_object_id,
            "source_display": cls.source_display(instance),
            "template_name": instance.template.name,
            "template_code": instance.template.code,
            "template_version": instance.template_version,
            "generated_by_display": cls.user_display(instance.generated_by),
            "generated_at": instance.generated_at.isoformat() if instance.generated_at else None,
            "correlation_id": instance.correlation_id,
            "page_count": instance.page_count,
            "checksum": instance.checksum,
            "mime_type": instance.mime_type,
            "status": instance.status,
            "preview_url": cls.preview_url(instance, request),
            "preview_blob_base64_or_url": cls.preview_url(instance, request),
            "signed_download_url": signed_url,
            "download_url_expires_at": expires_at.isoformat() if expires_at else None,
        }

    @staticmethod
    def user_display(user):
        if user is None:
            return "System"
        return str(
            getattr(user, "get_full_name", lambda: "")()
            or getattr(user, "full_name", "")
            or getattr(user, "username", "")
            or getattr(user, "email", "")
        )

    @classmethod
    def source_display(cls, instance):
        definition = DocumentTypeRegistry.get(instance.document_type)
        source = cls.resolve_source(definition, instance.source_object_id)
        return str(source)


__all__ = [
    "CompanyBranding",
    "DocumentEngine",
    "DocumentEngineError",
    "DocumentTypeDefinition",
    "DocumentTypeRegistry",
]
