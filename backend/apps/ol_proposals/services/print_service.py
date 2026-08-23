"""Proposal summary printout: versioned HTML template → durable HTML+PDF document.

Generated documents obey the mandate by retaining both the source link
(proposal + its captured quotation version) and the template code/version used,
mirroring the quotations print seam.
"""

from datetime import date
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.template import Context, Template
from django.utils import timezone

from apps.common.models import DomainEvent
from apps.governance.services.audit_service import AuditService
from apps.ol_proposals.errors import ProposalError
from apps.ol_proposals.models import OLProposalDocument, OLProposalPrintTemplate, ProposalDocumentStatus

MODULE = "ol_proposals"
DEFAULT_TEMPLATE_CODE = "OL_PROPOSAL_PRINT"
DEFAULT_TEMPLATE_VERSION = 1
DOCUMENT_TYPE = "PROPOSAL_PRINT"

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
    .summary-box { width: 52%; margin-left: auto; margin-top: 8px; }
    .summary-box td:first-child { font-weight: 700; }
    .signature { display: table; width: 100%; margin-top: 13px; padding: 8px 9px 3px; border-top: 1px solid #d5dbe2; background: #fbfbfc; page-break-inside: avoid; }
    .signature-left, .signature-right { display: table-cell; vertical-align: bottom; }
    .signature-right { width: 28%; text-align: center; }
    .signature-line { width: 165px; border-bottom: 1px solid #67717d; height: 21px; margin-bottom: 3px; }
    .stamp { width: 55px; height: 55px; border: 2px solid #66717d; border-radius: 50%; margin: 0 auto 3px; text-align: center; padding-top: 17px; font-size: 8pt; font-weight: 800; color: #3e4852; }
    .muted { color: #64707c; }
    .small { font-size: 7pt; }
    .avoid-break { page-break-inside: avoid; }
  </style>
</head>
<body>
<div class="sheet">
  <div class="header">
    <div class="header-left"><div class="logo-wrap"><div class="logo-arc"></div><div class="logo-text"><span>ZIC</span></div></div></div>
    <div class="header-right"><strong>{{ company.name }}</strong><br>{{ company.address }}<br>{% if company.phone %}Tel: {{ company.phone }}<br>{% endif %}{% if company.email %}Email: {{ company.email }}<br>{% endif %}Generated: {{ proposal.generated_at }}</div>
  </div>
  <div class="title">ORDINARY LIFE PROPOSAL SUMMARY</div>

  <div class="info-grid avoid-break">
    <div class="info-col"><div class="section-title">Policyholder</div><dl class="kv">
      <div class="kv-row"><dt>Name:</dt><dd>{{ policyholder.name }}</dd></div>
      <div class="kv-row"><dt>ID Type / Number:</dt><dd>{{ policyholder.identity_type }} / {{ policyholder.identity_number }}</dd></div>
      <div class="kv-row"><dt>Date of Birth:</dt><dd>{{ policyholder.date_of_birth }}</dd></div>
      <div class="kv-row"><dt>Age / Gender:</dt><dd>{{ policyholder.age }} / {{ policyholder.gender }}</dd></div>
      <div class="kv-row"><dt>Address:</dt><dd>{{ policyholder.address }}</dd></div>
    </dl></div>
    <div class="info-col"><div class="section-title">Proposal Summary</div><dl class="kv">
      <div class="kv-row"><dt>Proposal Number:</dt><dd>{{ proposal.proposal_number }}</dd></div>
      <div class="kv-row"><dt>Quotation:</dt><dd>{{ proposal.quotation_number }}</dd></div>
      <div class="kv-row"><dt>Status:</dt><dd>{{ proposal.status }}</dd></div>
      <div class="kv-row"><dt>Currency:</dt><dd>{{ proposal.currency }}</dd></div>
      <div class="kv-row"><dt>Expiry Date:</dt><dd>{{ proposal.expiry_date }}</dd></div>
    </dl></div>
  </div>

  {% if intermediary or employer %}
  <div class="info-grid avoid-break">
    <div class="info-col"><div class="section-title">Intermediary</div><dl class="kv">
      <div class="kv-row"><dt>Agent:</dt><dd>{{ intermediary.name }}</dd></div>
      <div class="kv-row"><dt>Channel:</dt><dd>{{ intermediary.channel }}</dd></div>
    </dl></div>
    <div class="info-col"><div class="section-title">Employer</div><dl class="kv">
      <div class="kv-row"><dt>Employer:</dt><dd>{{ employer.name }}</dd></div>
      <div class="kv-row"><dt>Reference:</dt><dd>{{ employer.reference }}</dd></div>
      <div class="kv-row"><dt>Payroll Deduction:</dt><dd>{{ employer.payroll_deduction }}</dd></div>
    </dl></div>
  </div>
  {% endif %}

  {% if plans %}
  <div class="block"><div class="subheading">Plans and Terms</div><table class="data"><thead><tr>
    <th>Plan</th><th>Sub Product</th><th>Term</th><th>Payment Period</th><th>Frequency</th><th class="num">Sum Assured ({{ proposal.currency }})</th><th class="num">Premium ({{ proposal.currency }})</th>
  </tr></thead><tbody>{% for plan in plans %}<tr>
    <td>{{ plan.name }}</td><td>{{ plan.sub_product|default:"-" }}</td><td>{{ plan.term_years }}</td><td>{{ plan.payment_period_years|default:"-" }}</td><td>{{ plan.premium_frequency }}</td><td class="num">{{ plan.base_sum_assured }}</td><td class="num">{{ plan.premium_amount }}</td>
  </tr>{% empty %}<tr><td colspan="7" class="muted">No plan configurations recorded.</td></tr>{% endfor %}</tbody></table></div>
  {% endif %}

  {% if benefits %}
  <div class="block"><div class="subheading">Benefits</div><table class="data"><thead><tr><th>Benefit</th><th>Type</th><th>Basis</th><th class="num">Value ({{ proposal.currency }})</th><th class="num">Sum Assured ({{ proposal.currency }})</th></tr></thead><tbody>{% for benefit in benefits %}<tr>
    <td>{{ benefit.name }}</td><td>{{ benefit.benefit_type|default:"-" }}</td><td>{{ benefit.basis }}</td><td class="num">{{ benefit.value|default:"-" }}</td><td class="num">{{ benefit.sum_assured|default:"-" }}</td>
  </tr>{% endfor %}</tbody></table></div>
  {% endif %}

  {% if riders %}
  <div class="block"><div class="subheading">Riders</div><table class="data"><thead><tr><th>Rider</th><th>Basis</th><th class="num">Benefit Value ({{ proposal.currency }})</th><th class="num">Rider Sum Assured ({{ proposal.currency }})</th><th class="num">Loading (%)</th></tr></thead><tbody>{% for rider in riders %}<tr>
    <td>{{ rider.name }}</td><td>{{ rider.benefit_basis }}</td><td class="num">{{ rider.benefit_value|default:"-" }}</td><td class="num">{{ rider.rider_sum_assured|default:"-" }}</td><td class="num">{{ rider.loading }}</td>
  </tr>{% endfor %}</tbody></table></div>
  {% endif %}

  {% if beneficiaries %}
  <div class="block"><div class="subheading">Beneficiaries</div><table class="data"><thead><tr><th>Name</th><th>Identity</th><th>Type</th><th class="num">Share (%)</th><th>Primary</th><th>Guardian</th></tr></thead><tbody>{% for beneficiary in beneficiaries %}<tr>
    <td>{{ beneficiary.name }}</td><td>{{ beneficiary.identity }}</td><td>{{ beneficiary.type }}</td><td class="num">{{ beneficiary.share }}</td><td>{{ beneficiary.is_primary }}</td><td>{{ beneficiary.guardian|default:"-" }}</td>
  </tr>{% endfor %}</tbody></table></div>
  {% endif %}

  <table class="data summary-box"><tbody>
    <tr><td>Total Premium</td><td class="num"><strong>{{ premium.total_premium }}</strong></td></tr>
    <tr><td>First Premium Due Date</td><td class="num">{{ premium.first_premium_due|default:"-" }}</td></tr>
    <tr><td>First Premium Amount</td><td class="num">{{ premium.first_premium_amount|default:"-" }}</td></tr>
  </tbody></table>

  <div class="block avoid-break"><div class="subheading">Declarations</div><dl class="kv">
    <div class="kv-row"><dt>PEP:</dt><dd>{{ declarations.pep }}</dd></div>
    <div class="kv-row"><dt>AML Flag:</dt><dd>{{ declarations.aml }}</dd></div>
    <div class="kv-row"><dt>Existing Policies:</dt><dd>{{ declarations.existing_policies }}</dd></div>
    <div class="kv-row"><dt>Occupation Risk Note:</dt><dd>{{ declarations.occupation_risk }}</dd></div>
    <div class="kv-row"><dt>Free-Text Declarations:</dt><dd>{{ declarations.free_text }}</dd></div>
  </dl></div>

  <div class="signature"><div class="signature-left"><div>Prepared By: {{ prepared_by }}</div><div class="signature-line"></div><div>Signature &amp; Date</div><div class="muted small">for and on behalf of {{ company.name }}</div></div><div class="signature-right"><div class="stamp">ZIC</div><strong>{{ company.name }}</strong><br><span class="muted small">Official Stamp</span></div></div>
</div>
</body>
</html>
"""

VARIABLES = [
    "company",
    "proposal",
    "policyholder",
    "intermediary",
    "employer",
    "plans",
    "benefits",
    "riders",
    "beneficiaries",
    "premium",
    "declarations",
]


class ProposalPrintService:
    """Generate durable, source-linked proposal summary documents (HTML + PDF)."""

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
    def _partner_name(partner):
        if partner is None:
            return ""
        for attr in ("legal_name", "company_name"):
            value = getattr(partner, attr, "") or ""
            if value:
                return str(value)
        first = getattr(partner, "first_name", "") or ""
        surname = getattr(partner, "surname", "") or ""
        if (first or surname).strip():
            return f"{first} {surname}".strip()
        return getattr(partner, "partner_number", "") or ""

    @classmethod
    def default_template(cls):
        template, _created = OLProposalPrintTemplate.objects.get_or_create(
            code=DEFAULT_TEMPLATE_CODE,
            version=DEFAULT_TEMPLATE_VERSION,
            defaults={
                "name": "Ordinary Life Proposal Summary",
                "description": "Summary printout for OL proposals.",
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
            OLProposalPrintTemplate.objects.filter(
                is_active=True,
                code=(template_code or DEFAULT_TEMPLATE_CODE).strip().upper(),
            )
            .filter(Q_effective(as_of))
            .order_by("-version")
            .first()
        )
        return template or cls.default_template()

    @classmethod
    def _source_version(cls, proposal):
        version = proposal.quotation_version
        if version is not None:
            return version
        return proposal.quotation.versions.order_by("-version_number", "-created_at").first()

    @classmethod
    def build_context(cls, proposal, template):
        layout = template.layout_variables if isinstance(template.layout_variables, dict) else {}
        selected = list(proposal.plan_configs.filter(is_selected=True).select_related("plan", "product_version__product"))
        currency = proposal.currency or "TZS"
        commitment = proposal.first_premium_commitment
        source = cls._source_version(proposal)
        return {
            "company": {
                "name": layout.get("company_name", DEFAULT_COMPANY["company_name"]),
                "address": layout.get("company_address", DEFAULT_COMPANY["company_address"]),
                "phone": layout.get("company_phone", ""),
                "email": layout.get("company_email", ""),
            },
            "proposal": {
                "proposal_number": proposal.proposal_number,
                "quotation_number": proposal.quotation.quote_number if proposal.quotation_id else "",
                "source_version": source.version_number if source else None,
                "status": proposal.status,
                "currency": currency,
                "expiry_date": cls._display(proposal.expiry_date),
                "generated_at": timezone.localdate().isoformat(),
            },
            "policyholder": {
                "name": proposal.partner_name_snapshot or cls._partner_name(proposal.partner) or "—",
                "identity_type": (proposal.prospect_snapshot or {}).get("identity_type", "") or "",
                "identity_number": (proposal.prospect_snapshot or {}).get("identity_number", "") or "",
                "date_of_birth": cls._display((proposal.prospect_snapshot or {}).get("date_of_birth")),
                "age": (proposal.prospect_snapshot or {}).get("age_at_quote", "") or "",
                "gender": (proposal.prospect_snapshot or {}).get("gender", "") or "",
                "address": (proposal.prospect_snapshot or {}).get("address", "") or "",
            },
            "intermediary": {
                "name": proposal.agent_name_snapshot or cls._partner_name(proposal.agent_partner) or "-",
                "channel": proposal.intermediary_channel or "-",
            },
            "employer": {
                "name": proposal.employer_name_snapshot or cls._partner_name(proposal.employer_partner) or "-",
                "reference": proposal.employment_reference or "-",
                "payroll_deduction": "Yes" if proposal.payroll_deduction else "No",
            },
            "plans": [
                {
                    "name": config.plan_name_snapshot or getattr(config.plan, "name", "") or getattr(config.plan, "code", "") or "-",
                    "sub_product": config.sub_product_code or "",
                    "term_years": config.term_years,
                    "payment_period_years": config.payment_period_years or config.term_years,
                    "premium_frequency": config.premium_frequency,
                    "base_sum_assured": cls._money(config.base_sum_assured, currency),
                    "premium_amount": cls._money(config.premium_amount, currency),
                }
                for config in selected
            ],
            "benefits": [
                {
                    "name": benefit.name or benefit.code,
                    "benefit_type": benefit.benefit_type,
                    "basis": benefit.basis,
                    "value": cls._money(benefit.value, currency),
                    "sum_assured": cls._money(benefit.sum_assured, currency),
                }
                for benefit in proposal.benefits.filter(is_selected=True)
            ],
            "riders": [
                {
                    "name": rider.rider_name_snapshot or getattr(rider.rider, "name", "") or "-",
                    "benefit_basis": rider.benefit_basis,
                    "benefit_value": cls._money(rider.benefit_value, currency),
                    "rider_sum_assured": cls._money(rider.rider_sum_assured, currency),
                    "loading": cls._display(rider.loading),
                }
                for rider in proposal.riders.filter(is_selected=True)
            ],
            "beneficiaries": [
                {
                    "name": beneficiary.person_name,
                    "identity": f"{beneficiary.identity_type} / {beneficiary.identity_number}".strip(" /"),
                    "type": beneficiary.beneficial_type_name_snapshot or "-",
                    "share": cls._display(beneficiary.share_percent),
                    "is_primary": "Yes" if beneficiary.is_primary else "No",
                    "guardian": beneficiary.guardian_name or "",
                }
                for beneficiary in proposal.beneficiaries.all()
            ],
            "premium": {
                "total_premium": cls._money((proposal.financial_summary_snapshot or {}).get("total_premium"), currency),
                "first_premium_due": cls._display(getattr(commitment, "due_date", None)),
                "first_premium_amount": cls._money(getattr(commitment, "premium_amount", None), currency),
            },
            "declarations": {
                "pep": "Yes" if proposal.declaration_pep_flag else "No",
                "aml": "Yes" if proposal.declaration_aml_flag else "No",
                "existing_policies": proposal.existing_policies_count if proposal.existing_policies_count is not None else "-",
                "occupation_risk": proposal.occupation_risk_note or "-",
                "free_text": "; ".join(f"{k}: {v}" for k, v in (proposal.declarations_free_text or {}).items()) or "-",
            },
            "prepared_by": str(getattr(proposal.created_by, "username", None) or "") or "ZIC Proposal Team",
        }

    @classmethod
    def _render_html(cls, template, context):
        try:
            return Template(template.template_html).render(Context(context))
        except Exception as exc:
            raise ProposalError(
                f"Proposal print template could not be rendered: {exc}",
                error_code="PROPOSAL_ERROR",
                status_code=422,
                resolution_steps=["Open the proposal print template configuration.", "Fix the template and reprint."],
            ) from exc

    @staticmethod
    def _render_pdf(html):
        try:
            from weasyprint import HTML

            return HTML(string=html).write_pdf()
        except Exception as exc:
            raise ProposalError(
                f"Proposal PDF could not be rendered: {exc}",
                error_code="PROPOSAL_ERROR",
                status_code=422,
                resolution_steps=["Confirm the PDF engine is installed.", "Retry the printout."],
            ) from exc

    @staticmethod
    def _save_content(path, content):
        return default_storage.save(path, ContentFile(content, name=path))

    @classmethod
    def generate(cls, *, proposal, actor, request=None, template_code=None, preview=False):
        if proposal.status == "CANCELLED":
            raise ProposalError(
                "A cancelled proposal cannot be printed.",
                error_code="PROPOSAL_ERROR",
                status_code=422,
                resolution_steps=["Reactivate the proposal if allowed, or generate from a fresh proposal."],
            )
        if proposal.status == "EXPIRED" and not preview:
            raise ProposalError(
                "An expired proposal cannot be printed without preview.",
                error_code="PROPOSAL_ERROR",
                status_code=422,
                resolution_steps=["Enable preview mode or create a fresh proposal."],
            )

        template = cls.resolve_template(template_code=template_code, as_of=timezone.localdate())
        context = cls.build_context(proposal, template)
        html = cls._render_html(template, context)
        pdf = cls._render_pdf(html)
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        prefix = f"ol_proposals/{proposal.proposal_number}/{timestamp}"
        html_reference = cls._save_content(f"{prefix}.html", html.encode("utf-8"))
        file_reference = cls._save_content(f"{prefix}.pdf", pdf)

        source = cls._source_version(proposal)
        document = OLProposalDocument.objects.create(
            proposal=proposal,
            document_type=DOCUMENT_TYPE,
            file_reference=file_reference,
            html_reference=html_reference,
            mime_type="application/pdf",
            status=ProposalDocumentStatus.GENERATED,
            template=template,
            template_version=template.version,
            generated_by=actor if actor and getattr(actor, "is_authenticated", False) else None,
            generated_at=timezone.now(),
            metadata={
                "preview": bool(preview),
                "source_version_number": source.version_number if source else None,
                "template_code": template.code,
                "template_version": template.version,
                "variables": VARIABLES,
            },
        )
        AuditService.log_action(
            action="PRINT",
            instance=proposal,
            actor=actor,
            request=request,
            after_state={
                "document_id": str(document.pk),
                "template_code": template.code,
                "template_version": template.version,
                "source_version": source.version_number if source else None,
            },
            reason="Proposal summary printout generated.",
            changed_fields=[],
        )
        DomainEvent.objects.create(
            event_type="ProposalPrintGenerated",
            aggregate_type="OLProposal",
            aggregate_id=str(proposal.pk),
            payload={
                "proposal_id": str(proposal.pk),
                "proposal_number": proposal.proposal_number,
                "document_id": str(document.pk),
                "source_version": source.version_number if source else None,
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


def Q_effective(as_of):
    from django.db.models import Q

    return Q(effective_from__isnull=True, effective_to__isnull=True) | Q(
        effective_from__lte=as_of, effective_to__isnull=True
    ) | Q(effective_from__lte=as_of, effective_to__gte=as_of)