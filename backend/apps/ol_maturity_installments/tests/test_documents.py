from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from pypdf import PdfReader
from rest_framework.test import APIClient, APITestCase

from apps.documents.models import BrandingConfiguration, DocumentInstance, DocumentTemplate
from apps.documents.services.engine import DocumentTypeRegistry
from apps.governance.models import AuditLog
from apps.ol_maturity_installments.models import (
    InstallmentItemStatus,
    InstallmentPlanStatus,
    OLInstallmentItem,
    OLMaturityInstallmentPlan,
)
from apps.ol_policies.models import Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner

PRINT_SCHEDULE_URL = "/api/v1/ol/maturity-installments/{plan_id}/print-schedule/"
PRINT_ADVICE_URL = "/api/v1/ol/maturity-installments/{plan_id}/print-advice/"


class InstallmentDocumentsTestCase(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="installments-documents",
            email="installments-documents@example.com",
            password="Strong-documents-password-123!",
        )
        self.denied_user = get_user_model().objects.create_user(
            username="installments-document-viewer",
            email="installments-document-viewer@example.com",
            password="Strong-documents-viewer-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-MIP-DOC-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Maturity Document Policyholder",
            email="maturity.document@example.com",
            mobile_number="+255711800001",
            phone="+255711800001",
        )
        self.agent = Partner.objects.create(
            partner_number="ZIC-MIP-DOC-A-0001",
            partner_type="AGENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Maturity Document Agent",
            email="maturity.document.agent@example.com",
            mobile_number="+255711800002",
            phone="+255711800002",
        )
        self.policy = self._policy()
        self.plan = self._plan()
        self._item(1, InstallmentItemStatus.PAID, paid_date=date(2025, 1, 14), payment_reference="REF-MIP-PAY-0001")
        self._item(2, InstallmentItemStatus.SCHEDULED)
        for definition in DocumentTypeRegistry.definitions():
            if definition.document_type not in {"OL_MATURITY_SCHEDULE", "OL_MATURITY_PAYMENT_ADVICE"}:
                continue
            DocumentTemplate.objects.update_or_create(
                code=definition.template_code,
                version=1,
                defaults={
                    "name": definition.title,
                    "document_type": definition.document_type,
                    "layout_template_path": definition.layout_template_path,
                    "variables_schema": definition.variables_schema,
                    "branding_config_reference": "COMPANY_BRANDING",
                    "is_active": True,
                },
            )
        BrandingConfiguration.objects.update_or_create(
            code="COMPANY_BRANDING",
            version=1,
            defaults={
                "company_name": "Zanzibar Insurance Corporation",
                "address": "Bima House, Mlandege Road, Zanzibar City",
                "phone": "+255 659 072 500",
                "email": "info@zic.co.tz",
                "registration_number": "ZIC-REG-001",
                "footer_legal_text": "Official ZIC maturity installment document.",
                "accent_colors": {"primary": "#183a91", "accent": "#d94754", "table_header": "#edf1f4"},
                "is_active": True,
            },
        )
        self.client.force_authenticate(self.admin)

    def _policy(self):
        quotation = OLQuotation.objects.create(
            quote_number="QT-MIP-DOC-0001",
            quote_name="Document test quote",
            quote_date=date(2026, 1, 1),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-MIP-DOC-0001",
            status="POLICY_ISSUED",
            partner=self.partner,
            agent_partner=self.agent,
            currency="TZS",
        )
        return Policy.objects.create(
            policy_number="POL-MIP-DOC-0001",
            proposal_ref=proposal,
            partner=self.partner,
            agent=self.agent,
            product_plan_ref="OL_ENDOWMENT_STANDARD",
            currency="TZS",
            sum_assured=Decimal("25000000.00"),
            premium_amount=Decimal("125000.00"),
            premium_frequency="ANNUALLY",
            term_years=10,
            risk_commencement_date=date(2016, 1, 15),
            maturity_date=date(2026, 1, 14),
            status="MATURED",
        )

    def _plan(self):
        return OLMaturityInstallmentPlan.objects.create(
            policy_ref=self.policy,
            partner=self.partner,
            currency="TZS",
            total_maturity_value=Decimal("2000000.00"),
            total_payable_amount=Decimal("2000000.00"),
            installment_count=2,
            frequency="ANNUAL",
            start_date=date(2025, 1, 14),
            end_date=date(2026, 1, 14),
            status=InstallmentPlanStatus.ACTIVE,
            created_by=self.admin,
        )

    def _item(self, number, status, *, paid_date=None, payment_reference=""):
        return OLInstallmentItem.objects.create(
            plan_ref=self.plan,
            installment_number=number,
            due_date=date(2025, 1, 14) + timedelta(days=365 * (number - 1)),
            amount=Decimal("1000000.00"),
            status=status,
            paid_date=paid_date,
            payment_reference=payment_reference,
            created_by=self.admin,
        )

    def _render(self, url):
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        payload = response.data["data"]
        self.assertTrue(payload["signed_download_url"])
        self.assertTrue(payload["preview_url"])
        return payload

    def _download(self, payload):
        signed = urlparse(payload["signed_download_url"])
        ticket = parse_qs(signed.query)["ticket"][0]
        response = APIClient().get(f"{signed.path}?ticket={ticket}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        return b"".join(response.streaming_content)

    def _pdf_text(self, payload):
        pdf_bytes = self._download(payload)
        reader = PdfReader(BytesIO(pdf_bytes))
        raw = "\n".join(page.extract_text() or "" for page in reader.pages)
        return " ".join(raw.split())

    # ------------------------------------------------------------------
    # Maturity Schedule
    # ------------------------------------------------------------------

    def test_maturity_schedule_pdf_contains_required_blocks(self):
        payload = self._render(PRINT_SCHEDULE_URL.format(plan_id=self.plan.pk))
        text = self._pdf_text(payload)
        for expected in (
            "MATURITY SCHEDULE",
            self.plan.plan_number,
            "POL-MIP-DOC-0001",
            "Maturity Document Policyholder",
            "2,000,000.00",
            "Annual",
            "Due date",
            "Amount",
            "Paid",
            "Scheduled",
            "REF-MIP-PAY-0001",
            "Signature & Date",
            "Page 1 of",
            "Template v1",
            "Zanzibar Insurance Corporation",
        ):
            self.assertIn(expected, text)
        instance = DocumentInstance.objects.get(pk=payload["id"])
        self.assertEqual(instance.document_type, "OL_MATURITY_SCHEDULE")
        self.assertEqual(instance.source_type, "ol_maturity_installments.olmaturityinstallmentplan")
        self.assertEqual(instance.source_object_id, str(self.plan.pk))
        self.assertEqual(instance.template_version, 1)
        self.assertEqual(payload["template_version"], 1)

    # ------------------------------------------------------------------
    # Payment Advice
    # ------------------------------------------------------------------

    def test_payment_advice_pdf_contains_installment_payment_blocks(self):
        payload = self._render(PRINT_ADVICE_URL.format(plan_id=self.plan.pk))
        text = self._pdf_text(payload)
        for expected in (
            "PAYMENT ADVICE",
            self.plan.plan_number,
            "POL-MIP-DOC-0001",
            "Maturity Document Policyholder",
            "Payment advice",
            "Total payable",
            "Balance",
            "Due date",
            "REF-MIP-PAY-0001",
            "Page 1 of",
            "Template v1",
        ):
            self.assertIn(expected, text)
        instance = DocumentInstance.objects.get(pk=payload["id"])
        self.assertEqual(instance.document_type, "OL_MATURITY_PAYMENT_ADVICE")
        self.assertEqual(instance.source_type, "ol_maturity_installments.olmaturityinstallmentplan")
        self.assertEqual(instance.template_version, 1)

    # ------------------------------------------------------------------
    # Watermarks
    # ------------------------------------------------------------------

    def test_cancelled_plan_schedule_has_cancelled_watermark(self):
        self.plan.status = InstallmentPlanStatus.CANCELLED
        self.plan.save(update_fields=["status", "updated_at"])
        payload = self._render(PRINT_SCHEDULE_URL.format(plan_id=self.plan.pk))
        instance = DocumentInstance.objects.get(pk=payload["id"])
        html = self.client.get(f"/api/v1/documents/instances/{instance.pk}/preview/")
        self.assertEqual(html.status_code, 200)
        self.assertIn(b"CANCELLED", b"".join(html.streaming_content))

    def test_plan_with_missed_installment_has_missed_payment_watermark(self):
        missed = self.plan.items.get(installment_number=2)
        missed.status = InstallmentItemStatus.MISSED
        missed.save(update_fields=["status", "updated_at"])
        payload = self._render(PRINT_ADVICE_URL.format(plan_id=self.plan.pk))
        instance = DocumentInstance.objects.get(pk=payload["id"])
        html = self.client.get(f"/api/v1/documents/instances/{instance.pk}/preview/")
        self.assertEqual(html.status_code, 200)
        self.assertIn(b"MISSED PAYMENT", b"".join(html.streaming_content))

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    def test_print_permission_is_enforced(self):
        self.client.force_authenticate(self.denied_user)
        response = self.client.post(PRINT_SCHEDULE_URL.format(plan_id=self.plan.pk), {}, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertIn("permission", str(response.data).lower())

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def test_generation_and_download_are_audited(self):
        payload = self._render(PRINT_SCHEDULE_URL.format(plan_id=self.plan.pk))
        instance = DocumentInstance.objects.get(pk=payload["id"])
        self.assertTrue(
            AuditLog.objects.filter(action="DOCUMENT_GENERATED", object_id=str(instance.pk)).exists()
        )
        self._download(payload)
        self.assertTrue(
            AuditLog.objects.filter(action="DOCUMENT_TICKET_DOWNLOADED", object_id=str(instance.pk)).exists()
        )
