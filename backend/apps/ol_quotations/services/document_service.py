from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.common.models import DomainEvent
from apps.governance.services.audit_service import AuditService

from apps.ol_quotations.models import (
    OLQuotation,
    OLQuotationDocument,
    OLQuotationPrintTemplate,
    OLQuotationVersion,
    QuotationStatus,
)
from .quotation_service import QuotationService
from .print_ticket_service import PrintTicketService
from apps.documents.services.engine import DocumentEngine


class QuotationDocumentService:
    """Generate durable, source-linked quotation HTML and PDF documents."""

    MODULE = "ol_quotations"
    DEFAULT_TEMPLATE_CODE = "OL_QUOTATION_PRINT"
    DEFAULT_TEMPLATE_VERSION = 2
    DOCUMENT_TYPE = "QUOTATION_PRINT"
    # Legacy seed/API compatibility only; rendering is owned by DocumentEngine.
    DEFAULT_TEMPLATE_HTML = ""

    @staticmethod

    def _display_name(value, fallback=""):
        if value is None:
            return fallback
        for attr in ("full_name", "display_name", "name"):
            candidate = getattr(value, attr, None)
            if candidate:
                return str(candidate)
        first = getattr(value, "first_name", "") or ""
        last = getattr(value, "last_name", "") or ""
        if (first or last).strip():
            return f"{first} {last}".strip()
        return str(getattr(value, "username", "") or getattr(value, "email", "") or fallback)

    @staticmethod
    def _display(value, default=""):
        if value is None:
            return default
        if isinstance(value, Decimal):
            return f"{value:,.2f}"
        if isinstance(value, date):
            return value.isoformat()
        return str(value)

    @classmethod
    def _money(cls, value, currency):
        if value is None or value == "":
            return "-"
        formatted = cls._display(value)
        return f"{currency} {formatted}" if currency else formatted

    @classmethod
    def default_template(cls):
        template, created = OLQuotationPrintTemplate.objects.get_or_create(
            code=cls.DEFAULT_TEMPLATE_CODE,
            version=cls.DEFAULT_TEMPLATE_VERSION,
            defaults={
                "name": "Ordinary Life Quotation Print",
                "description": "Screenshot-aligned Ordinary Life quotation output template.",
                "template_html": cls.DEFAULT_TEMPLATE_HTML,
                "layout_variables": {"company_name": "Zanzibar Insurance Corporation", "company_address": "Bima House, No. 1 Mpirani Street, Mlandege Road, Zanzibar City", "company_phone": "+255 659 072 500", "company_email": "info@zic.co.tz"},
                "effective_from": timezone.localdate(),
                "is_active": True,
            },
        )
        if created:
            return template
        return template

    @classmethod
    def resolve_template(cls, *, template_code=None, as_of=None):
        as_of = as_of or timezone.localdate()
        queryset = OLQuotationPrintTemplate.objects.filter(
            is_active=True,
            effective_from__isnull=True,
        ) | OLQuotationPrintTemplate.objects.filter(
            is_active=True,
            effective_from__lte=as_of,
        )
        queryset = queryset.filter(code=(template_code or cls.DEFAULT_TEMPLATE_CODE).strip().upper())
        queryset = queryset.filter(effective_to__isnull=True) | queryset.filter(effective_to__gte=as_of)
        template = queryset.order_by("-version").first()
        return template or cls.default_template()

    @classmethod
    def _source_version(cls, quotation):
        return quotation.versions.filter(
            version_number=quotation.current_version_number,
        ).order_by("-created_at").first()

    @classmethod
    def _plan_context(cls, quotation):
        rows = []
        for config in quotation.plan_configurations.filter(is_selected=True).select_related("plan", "product_version"):
            plan = config.plan
            rows.append({
                "id": str(config.pk),
                "code": cls._display(getattr(plan, "code", None), config.sub_product_code or "PLAN"),
                "name": cls._display(getattr(plan, "name", None)),
                "description": cls._display(getattr(plan, "description", None)),
                "term_years": config.term_years,
                "payment_period_years": config.payment_period_years or config.term_years,
                "premium_frequency": config.premium_frequency,
                "base_sum_assured": cls._money(config.base_sum_assured, quotation.currency),
                "premium_amount": cls._money(config.premium_amount, quotation.currency),
                "estimated_maturity_value": cls._money(config.estimated_maturity_value, quotation.currency),
                "estimated_bonus_rate": cls._display(config.estimated_bonus_rate),
                "joint_life": config.joint_life,
                "mortgage": config.mortgage,
            })
        return rows

    @classmethod
    def _member_context(cls, quotation):
        rows = []
        for member in quotation.members.all().order_by("member_type", "last_name", "first_name"):
            metadata = member.metadata if isinstance(member.metadata, dict) else {}
            is_principal = str(member.member_type or "").upper() in {"POLICYHOLDER", "PRINCIPAL", "LIFE_ASSURED"}
            rows.append({
                "name": f"{member.first_name} {member.last_name}".strip() or "Member",
                "age": member.age_at_quote,
                "gender": member.gender,
                "coverage_percent": cls._display(metadata.get("coverage_percent", 100 if is_principal else "")),
                "sum_assured": cls._money(metadata.get("sum_assured", member.member_sum_assured), quotation.currency),
                "basic_premium": cls._money(metadata.get("basic_premium", ""), quotation.currency),
                "rider_premium": cls._money(metadata.get("rider_premium", ""), quotation.currency),
                "total_premium": cls._money(metadata.get("total_premium", ""), quotation.currency),
                "plan_name": cls._display(metadata.get("plan_name", "")),
                "is_principal": is_principal,
            })
        return rows

    @classmethod
    def _rider_context(cls, quotation):
        rows = []
        for selection in quotation.rider_selections.filter(is_selected=True).select_related("rider", "plan_configuration__plan"):
            rows.append({
                "id": str(selection.pk),
                "code": cls._display(getattr(selection.rider, "code", None)),
                "name": cls._display(getattr(selection.rider, "name", None)),
                "benefit_basis": selection.benefit_basis,
                "benefit_value": cls._display(selection.benefit_value),
                "rider_sum_assured": cls._money(selection.rider_sum_assured, quotation.currency),
                "premium_amount": cls._money(selection.premium_amount, quotation.currency),
                "loading": cls._display(selection.loading),
                "discount": cls._display(selection.discount),
                "maximum_cap": cls._display(selection.maximum_cap),
                "benefit_ratio": cls._display(selection.benefit_value if selection.benefit_basis == "RATIO" else ""),
                "plan_name": cls._display(getattr(getattr(selection.plan_configuration, "plan", None), "name", "")),
                "sub_product": cls._display(getattr(selection.plan_configuration, "sub_product_code", None), "-"),
            })
        return rows

    @classmethod
    def _installment_context(cls, quotation):
        schedules = []
        try:
            summary = quotation.financial_summary
        except Exception:
            summary = None
        maturity_value = getattr(summary, "estimated_maturity_value", None)
        if maturity_value is None:
            maturity_value = sum(
                (config.estimated_maturity_value or Decimal("0") for config in quotation.plan_configurations.filter(is_selected=True)),
                Decimal("0"),
            )
        saved_payouts = {}
        raw_payouts = getattr(summary, "installment_payouts", None) if summary else None
        if isinstance(raw_payouts, list):
            saved_payouts = {str(item.get("sequence")): item for item in raw_payouts if isinstance(item, dict)}
        for config in quotation.installment_configurations.filter(is_selected=True).select_related("plan_configuration__plan"):
            plan = config.plan_configuration.plan if config.plan_configuration_id and config.plan_configuration.plan_id else None
            rows = []
            for row in config.rate_rows.all().order_by("sequence", "period_from"):
                payout_date = row.installment_configuration.first_due_date
                if payout_date:
                    months = max(0, (row.sequence - 1) * cls._frequency_months(config.frequency))
                    month_index = payout_date.month - 1 + months
                    year = payout_date.year + month_index // 12
                    month = month_index % 12 + 1
                    import calendar
                    day = min(payout_date.day, calendar.monthrange(year, month)[1])
                    payout_date = payout_date.replace(year=year, month=month, day=day)
                saved_payout = saved_payouts.get(str(row.sequence), {})
                payout_amount = saved_payout.get("payout_amount")
                if payout_amount in (None, ""):
                    if row.charge and row.charge > 0:
                        payout_amount = row.charge
                    else:
                        payout_amount = (maturity_value or Decimal("0")) * row.rate_percent / Decimal("100")
                rows.append({
                    "sequence": row.sequence,
                    "description": row.description or row.notes,
                    "payout_date": cls._display(payout_date),
                    "rate_percent": cls._display(row.rate_percent),
                    "paid_up_rate": cls._display(row.paid_up_rate),
                    "payout_amount": cls._money(payout_amount, config.currency or quotation.currency),
                })
            schedules.append({
                "plan_code": cls._display(getattr(plan, "code", None), "PLAN"),
                "frequency": config.frequency,
                "annuity_period_years": config.annuity_period_years,
                "number_of_installments": config.number_of_installments,
                "after_maturity_benefits": config.after_maturity_benefits,
                "before_maturity_benefits": config.before_maturity_benefits,
                "rows": rows,
            })
        return schedules

    @staticmethod
    def _frequency_months(frequency):
        return {
            "MONTHLY": 1,
            "QUARTERLY": 3,
            "SEMI_ANNUALLY": 6,
            "SEMI_ANNUAL": 6,
            "ANNUALLY": 12,
            "ANNUAL": 12,
        }.get((frequency or "").upper(), 12)

    @classmethod
    def _benefit_context(cls, quotation):
        rows = []
        for benefit in quotation.benefits.filter(is_selected=True).select_related("beneficial_type", "plan_configuration__plan"):
            rows.append({
                "code": cls._display(benefit.code),
                "name": cls._display(getattr(benefit.beneficial_type, "name", None) or benefit.name or benefit.code),
                "benefit_type": cls._display(getattr(benefit.beneficial_type, "code", None) or benefit.benefit_type),
                "basis": cls._display(benefit.basis),
                "value": cls._money(benefit.value, quotation.currency),
                "sum_assured": cls._money(benefit.sum_assured, quotation.currency),
                "loading": cls._display(benefit.loading),
                "discount": cls._display(benefit.discount),
                "maximum_cap": cls._money(benefit.maximum_cap, quotation.currency),
                "plan_name": cls._display(getattr(getattr(benefit.plan_configuration, "plan", None), "name", None)),
            })
        return rows

    @classmethod
    def build_context(cls, quotation, template):
        try:
            summary = quotation.financial_summary
        except Exception:
            summary = None
        agent = quotation.agent or quotation.agent_partner
        prospect_name = ""
        if quotation.partner_id:
            prospect_name = cls._display_name(quotation.partner, "")
        if not prospect_name:
            prospect_name = quotation.quote_name
        context = {
            "company": {
                "name": (template.layout_variables or {}).get("company_name", "Zanzibar Insurance Corporation"),
                "address": (template.layout_variables or {}).get("company_address", "Bima House, No. 1 Mpirani Street, Mlandege Road, Zanzibar City"),
                "phone": (template.layout_variables or {}).get("company_phone", ""),
                "email": (template.layout_variables or {}).get("company_email", ""),
            },
            "quote": {
                "id": str(quotation.pk),
                "quote_number": quotation.quote_number,
                "quote_name": quotation.quote_name,
                "quote_date": cls._display(quotation.quote_date),
                "status": quotation.status,
                "currency": quotation.currency,
                "expiry_date": cls._display(quotation.expiry_date),
                "version_number": quotation.current_version_number,
                "validity_days": max(0, (quotation.expiry_date - quotation.quote_date).days) if quotation.expiry_date and quotation.quote_date else 30,
            },
            "members": cls._member_context(quotation),
            "prepared_by": cls._display_name(getattr(quotation, "created_by", None), "ZIC Quotation Team"),
            "prospect": {
                "name": prospect_name,
                "identity_type": quotation.identity_type,
                "identity_number": quotation.identity_number,
                "date_of_birth": cls._display(quotation.date_of_birth),
                "age_at_quote": quotation.age_at_quote,
                "gender": quotation.gender,
                "smoker_status": quotation.smoker_status,
                "location": quotation.location or cls._display(getattr(quotation.location_master, "name", None)),
                "address": quotation.address,
            },
            "agent": {"name": cls._display_name(agent, "Not assigned")},
            "plans": cls._plan_context(quotation),
            "riders": cls._rider_context(quotation),
            "benefits": cls._benefit_context(quotation),
            "installments": cls._installment_context(quotation),
            "financial": {
                "total_sum_assured": cls._money(getattr(summary, "total_sum_assured", quotation.total_sum_assured), quotation.currency),
                "base_premium": cls._money(getattr(summary, "base_premium", quotation.total_premium), quotation.currency),
                "total_rider_premium": cls._money(getattr(summary, "total_rider_premium", None), quotation.currency),
                "total_loading": cls._money(getattr(summary, "total_loading", None), quotation.currency),
                "total_discount": cls._money(getattr(summary, "total_discount", None), quotation.currency),
                "total_tax": cls._money(getattr(summary, "total_tax", None), quotation.currency),
                "total_premium": cls._money(getattr(summary, "total_premium", quotation.total_premium), quotation.currency),
                "estimated_maturity_value": cls._money(getattr(summary, "estimated_maturity_value", None), quotation.currency),
            },
        }
        return context

    @classmethod
    def generate(cls, *, quotation, actor, request=None, template_code=None, preview=False):
        effective_status = QuotationService.effective_status(quotation)
        if effective_status == QuotationStatus.EXPIRED:
            raise ValidationError("Expired quotations cannot be printed.")
        if quotation.status == QuotationStatus.DRAFT and not preview:
            raise ValidationError("Draft quotations require preview=true to generate a printout.")
        if quotation.status not in {QuotationStatus.DRAFT, QuotationStatus.FINALIZED, QuotationStatus.CONVERTED}:
            raise ValidationError("Only draft previews, finalized, or converted quotations can be printed.")
        template = cls.resolve_template(template_code=template_code, as_of=quotation.quote_date)
        source_version = cls._source_version(quotation)
        if source_version is None:
            source_version = OLQuotationVersion.objects.create(
                quotation=quotation,
                version_number=quotation.current_version_number,
                status=quotation.status,
                snapshot=QuotationService.version_snapshot(quotation),
                change_reason="Source version captured for quotation printout.",
                created_by=QuotationService.actor(actor),
                updated_by=QuotationService.actor(actor),
            )
        unified_instance = DocumentEngine.render(
            document_type="OL_QUOTATION",
            object_id=quotation.pk,
            actor=actor,
            request=request,
        )
        document = OLQuotationDocument.objects.create(
            quotation=quotation,
            source_version=source_version,
            template=template,
            template_version=template.version,
            document_type=cls.DOCUMENT_TYPE,
            file_reference=unified_instance.file_reference,
            html_reference=unified_instance.preview_reference,
            mime_type=unified_instance.mime_type,
            status="GENERATED",
            generated_by=QuotationService.actor(actor),
            generated_at=unified_instance.generated_at,
            metadata={
                "preview": bool(preview),
                "quotation_version_number": quotation.current_version_number,
                "template_code": template.code,
                "template_version": template.version,
                "unified_document_instance_id": str(unified_instance.pk),
                "variables": [
                    "quote", "prospect", "plans", "riders", "benefits", "installments", "financial", "agent", "company",
                ],
            },
            created_by=QuotationService.actor(actor),
            updated_by=QuotationService.actor(actor),
        )
        AuditService.log_action(
            action="PRINT",
            instance=quotation,
            actor=actor,
            request=request,
            before_state=QuotationService.snapshot(quotation),
            after_state={
                **QuotationService.snapshot(quotation),
                "document_id": str(document.pk),
                "template_code": template.code,
                "template_version": template.version,
            },
            reason="Quotation printout generated.",
            changed_fields=[],
        )
        DomainEvent.objects.create(
            event_type="QuotationPrintGenerated",
            aggregate_type="OLQuotation",
            aggregate_id=str(quotation.pk),
            payload={
                "quotation_id": str(quotation.pk),
                "quote_number": quotation.quote_number,
                "document_id": str(document.pk),
                "source_version_id": str(source_version.pk),
                "quotation_version_number": quotation.current_version_number,
                "template_code": template.code,
                "template_version": template.version,
                "preview": bool(preview),
            },
        )
        return document

    @staticmethod
    def document_urls(document, *, request=None, actor=None, issue_tickets=False):
        result = {
            "pdf_url": PrintTicketService.protected_path(document, "pdf") if document.file_reference else None,
            "html_url": PrintTicketService.protected_path(document, "html") if document.html_reference else None,
        }
        if issue_tickets and actor is not None:
            pdf_ticket, expires_at = PrintTicketService.issue(
                document=document,
                actor=actor,
                request=request,
                content_format="pdf",
            )
            result["pdf_url"] = PrintTicketService.ticket_url(
                document=document,
                ticket=pdf_ticket,
                content_format="pdf",
                request=request,
            )
            result["signed_download_url"] = result["pdf_url"]
            result["download_url_expires_at"] = expires_at.isoformat()
            if document.html_reference:
                html_ticket, html_expires_at = PrintTicketService.issue(
                    document=document,
                    actor=actor,
                    request=request,
                    content_format="html",
                )
                result["html_url"] = PrintTicketService.ticket_url(
                    document=document,
                    ticket=html_ticket,
                    content_format="html",
                    request=request,
                )
                result["signed_preview_url"] = result["html_url"]
                result["preview_url_expires_at"] = html_expires_at.isoformat()
        return result
