from datetime import date
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError as DjangoValidationError
from django.template import Context, Template, TemplateDoesNotExist
from django.template.loader import render_to_string
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


class QuotationDocumentService:
    """Generate durable, source-linked quotation HTML and PDF documents."""

    MODULE = "ol_quotations"
    DEFAULT_TEMPLATE_CODE = "OL_QUOTATION_PRINT"
    DOCUMENT_TYPE = "QUOTATION_PRINT"

    DEFAULT_TEMPLATE_HTML = """
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <style>
    @page { size: A4; margin: 18mm 15mm 18mm 15mm; }
    body { font-family: Arial, Helvetica, sans-serif; color: #111; font-size: 10pt; line-height: 1.35; }
    .header { border-bottom: 2px solid #111; padding-bottom: 10px; margin-bottom: 16px; }
    .company { font-size: 18pt; font-weight: 700; letter-spacing: .04em; }
    .muted { color: #555; }
    h1 { font-size: 18pt; margin: 0 0 12px; }
    h2 { font-size: 12pt; border-bottom: 1px solid #999; padding-bottom: 4px; margin: 18px 0 8px; }
    table { width: 100%; border-collapse: collapse; margin: 6px 0 12px; }
    th, td { border: 1px solid #777; padding: 5px 6px; vertical-align: top; }
    th { background: #eee; text-align: left; }
    .right { text-align: right; }
    .summary { width: 48%; margin-left: auto; }
    .footer { border-top: 1px solid #999; margin-top: 22px; padding-top: 7px; font-size: 8pt; }
  </style>
</head>
<body>
  <div class=\"header\">
    <div class=\"company\">{{ company.name }}</div>
    <div class=\"muted\">{{ company.address }}{% if company.phone %} · {{ company.phone }}{% endif %}{% if company.email %} · {{ company.email }}{% endif %}</div>
  </div>
  <h1>Quotation</h1>
  <table>
    <tr><th>Quote Number</th><td>{{ quote.quote_number }}</td><th>Quote Date</th><td>{{ quote.quote_date }}</td></tr>
    <tr><th>Quote Name</th><td>{{ quote.quote_name }}</td><th>Currency</th><td>{{ quote.currency }}</td></tr>
    <tr><th>Status</th><td>{{ quote.status }}</td><th>Valid Until</th><td>{{ quote.expiry_date }}</td></tr>
  </table>

  <h2>Prospect Details</h2>
  <table>
    <tr><th>Name</th><td>{{ prospect.name }}</td><th>Identity</th><td>{{ prospect.identity_type }} {{ prospect.identity_number }}</td></tr>
    <tr><th>Date of Birth</th><td>{{ prospect.date_of_birth }}</td><th>Age at Quote</th><td>{{ prospect.age_at_quote }}</td></tr>
    <tr><th>Gender</th><td>{{ prospect.gender }}</td><th>Smoker Status</th><td>{{ prospect.smoker_status }}</td></tr>
    <tr><th>Location</th><td>{{ prospect.location }}</td><th>Agent</th><td>{{ agent.name }}</td></tr>
  </table>
  {% if prospect.address %}<p><strong>Address:</strong> {{ prospect.address }}</p>{% endif %}

  <h2>Plans and Premiums</h2>
  <table>
    <tr><th>Plan</th><th>Term</th><th>Payment Period</th><th>Frequency</th><th>Sum Assured</th><th>Premium</th><th>Maturity Value</th></tr>
    {% for plan in plans %}
    <tr><td>{{ plan.code }}{% if plan.name %} — {{ plan.name }}{% endif %}</td><td>{{ plan.term_years }} years</td><td>{{ plan.payment_period_years }}</td><td>{{ plan.premium_frequency }}</td><td class=\"right\">{{ plan.base_sum_assured }}</td><td class=\"right\">{{ plan.premium_amount }}</td><td class=\"right\">{{ plan.estimated_maturity_value }}</td></tr>
    {% endfor %}
  </table>

  {% if riders %}
  <h2>Riders and Benefits</h2>
  <table>
    <tr><th>Rider</th><th>Benefit Basis</th><th>Benefit Value</th><th>Sum Assured</th><th>Premium</th></tr>
    {% for rider in riders %}<tr><td>{{ rider.code }}{% if rider.name %} — {{ rider.name }}{% endif %}</td><td>{{ rider.benefit_basis }}</td><td>{{ rider.benefit_value }}</td><td class=\"right\">{{ rider.rider_sum_assured }}</td><td class=\"right\">{{ rider.premium_amount }}</td></tr>{% endfor %}
  </table>
  {% endif %}

  {% if installments %}
  <h2>Installment Schedule</h2>
  {% for schedule in installments %}
  <p><strong>{{ schedule.plan_code }}</strong> · {{ schedule.frequency }} · {{ schedule.number_of_installments }} installments · {{ schedule.annuity_period_years }} year annuity period</p>
  <table><tr><th>#</th><th>Description</th><th>Due Date</th><th>Rate</th><th>Paid-Up Rate</th><th>Amount</th></tr>
  {% for row in schedule.rows %}<tr><td>{{ row.sequence }}</td><td>{{ row.description }}</td><td>{{ row.payout_date }}</td><td>{{ row.rate_percent }}%</td><td>{{ row.paid_up_rate }}</td><td class=\"right\">{{ row.payout_amount }}</td></tr>{% endfor %}
  </table>
  {% endfor %}
  {% endif %}

  <table class=\"summary\">
    <tr><th>Total Sum Assured</th><td class=\"right\">{{ financial.total_sum_assured }}</td></tr>
    <tr><th>Base Premium</th><td class=\"right\">{{ financial.base_premium }}</td></tr>
    <tr><th>Rider Premium</th><td class=\"right\">{{ financial.total_rider_premium }}</td></tr>
    <tr><th>Loadings</th><td class=\"right\">{{ financial.total_loading }}</td></tr>
    <tr><th>Discounts</th><td class=\"right\">{{ financial.total_discount }}</td></tr>
    <tr><th>Taxes</th><td class=\"right\">{{ financial.total_tax }}</td></tr>
    <tr><th>Total Premium</th><td class=\"right\"><strong>{{ financial.total_premium }}</strong></td></tr>
    <tr><th>Estimated Maturity Value</th><td class=\"right\">{{ financial.estimated_maturity_value }}</td></tr>
  </table>
  <div class=\"footer\">This quotation is generated from the ZIC quotation system. It is subject to the applicable product terms, underwriting, and approval requirements.</div>
</body>
</html>
"""

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
    def default_template(cls):
        template, created = OLQuotationPrintTemplate.objects.get_or_create(
            code=cls.DEFAULT_TEMPLATE_CODE,
            version=1,
            defaults={
                "name": "Ordinary Life Quotation Print",
                "description": "Default monochrome quotation output template.",
                "template_html": cls.DEFAULT_TEMPLATE_HTML,
                "layout_variables": {"company_name": "Zanzibar Insurance Company"},
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
                "base_sum_assured": cls._display(config.base_sum_assured),
                "premium_amount": cls._display(config.premium_amount),
                "estimated_maturity_value": cls._display(config.estimated_maturity_value),
                "estimated_bonus_rate": cls._display(config.estimated_bonus_rate),
                "joint_life": config.joint_life,
                "mortgage": config.mortgage,
            })
        return rows

    @classmethod
    def _rider_context(cls, quotation):
        rows = []
        for selection in quotation.rider_selections.filter(is_selected=True).select_related("rider"):
            rows.append({
                "id": str(selection.pk),
                "code": cls._display(getattr(selection.rider, "code", None)),
                "name": cls._display(getattr(selection.rider, "name", None)),
                "benefit_basis": selection.benefit_basis,
                "benefit_value": cls._display(selection.benefit_value),
                "rider_sum_assured": cls._display(selection.rider_sum_assured),
                "premium_amount": cls._display(selection.premium_amount),
                "loading": cls._display(selection.loading),
                "discount": cls._display(selection.discount),
                "maximum_cap": cls._display(selection.maximum_cap),
            })
        return rows

    @classmethod
    def _installment_context(cls, quotation):
        schedules = []
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
                rows.append({
                    "sequence": row.sequence,
                    "description": row.description or row.notes,
                    "payout_date": cls._display(payout_date),
                    "rate_percent": cls._display(row.rate_percent),
                    "paid_up_rate": cls._display(row.paid_up_rate),
                    "payout_amount": cls._display(row.charge or row.rate),
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
                "name": (template.layout_variables or {}).get("company_name", "Zanzibar Insurance Company"),
                "address": (template.layout_variables or {}).get("company_address", "Zanzibar, Tanzania"),
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
            },
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
            "benefits": [],
            "installments": cls._installment_context(quotation),
            "financial": {
                "total_sum_assured": cls._display(getattr(summary, "total_sum_assured", quotation.total_sum_assured)),
                "base_premium": cls._display(getattr(summary, "base_premium", quotation.total_premium)),
                "total_rider_premium": cls._display(getattr(summary, "total_rider_premium", None)),
                "total_loading": cls._display(getattr(summary, "total_loading", None)),
                "total_discount": cls._display(getattr(summary, "total_discount", None)),
                "total_tax": cls._display(getattr(summary, "total_tax", None)),
                "total_premium": cls._display(getattr(summary, "total_premium", quotation.total_premium)),
                "estimated_maturity_value": cls._display(getattr(summary, "estimated_maturity_value", None)),
            },
        }
        return context

    @classmethod
    def _render_html(cls, template, context):
        try:
            return Template(template.template_html).render(Context(context))
        except Exception as exc:
            raise ValidationError({"template": f"Quotation print template could not be rendered: {exc}"}) from exc

    @staticmethod
    def _render_pdf(html):
        try:
            from weasyprint import HTML
            return HTML(string=html).write_pdf()
        except Exception as exc:
            raise ValidationError({"pdf": f"Quotation PDF could not be rendered: {exc}"}) from exc

    @staticmethod
    def _save_content(path, content, content_type=None):
        return default_storage.save(path, ContentFile(content, name=path))

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
        context = cls.build_context(quotation, template)
        html = cls._render_html(template, context)
        pdf = cls._render_pdf(html)
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        prefix = f"ol_quotations/{quotation.quote_number}/v{quotation.current_version_number}/{timestamp}"
        html_reference = cls._save_content(f"{prefix}.html", html.encode("utf-8"))
        file_reference = cls._save_content(f"{prefix}.pdf", pdf)
        document = OLQuotationDocument.objects.create(
            quotation=quotation,
            source_version=source_version,
            template=template,
            template_version=template.version,
            document_type=cls.DOCUMENT_TYPE,
            file_reference=file_reference,
            html_reference=html_reference,
            mime_type="application/pdf",
            status="GENERATED",
            generated_by=QuotationService.actor(actor),
            generated_at=timezone.now(),
            metadata={
                "preview": bool(preview),
                "quotation_version_number": quotation.current_version_number,
                "template_code": template.code,
                "template_version": template.version,
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
    def document_urls(document):
        return {
            "pdf_url": default_storage.url(document.file_reference) if document.file_reference else None,
            "html_url": default_storage.url(document.html_reference) if document.html_reference else None,
        }
