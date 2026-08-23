from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.documents.models import DocumentInstance, DocumentTemplate
from apps.governance.models import AuditLog
from apps.documents.services.engine import DocumentEngine
from apps.ol_quotations.models import OLQuotation
from apps.partner_onboarding.models import Branch, Location
from apps.partners.models import Partner
from apps.system_parameters.models import ParameterGroup, SystemParameter
from apps.users.models import User


class UnifiedDocumentEngineAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_ol_quotations", verbosity=0)
        cls.admin = User.objects.create_superuser(
            username="unified-document-admin",
            email="unified-document-admin@example.com",
            password="Strong-pass-123!",
        )
        cls.denied_user = User.objects.create_user(
            username="unified-document-denied",
            email="unified-document-denied@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
        )
        cls.partner = Partner.objects.create(
            partner_number="PT-UNIFIED-DOC-001",
            partner_type="INDIVIDUAL",
            party_type="INDIVIDUAL",
            first_name="Asha",
            surname="Ali",
            email="asha.unified@example.com",
            mobile_number="255700000099",
            identification_type="NIN",
            identification_number="NIN-UNIFIED-001",
            date_of_birth=date(1990, 1, 1),
            is_active=True,
            status="ACTIVE",
        )
        cls.quotation = OLQuotation.objects.create(
            quote_number="OL-UNIFIED-DOC-001",
            quote_name="Unified Engine Acceptance Quote",
            quote_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            partner=cls.partner,
            currency="TZS",
            created_by=cls.admin,
            updated_by=cls.admin,
        )
        group, _ = ParameterGroup.objects.get_or_create(
            code="UNIFIED_DOCUMENT_BRANDING_TEST",
            defaults={"name": "Unified document branding test"},
        )
        cls.branding_parameters = {
            "COMPANY_BRANDING_COMPANY_NAME": "Zanzibar Insurance Corporation Test",
            "COMPANY_BRANDING_ADDRESS": "Bima House, Mlandege Road, Zanzibar City",
            "COMPANY_BRANDING_PHONE": "+255 659 072 500",
            "COMPANY_BRANDING_EMAIL": "branding-test@zic.co.tz",
            "COMPANY_BRANDING_REGISTRATION_NUMBER": "ZIC-REG-001",
            "COMPANY_BRANDING_FOOTER_LEGAL_TEXT": "Test legal footer for generated documents.",
            "COMPANY_BRANDING_ACCENT_COLORS": {
                "primary": "#123456",
                "accent": "#654321",
                "table_header": "#eeeeee",
            },
        }
        for code, value in cls.branding_parameters.items():
            value_type = "JSON" if isinstance(value, dict) else "STRING"
            defaults = {"group": group, "name": code, "value_type": value_type, "is_active": True}
            if value_type == "JSON":
                defaults["json_value"] = value
            else:
                defaults["string_value"] = value
            SystemParameter.objects.update_or_create(code=code, defaults=defaults)
        cache.clear()

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def render_document(self):
        response = self.client.post(
            f"/api/v1/documents/render/OL_QUOTATION/{self.quotation.pk}/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["data"]

    def test_render_returns_pdf_page_count_and_source_template_provenance(self):
        data = self.render_document()
        self.assertEqual(data["mime_type"], "application/pdf")
        self.assertGreaterEqual(data["page_count"], 1)
        self.assertEqual(data["source_type"], "ol_quotations.olquotation")
        self.assertEqual(data["source_object_id"], str(self.quotation.pk))
        self.assertEqual(data["template_version"], 1)
        self.assertEqual(data["template_name"], "Ordinary Life Quotation")
        self.assertTrue(data["checksum"])
        instance = DocumentInstance.objects.get(pk=data["id"])
        self.assertEqual(instance.template_version, instance.template.version)
        self.assertEqual(instance.source_object_id, str(self.quotation.pk))
        self.assertTrue(
            AuditLog.objects.filter(
                action="DOCUMENT_GENERATED",
                object_id=str(instance.pk),
                source_channel="API",
            ).exists()
        )

    def test_branding_values_appear_in_rendered_html(self):
        data = self.render_document()
        instance = DocumentInstance.objects.get(pk=data["id"])
        with default_storage.open(instance.preview_reference, "rb") as handle:
            html = handle.read().decode("utf-8")
        self.assertIn("Zanzibar Insurance Corporation Test", html)
        self.assertIn("Bima House, Mlandege Road, Zanzibar City", html)
        self.assertIn("+255 659 072 500", html)
        self.assertIn("branding-test@zic.co.tz", html)
        self.assertIn("ZIC-REG-001", html)
        self.assertIn("Test legal footer for generated documents.", html)
        self.assertIn("#123456", html)
        self.assertIn("Template v1", html)

    def test_unauthenticated_download_returns_teachable_401(self):
        data = self.render_document()
        anonymous = APIClient()
        response = anonymous.get(f"/api/v1/documents/instances/{data['id']}/download/")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Authentication credentials were not provided", str(response.data))
        self.assertTrue(response["WWW-Authenticate"].startswith("Bearer"))

    def test_permission_denial_is_enforced_for_render_and_download(self):
        self.client.force_authenticate(self.denied_user)
        response = self.client.post(
            f"/api/v1/documents/render/OL_QUOTATION/{self.quotation.pk}/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("permission", str(response.data).lower())

    def test_signed_download_url_streams_pdf_without_bearer_and_preview_uses_bearer(self):
        data = self.render_document()
        signed = urlparse(data["signed_download_url"])
        ticket = parse_qs(signed.query)["ticket"][0]
        anonymous = APIClient()
        response = anonymous.get(f"{signed.path}?ticket={ticket}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(response["Cache-Control"], "private, no-store, max-age=0")
        self.assertIn(b"%PDF", b"".join(response.streaming_content))
        self.assertTrue(
            AuditLog.objects.filter(
                action="DOCUMENT_TICKET_DOWNLOADED",
                object_id=data["id"],
                source_channel="API",
            ).exists()
        )

        preview = urlparse(data["preview_url"])
        preview_response = self.client.get(preview.path)
        self.assertEqual(preview_response.status_code, 200)
        self.assertEqual(preview_response["Content-Type"], "text/html; charset=utf-8")
        self.assertIn(b"Zanzibar Insurance Corporation Test", b"".join(preview_response.streaming_content))

    def test_instance_list_uses_display_fields_and_source_filters(self):
        first = self.render_document()
        second = self.render_document()
        response = self.client.get(
            "/api/v1/documents/instances/",
            {
                "source_type": "ol_quotations.olquotation",
                "object_id": str(self.quotation.pk),
                "page_size": 1,
            },
        )
        self.assertEqual(response.status_code, 200, response.data)
        payload = response.data["data"]
        self.assertEqual(payload["count"], 2)
        self.assertEqual(len(payload["results"]), 1)
        row = payload["results"][0]
        self.assertEqual(row["source_display"], str(self.quotation))
        self.assertEqual(row["generated_by_display"], self.admin.username)
        self.assertNotIn("generated_by", row)
        self.assertEqual({first["source_object_id"], second["source_object_id"]}, {str(self.quotation.pk)})

    def test_rerender_creates_a_new_instance_and_preserves_history(self):
        self.render_document()
        self.render_document()
        self.assertEqual(
            DocumentInstance.objects.filter(
                document_type="OL_QUOTATION",
                source_object_id=str(self.quotation.pk),
            ).count(),
            2,
        )
        self.assertEqual(DocumentTemplate.objects.filter(code="OL_QUOTATION_UNIFIED").count(), 1)
