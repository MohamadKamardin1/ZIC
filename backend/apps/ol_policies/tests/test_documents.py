from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from pypdf import PdfReader
from rest_framework.test import APITestCase

from apps.documents.models import DocumentInstance, DocumentTemplate
from apps.ol_policies.models import Policy, PolicyBenefit, PolicyMember, PolicyRider, PolicyStatus
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner


class PolicyDocumentsTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="policy-document-admin",
            email="policy-document-admin@example.com",
            password="Strong-policy-document-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-DOC-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Asha Mohammed",
            email="asha.document@example.com",
            mobile_number="+255711800001",
            phone="+255711800001",
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-DOC-0001",
            quote_name="Document quote",
            quote_date=date.today() - timedelta(days=20),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-DOC-0001",
            status="CONVERTED",
            partner=self.partner,
            currency="TZS",
            prospect_snapshot={},
            financial_summary_snapshot={},
        )
        self.policy = Policy.objects.create(
            proposal_ref=proposal,
            partner=self.partner,
            product_plan_ref="OL_DOCUMENT_PRODUCT",
            currency="TZS",
            sum_assured=Decimal("1000000.00"),
            premium_amount=Decimal("120000.00"),
            premium_frequency="ANNUALLY",
            term_years=10,
            risk_commencement_date=date.today() - timedelta(days=20),
            maturity_date=date.today() + timedelta(days=3610),
            status=PolicyStatus.ACTIVE,
            contract_snapshot={
                "plans": [{
                    "code": "OL_DOCUMENT_PLAN",
                    "name": "Document Protection Plan",
                    "term_years": 10,
                    "payment_period_years": 10,
                    "premium_frequency": "ANNUALLY",
                    "sum_assured": "1000000.00",
                    "badges": ["With Profit"],
                }],
                "premium_schedule": [{"installment_number": 1, "due_date": date.today().isoformat(), "amount": "120000.00"}],
                "financial_summary": {"base_premium": "120000.00", "total_premium": "120000.00"},
                "legal_clauses": ["Coverage is subject to approved underwriting terms."],
            },
        )
        PolicyMember.objects.create(
            policy=self.policy,
            member_relation="PRINCIPAL",
            name="Asha Mohammed",
            dob=date(1990, 2, 3),
            gender="FEMALE",
            benefit_amount=Decimal("1000000.00"),
        )
        PolicyBenefit.objects.create(
            policy=self.policy,
            benefit_type="DEATH_BENEFIT",
            calculation_basis="SUM_ASSURED",
            amount=Decimal("1000000.00"),
        )
        PolicyRider.objects.create(
            policy=self.policy,
            rider_code="PA_RIDER",
            sum_assured=Decimal("300000.00"),
            amount=Decimal("300000.00"),
            premium=Decimal("5000.00"),
        )
        self.templates = {
            "POLICY_CONTRACT": DocumentTemplate.objects.update_or_create(
                code="POLICY_CONTRACT_UNIFIED",
                version=1,
                defaults={
                    "name": "Policy Contract",
                    "document_type": "POLICY_CONTRACT",
                    "layout_template_path": "documents/policy_contract.html",
                    "variables_schema": {
                        "policy": "object", "prospect": "object", "agent": "object", "plans": "array",
                        "members": "array", "benefits": "array", "riders": "array", "premium_schedule": "array",
                        "financial": "object", "legal_clauses": "array", "signatures": "array", "branding": "object", "quote": "object",
                    },
                    "is_active": True,
                },
            )[0],
            "POLICY_SCHEDULE": DocumentTemplate.objects.update_or_create(
                code="POLICY_SCHEDULE_UNIFIED",
                version=1,
                defaults={
                    "name": "Schedule of Benefits",
                    "document_type": "POLICY_SCHEDULE",
                    "layout_template_path": "documents/policy_schedule.html",
                    "variables_schema": {
                        "policy": "object", "prospect": "object", "plans": "array", "members": "array",
                        "benefits": "array", "riders": "array", "branding": "object", "quote": "object",
                    },
                    "is_active": True,
                },
            )[0],
        }
        self.client.force_authenticate(self.user)

    def _render(self, path):
        response = self.client.post(path, {}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response

    def test_contract_pdf_contains_policy_blocks_and_signed_download_works(self):
        response = self._render(f"/api/v1/ol/policies/{self.policy.pk}/print-contract/")
        payload = response.data["data"]
        self.assertTrue(payload["signed_download_url"])
        self.assertEqual(payload["mime_type"], "application/pdf")
        self.assertGreaterEqual(payload["page_count"], 1)
        instance = DocumentInstance.objects.get(pk=payload["id"])
        self.assertEqual(instance.document_type, "POLICY_CONTRACT")
        self.assertEqual(instance.source_type, "ol_policies.policy")
        self.assertEqual(instance.template_version, 1)

        download = urlparse(payload["signed_download_url"])
        ticket = parse_qs(download.query)["ticket"][0]
        downloaded = self.client.get(f"/api/v1/documents/instances/{instance.pk}/download/?ticket={ticket}")
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded["Content-Type"], "application/pdf")
        pdf_bytes = b"".join(downloaded.streaming_content)
        self.assertGreater(len(pdf_bytes), 1000)
        text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_bytes)).pages)
        for expected in ("POLICY CONTRACT", "POL-", "Asha Mohammed", "Policy Terms", "Legal Clauses", "Policyholder", "Company Representative"):
            self.assertIn(expected, text)

    def test_schedule_pdf_uses_same_engine_and_auditable_instance(self):
        response = self._render(f"/api/v1/ol/policies/{self.policy.pk}/print-schedule/")
        payload = response.data["data"]
        instance = DocumentInstance.objects.get(pk=payload["id"])
        self.assertEqual(instance.document_type, "POLICY_SCHEDULE")
        self.assertEqual(payload["template_name"], "Schedule of Benefits")
        self.assertTrue(payload["preview_url"])
        preview = self.client.get(urlparse(payload["preview_url"]).path)
        self.assertEqual(preview.status_code, 200)
        signed = urlparse(payload["signed_download_url"])
        ticket = parse_qs(signed.query)["ticket"][0]
        downloaded = self.client.get(f"/api/v1/documents/instances/{instance.pk}/download/?ticket={ticket}")
        self.assertEqual(downloaded.status_code, 200)
        pdf_bytes = b"".join(downloaded.streaming_content)
        text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_bytes)).pages)
        for expected in ("SCHEDULE OF BENEFITS", "Coverage Details", "Asha Mohammed", "DEATH_BENEFIT"):
            self.assertIn(expected, text)
        self.assertEqual(DocumentInstance.objects.filter(source_object_id=str(self.policy.pk), document_type="POLICY_SCHEDULE").count(), 1)

    def test_surrendered_policy_has_status_watermark_in_contract_html(self):
        self.policy.status = PolicyStatus.SURRENDERED
        self.policy.save(update_fields=["status", "updated_at"])
        response = self._render(f"/api/v1/ol/policies/{self.policy.pk}/print-contract/")
        instance = DocumentInstance.objects.get(pk=response.data["data"]["id"])
        html = self.client.get(f"/api/v1/documents/instances/{instance.pk}/preview/")
        self.assertEqual(html.status_code, 200)
        html_bytes = b"".join(html.streaming_content)
        self.assertIn(b"SURRENDERED", html_bytes)
