"""Front Office Receipts — receipt printout generation (Prompt 8).

Mirrors the unified print/PDF engine (``ol_proposals.services.print_service``):
a versioned HTML template registered under the document template type ``RECEIPT``
is resolved effective-as-of, rendered to HTML, converted to PDF with WeasyPrint,
and persisted through ``default_storage``. The generated ``ReceiptDocument``
retains the source transaction (``receipt``), the template code/version used, and
the generating user/timestamp. Generated files are only reachable through the
authenticated print pipeline: ``document_urls`` returns signed, short-lived
download tickets (see ``print_ticket``) instead of exposing the public media URL.
"""

from datetime import date
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.template import Context, Template
from django.utils import timezone

from apps.front_office.receipts.errors import ReceiptError, invalid_status
from apps.front_office.receipts.models import (
    ReceiptDocument,
    ReceiptDocumentStatus,
    ReceiptPrintTemplate,
    ReceiptStatus,
)
from apps.front_office.receipts.services.amount_in_words import amount_in_words
from apps.front_office.receipts.services.print_ticket import issue_download_ticket
from apps.governance.services.audit_service import AuditService

DEFAULT_TEMPLATE_CODE = "RECEIPT"
DEFAULT_TEMPLATE_VERSION = 1
DOCUMENT_TYPE = "RECEIPT"

DEFAULT_COMPANY = {
    "company_name": "Zanzibar Insurance Corporation",
    "company_address": "Bima House, No. 1 Mpirani Street, Mlandege Road, Zanzibar City",
    "company_phone": "+255 659 072 500",
    "company_email": "info@zic.co.tz",
}

DEFAULT_TEMPLATE_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <style>
    @page { size: A4; margin: 12mm 11mm 14mm 11mm; }
    * { box-sizing: border-box; }
    body { font-family: Arial, Helvetica, sans-serif; color: #26313d; font-size: 8.5pt; line-height: 1.25; margin: 0; }
    .sheet { width: 100%; }
    .header { display: table; width: 100%; border-bottom: 2px solid #2d3440; padding-bottom: 8px; margin-bottom: 8px; }
    .header-left, .header-right { display: table-cell; vertical-align: top; }
    .header-right { text-align: right; width: 62%; font-size: 7.3pt; line-height: 1.35; color: #46515d; }
    .logo-wrap { width: 105px; height: 55px; position: relative; }
    .logo-arc { width: 57px; height: 14px; border-top: 3px solid #d94754; border-radius: 50%; position: absolute; left: 23px; top: 3px; }
    .logo-text { position: absolute; left: 0; top: 8px; color: #183a91; font-weight: 900; font-size: 35pt; letter-spacing: -0.14em; line-height: 1; }
    .logo-text span { display: inline-block; transform: skew(-7deg); }
    .title { text-align: center; font-weight: 800; letter-spacing: .12em; font-size: 13pt; padding: 4px 0 5px; border-bottom: 2px solid #2d3440; margin-bottom: 9px; }
    .preview-tag { text-align: center; font-weight: 800; color: #b23b3b; letter-spacing: .18em; font-size: 9pt; margin: 2px 0 6px; }
    .info-grid { display: table; width: 100%; border: 1px solid #d5dbe2; margin-bottom: 9px; }
    .info-col { display: table-cell; width: 50%; padding: 7px 9px; vertical-align: top; }
    .info-col + .info-col { border-left: 1px solid #d5dbe2; }
    .section-title { font-size: 9pt; font-weight: 800; border-bottom: 1px solid #c7ced7; padding-bottom: 3px; margin: 0 0 5px; }
    .kv { margin: 0; }
    .kv-row { display: table; width: 100%; margin: 0 0 2px; }
    .kv-row dt, .kv-row dd { display: table-cell; vertical-align: top; }
    .kv-row dt { width: 44%; font-weight: 700; color: #4f5a66; }
    .kv-row dd { width: 56%; margin: 0; }
    .block { margin-top: 8px; page-break-inside: avoid; }
    table.data { width: 100%; border-collapse: collapse; margin-top: 4px; font-size: 7.15pt; }
    table.data th, table.data td { border: 1px solid #d2d8df; padding: 4px 4px; vertical-align: middle; }
    table.data th { background: #edf1f4; color: #26313d; font-weight: 800; text-align: left; }
    table.data td.num, table.data th.num { text-align: right; }
    table.data tr.total td { font-weight: 800; background: #f7f8fa; }
    .subheading { border-bottom: 1px solid #c7ced7; font-size: 9pt; font-weight: 800; padding-bottom: 3px; }
    .amount-box { display: table; width: 100%; margin-top: 8px; }
    .amount-box > div { display: table-cell; padding: 7px 9px; vertical-align: top; }
    .amount-figures { width: 34%; border: 1px solid #d5dbe2; }
    .amount-figures .value { font-size: 13pt; font-weight: 800; color: #183a91; }
    .amount-words { border: 1px solid #d5dbe2; border-left: none; font-weight: 700; }
    .signature { display: table; width: 100%; margin-top: 13px; padding: 8px 9px 3px; border-top: 1px solid #d5dbe2; background: #fbfbfc; page-break-inside: avoid; }
    .signature-left, .signature-right { display: table-cell; vertical-align: bottom; }
    .signature-right { width: 28%; text-align: center; }
    .signature-line { width: 165px; border-bottom: 1px solid #67717d; height: 21px; margin-bottom: 3px; }
    .stamp { width: 55px; height: 55px; border: 2px solid #66717d; border-radius: 50%; margin: 0 auto 3px; text-align: center; padding-top: 17px; font-size: 8pt; font-weight: 800; color: #3e4852; }
    .muted { color: #64707c; }
    .small { font-size: 7pt; }
    .avoid-break { page-break-inside: avoid; }
    .footer { margin-top: 10px; padding-top: 6px; border-top: 1px solid #d5dbe2; font-size: 6.8pt; color: #64707c; text-align: center; }
    .watermark { position: absolute; top: 42%; left: 0; right: 0; text-align: center; transform: rotate(-30deg); font-size: 30pt; font-weight: 900; letter-spacing: .2em; color: rgba(179, 59, 59, .28); z-index: 5; }
  </style>
</head>
<body>
<div class="sheet">
  {% if watermark %}<div class="watermark">{{ watermark }}</div>{% endif %}
  <div class="header">
    <div class="header-left"><div class="logo-wrap"><div class="logo-arc"></div><div class="logo-text"><span>ZIC</span></div></div></div>
    <div class="header-right"><strong>{{ company.name }}</strong><br>{{ company.address }}<br>{% if company.phone %}Tel: {{ company.phone }}<br>{% endif %}{% if company.email %}Email: {{ company.email }}<br>{% endif %}Generated: {{ generated.at }}</div>
  </div>
  <div class="title">OFFICIAL RECEIPT</div>
  {% if preview %}<div class="preview-tag">PREVIEW — NOT AN OFFICIAL RECEIPT</div>{% endif %}

  <div class="info-grid avoid-break">
    <div class="info-col"><div class="section-title">Receipt Details</div><dl class="kv">
      <div class="kv-row"><dt>Receipt Number:</dt><dd>{{ receipt.receipt_number|default:"Draft" }}</dd></div>
      <div class="kv-row"><dt>Receipt Date:</dt><dd>{{ receipt.receipt_date }}</dd></div>
      <div class="kv-row"><dt>Branch:</dt><dd>{{ receipt.branch }}</dd></div>
      <div class="kv-row"><dt>Status:</dt><dd>{{ receipt.status }}</dd></div>
      <div class="kv-row"><dt>Payment Mode:</dt><dd>{{ receipt.payment_mode }}</dd></div>
      <div class="kv-row"><dt>Payment Reference:</dt><dd>{{ receipt.payment_reference|default:"-" }}</dd></div>
      <div class="kv-row"><dt>Currency:</dt><dd>{{ receipt.currency }}</dd></div>
    </dl></div>
    <div class="info-col"><div class="section-title">Payer</div><dl class="kv">
      <div class="kv-row"><dt>Payer Name:</dt><dd>{{ payer.name }}</dd></div>
      <div class="kv-row"><dt>Identity / Partner No.:</dt><dd>{{ payer.identity }}</dd></div>
      <div class="kv-row"><dt>Source Module:</dt><dd>{{ receipt.source_module }}</dd></div>
      <div class="kv-row"><dt>Source Reference:</dt><dd>{{ receipt.source_reference }}</dd></div>
      <div class="kv-row"><dt>Cashier / Created By:</dt><dd>{{ cashier }}</dd></div>
      <div class="kv-row"><dt>Posted By:</dt><dd>{{ posted_by }}</dd></div>
    </dl></div>
  </div>

  <div class="block avoid-break"><div class="subheading">Amount</div><div class="amount-box">
    <div class="amount-figures"><span class="muted small">Amount in Figures</span><br><span class="value">{{ money.figures }}</span></div>
    <div class="amount-words"><span class="muted small">Amount in Words</span><br>{{ money.words }}</div>
  </div></div>

  {% if allocations %}
  <div class="block"><div class="subheading">Allocated Commitments</div><table class="data"><thead><tr>
    <th>#</th><th>Target / Commitment</th><th>Narration</th><th class="num">Amount ({{ receipt.currency }})</th>{% if money.show_converted %}<th class="num">Converted ({{ money.converted_currency }})</th>{% endif %}<th>Allocation Status</th>
  </tr></thead><tbody>{% for row in allocations %}<tr>
    <td>{{ forloop.counter }}</td><td>{{ row.target_display }}</td><td>{{ row.narration|default:"-" }}</td><td class="num">{{ row.amount }}</td>{% if money.show_converted %}<td class="num">{{ row.converted }}</td>{% endif %}<td>{{ row.status }}</td>
  </tr>{% endfor %}{% if money.show_unallocated %}<tr class="total"><td colspan="3">Unallocated Balance</td><td class="num">{{ money.unallocated }}</td>{% if money.show_converted %}<td></td>{% endif %}<td>Unallocated</td></tr>{% endif %}</tbody></table></div>
  {% else %}
  <div class="block avoid-break"><div class="subheading">Allocation</div><dl class="kv">
    <div class="kv-row"><dt>Allocated Amount:</dt><dd>{{ money.allocated }}</dd></div>
    <div class="kv-row"><dt>Unallocated Amount:</dt><dd>{{ money.unallocated }}</dd></div>
  </dl></div>
  {% endif %}

  <div class="block avoid-break"><div class="subheading">Print Trace</div><dl class="kv">
    <div class="kv-row"><dt>Generated By:</dt><dd>{{ generated.by }}</dd></div>
    <div class="kv-row"><dt>Generated At:</dt><dd>{{ generated.at }}</dd></div>
  </dl></div>

  <div class="signature"><div class="signature-left"><div>Received By: {{ payer.name }}</div><div class="signature-line"></div><div>Signature &amp; Date</div><div class="muted small">payer / recipient of services</div></div><div class="signature-right"><div class="stamp">ZIC</div><strong>{{ company.name }}</strong><br><span class="muted small">Official Stamp</span></div></div>

  <div class="footer">Template v{{ template_version }} · Generated by ZIC Front Office Receipts · {{ generated.at }}</div>
</div>
</body>
</html>
"""

VARIABLES = [
    "company",
    "receipt",
    "payer",
    "money",
    "allocations",
    "generated",
    "cashier",
    "posted_by",
    "watermark",
    "preview",
    "template_version",
]


def Q_effective(as_of):
    from django.db.models import Q

    return Q(effective_from__isnull=True, effective_to__isnull=True) | Q(
        effective_from__lte=as_of, effective_to__isnull=True
    ) | Q(effective_from__lte=as_of, effective_to__gte=as_of)


class ReceiptPrintService:
    """Generate durable, source-linked receipt printout documents (HTML + PDF)."""

    @staticmethod
    def _display(value, default=""):
        if value is None or value == "":
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
        return f"{currency} {cls._display(value)}" if currency else cls._display(value)

    @staticmethod
    def _actor_display(actor, fallback=""):
        if actor is None:
            return fallback
        if hasattr(actor, "get_full_name"):
            full = actor.get_full_name() or ""
            if full:
                return full
        return getattr(actor, "username", None) or str(actor)

    @classmethod
    def default_template(cls):
        template, _created = ReceiptPrintTemplate.objects.get_or_create(
            code=DEFAULT_TEMPLATE_CODE,
            version=DEFAULT_TEMPLATE_VERSION,
            defaults={
                "name": "Front Office Receipt",
                "description": "Official receipt printout for premium collections.",
                "template_html": DEFAULT_TEMPLATE_HTML,
                "layout_variables": dict(DEFAULT_COMPANY),
                "effective_from": timezone.localdate(),
                "is_active": True,
            },
        )
        return template

    @classmethod
    def resolve_template(cls, *, template_code=None, as_of=None):
        as_of = as_of or timezone.localdate()
        template = (
            ReceiptPrintTemplate.objects.filter(
                is_active=True,
                code=(template_code or DEFAULT_TEMPLATE_CODE).strip().upper(),
            )
            .filter(Q_effective(as_of))
            .order_by("-version")
            .first()
        )
        return template or cls.default_template()

    @staticmethod
    def _watermark_for(receipt):
        if receipt.status == ReceiptStatus.REVERSED:
            return "REVERSED"
        if receipt.status == ReceiptStatus.CANCELLED:
            return "CANCELLED"
        return ""

    @classmethod
    def _allocation_context(cls, receipt, currency):
        rows = []
        show_converted = False
        for allocation in receipt.allocations.select_related("commitment").order_by("allocated_at", "created_at"):
            if allocation.converted_currency and allocation.converted_currency != currency:
                show_converted = True
            converted = cls._money(allocation.converted_amount, allocation.converted_currency)
            target_display = allocation.target_display or allocation.target_id
            if allocation.commitment_id:
                target_display = (
                    f"{allocation.commitment.commitment_number} · {target_display}".strip(" ·")
                    if target_display
                    else allocation.commitment.commitment_number
                )
            rows.append(
                {
                    "target_display": target_display or "-",
                    "narration": allocation.narration,
                    "amount": cls._money(allocation.amount, currency),
                    "converted": converted,
                    "converted_currency": allocation.converted_currency or currency,
                    "status": allocation.get_allocation_status_display(),
                }
            )
        return rows, show_converted

    @classmethod
    def build_context(cls, receipt, template):
        layout = template.layout_variables if isinstance(template.layout_variables, dict) else {}
        currency = receipt.currency or "TZS"
        unallocated = Decimal(receipt.unallocated_amount or 0)
        allocations, show_converted = cls._allocation_context(receipt, currency)
        partner_number = getattr(receipt.partner, "partner_number", None) if receipt.partner_id else None
        identity = receipt.payer_identity or partner_number or "-"
        if receipt.payer_identity and partner_number:
            identity = f"{receipt.payer_identity} / {partner_number}"
        source_reference = ""
        if receipt.source_reference_id:
            prefix = f"{receipt.source_reference_type} " if receipt.source_reference_type else ""
            source_reference = f"{prefix}{receipt.source_reference_id}"
        return {
            "company": {
                "name": layout.get("company_name", DEFAULT_COMPANY["company_name"]),
                "address": layout.get("company_address", DEFAULT_COMPANY["company_address"]),
                "phone": layout.get("company_phone", ""),
                "email": layout.get("company_email", ""),
            },
            "receipt": {
                "receipt_number": receipt.receipt_number or "Draft",
                "receipt_date": cls._display(receipt.receipt_date),
                "branch": receipt.branch_name_snapshot or str(receipt.branch) if receipt.branch_id else "-",
                "status": receipt.get_status_display(),
                "currency": currency,
                "payment_mode": receipt.get_payment_mode_display(),
                "payment_reference": receipt.payment_reference,
                "source_module": receipt.get_source_module_display(),
                "source_reference": source_reference or "-",
            },
            "payer": {
                "name": receipt.payer_name or receipt.display_partner or "-",
                "identity": identity,
            },
            "money": {
                "figures": cls._money(receipt.receipt_amount, currency),
                "words": amount_in_words(receipt.receipt_amount, currency),
                "allocated": cls._money(receipt.allocated_amount, currency),
                "unallocated": cls._money(unallocated, currency),
                "show_unallocated": unallocated > 0,
                "show_converted": show_converted,
                "converted_currency": currency,
            },
            "allocations": allocations,
            "generated": {
                "by": "",
                "at": timezone.localtime().strftime("%Y-%m-%d %H:%M:%S"),
            },
            "cashier": cls._actor_display(receipt.created_by, "-"),
            "posted_by": cls._posted_by_display(receipt),
            "watermark": cls._watermark_for(receipt),
            "preview": False,
            "template_version": template.version,
        }

    @staticmethod
    def _posted_by_display(receipt):
        if not receipt.posted_by_id:
            return "-"
        label = ReceiptPrintService._actor_display(receipt.posted_by, "")
        if receipt.posted_at:
            label = f"{label} · {ReceiptPrintService._display(receipt.posted_at)}"
        return label

    @classmethod
    def _render_html(cls, template, context):
        try:
            return Template(template.template_html).render(Context(context))
        except Exception as exc:
            raise ReceiptError(
                f"Receipt print template could not be rendered: {exc}",
                error_code="RECEIPT_ERROR",
                status_code=422,
                resolution_steps=["Open the receipt print template configuration.", "Fix the template and reprint."],
            ) from exc

    @staticmethod
    def _render_pdf(html):
        try:
            from weasyprint import HTML

            return HTML(string=html).write_pdf()
        except Exception as exc:
            raise ReceiptError(
                f"Receipt PDF could not be rendered: {exc}",
                error_code="RECEIPT_ERROR",
                status_code=422,
                resolution_steps=["Confirm the PDF engine is installed.", "Retry the printout."],
            ) from exc

    @staticmethod
    def _save_content(path, content):
        return default_storage.save(path, ContentFile(content, name=path))

    @classmethod
    def generate(cls, *, receipt, actor, request=None, template_code=None, preview=False):
        """Render a receipt printout respecting the Prompt 8 print rules.

        - DRAFT: preview only (``preview=True`` required; the permission gate on
          the endpoint still applies).
        - POSTED/PARTIALLY_ALLOCATED/FULLY_ALLOCATED: official receipt.
        - REVERSED: official receipt with a reversal watermark.
        - CANCELLED: official receipt with a cancelled watermark.
        """
        status = receipt.status
        if status == ReceiptStatus.DRAFT and not preview:
            raise invalid_status("print", status)
        if status not in {
            ReceiptStatus.DRAFT,
            ReceiptStatus.POSTED,
            ReceiptStatus.PARTIALLY_ALLOCATED,
            ReceiptStatus.FULLY_ALLOCATED,
            ReceiptStatus.REVERSED,
            ReceiptStatus.CANCELLED,
        }:
            raise invalid_status("print", status)

        watermark = cls._watermark_for(receipt)
        template = cls.resolve_template(template_code=template_code, as_of=timezone.localdate())
        context = cls.build_context(receipt, template)
        context["generated"]["by"] = cls._actor_display(actor, "-")
        context["preview"] = bool(preview)
        html = cls._render_html(template, context)
        pdf = cls._render_pdf(html)
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        number_dir = receipt.receipt_number or "DRAFT"
        prefix = f"front_office_receipts/{number_dir}/{timestamp}"
        html_reference = cls._save_content(f"{prefix}.html", html.encode("utf-8"))
        file_reference = cls._save_content(f"{prefix}.pdf", pdf)

        document = ReceiptDocument.objects.create(
            receipt=receipt,
            document_type=DOCUMENT_TYPE,
            file_reference=file_reference,
            html_reference=html_reference,
            filename=f"{receipt.receipt_number or 'draft'}.pdf",
            mime_type="application/pdf",
            status=ReceiptDocumentStatus.GENERATED,
            template=template,
            template_version=template.version,
            generated_by=actor if actor and getattr(actor, "is_authenticated", False) else None,
            generated_at=timezone.now(),
            metadata={
                "preview": bool(preview),
                "watermark": watermark or "",
                "template_code": template.code,
                "template_version": template.version,
                "variables": VARIABLES,
            },
        )
        AuditService.log_action(
            action="PRINT",
            instance=receipt,
            actor=actor,
            request=request,
            after_state={
                "document_id": str(document.pk),
                "template_code": template.code,
                "template_version": template.version,
                "watermark": watermark or "",
                "preview": bool(preview),
            },
            reason="Receipt printout generated.",
            changed_fields=[],
        )
        from apps.front_office.receipts import events as receipt_events

        receipt_events.emit_print_generated(
            receipt,
            actor=actor,
            document=document,
            template_code=template.code,
            template_version=template.version,
            preview=bool(preview),
            watermark=watermark or "",
            source_channel=getattr(request, "source_channel", None) if request else None,
        )
        return document

    @staticmethod
    def document_urls(document, request=None, *, purpose="download"):
        """Signed-ticket download URLs (authenticated print pipeline, no /media/)."""
        user = request.user if request is not None else None
        urls = {}
        for kind, reference in (("pdf", document.file_reference), ("html", document.html_reference)):
            if not reference:
                continue
            ticket = issue_download_ticket(
                document_id=document.pk,
                user_id=getattr(user, "pk", ""),
                purpose=purpose,
            )
            path = f"/api/v1/front-office/receipts/documents/{document.pk}/download/?ticket={ticket}"
            urls[f"{kind}_url"] = request.build_absolute_uri(path) if request is not None else path
        return urls
