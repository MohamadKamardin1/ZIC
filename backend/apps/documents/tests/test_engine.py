from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.cache import cache
from django.test import TestCase
from pypdf import PdfReader
from rest_framework.test import APIClient

from apps.documents.models import BrandingConfiguration, DocumentInstance, DocumentTemplate
from apps.governance.models import AuditLog
from apps.documents.services.engine import DocumentEngine, DocumentTypeRegistry
from apps.ol_parameters.models import (
    OLInvestmentFund,
    OLInvestmentFundType,
    OLPlanType,
    OLProduct as ParameterProduct,
    OLRiderSetup,
)
from apps.ol_commitments.models import OLCommitment, OLCommitmentAllocation
from apps.front_office.models import FOReceipt
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import (
    OLQuotation,
    OLQuotationBenefit,
    OLQuotationFinancialSummary,
    OLQuotationFundAllocation,
    OLQuotationInstallmentConfiguration,
    OLQuotationInstallmentRateRow,
    OLQuotationMember,
    OLQuotationPlanConfiguration,
    OLQuotationRiderSelection,
)
from apps.ordinary_life.models import OLPlan, OLProduct as LegacyProduct, OLProductVersion
from apps.partner_onboarding.models import Branch, Location
from apps.partners.models import Partner
from apps.system_parameters.models import ParameterGroup, SystemParameter
from apps.users.models import User


def seed_unified_test_templates():
    for definition in DocumentTypeRegistry.definitions():
        if definition.status != "READY":
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


class UnifiedReceiptDocumentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_unified_test_templates()
        cls.admin = User.objects.create_superuser(
            username="unified-receipt-document-admin",
            email="unified-receipt-document-admin@example.com",
            password="Strong-pass-123!",
        )
        cls.receipt = FOReceipt.objects.create(
            receipt_number="RCT-UNIFIED-001",
            amount=Decimal("125000.00"),
            payment_method="BANK_TRANSFER",
            payment_date=date.today(),
            reference="POL-UNIFIED-001",
            status="COMPLETED",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.base = f"/api/v1/front-office/receipts/{self.receipt.pk}"

    def test_receipt_print_returns_secure_preview_and_download_urls(self):
        response = self.client.post(f"{self.base}/print/", {}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        document = response.data["data"]["document"]
        self.assertTrue(document["preview_url"])
        self.assertTrue(document["signed_download_url"])
        self.assertEqual(document["preview_blob_base64_or_url"], document["preview_url"])

        signed = urlparse(document["signed_download_url"])
        ticket = parse_qs(signed.query)["ticket"][0]
        download = APIClient().get(f"{signed.path}?ticket={ticket}")
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download["Content-Type"], "application/pdf")
        pdf_bytes = b"".join(download.streaming_content)
        self.assertIn("RCT-UNIFIED-001", "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_bytes)).pages))
        self.assertTrue(AuditLog.objects.filter(action="DOCUMENT_GENERATED", object_id=document["id"], source_channel="API").exists())
        self.assertTrue(AuditLog.objects.filter(action="DOCUMENT_TICKET_DOWNLOADED", object_id=document["id"], source_channel="API").exists())

        listing = self.client.get(f"{self.base}/documents/")
        self.assertEqual(listing.status_code, 200, listing.data)
        self.assertEqual(listing.data["data"]["count"], 1)
        listed_url = listing.data["data"]["results"][0]["signed_download_url"]
        self.assertTrue(listed_url)
        self.assertTrue(listed_url.startswith("http://testserver/api/v1/documents/instances/"))
        self.assertIn("ticket=", listed_url)

    def test_inactive_receipt_template_returns_teachable_error(self):
        DocumentTemplate.objects.filter(code="RECEIPT_UNIFIED").update(is_active=False)
        response = self.client.post(f"/api/v1/documents/render/RECEIPT/{self.receipt.pk}/", {}, format="json")
        self.assertEqual(response.status_code, 409, response.data)
        self.assertEqual(response.data["code"], "TEMPLATE_NOT_FOUND")
        self.assertTrue(response.data["resolution_steps"])

    @patch("apps.documents.services.engine.default_storage.save", side_effect=OSError("storage unavailable"))
    def test_storage_failure_returns_document_render_failed_shape(self, _save):
        response = self.client.post(f"/api/v1/documents/render/RECEIPT/{self.receipt.pk}/", {}, format="json")
        self.assertEqual(response.status_code, 500, response.data)
        self.assertEqual(response.data["code"], "DOCUMENT_RENDER_FAILED")
        self.assertTrue(response.data["resolution_steps"])
        self.assertIn("correlation ID", " ".join(response.data["resolution_steps"]))


class UnifiedDocumentEngineAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_ol_quotations", verbosity=0)
        seed_unified_test_templates()
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
        self.assertEqual(data["preview_blob_base64_or_url"], data["preview_url"])
        self.assertEqual(data["instance"]["id"], data["id"])
        self.assertEqual(data["instance"]["signed_download_url"], data["signed_download_url"])
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

    def _prepare_complete_quotation(self, plan_count=4):
        plan_type = OLPlanType.objects.create(
            code=f"PDF-PLAN-TYPE-{plan_count}",
            name="With Profit Education Plan",
            plan_category="INDIVIDUAL",
        )
        parameter_product = ParameterProduct.objects.create(
            code=f"PDF-PRODUCT-{plan_count}",
            name="ZIC Education and Protection Product",
            plan_type=plan_type,
            effective_from=date.today(),
            currency="TZS",
            premium_frequencies=["ANNUAL", "MONTHLY"],
            allow_riders=True,
            allow_bonus=True,
            allow_loans=True,
            allow_surrender=True,
            allow_paidup=True,
        )
        legacy_product = LegacyProduct.objects.create(
            code=f"PDF-LEGACY-{plan_count}",
            name="ZIC Education Legacy Product",
            business_area="ORDINARY_LIFE",
        )
        product_version = OLProductVersion.objects.create(
            product=legacy_product,
            version_number=1,
            effective_from=date.today(),
            currency="TZS",
            payment_frequencies=["ANNUAL", "MONTHLY"],
            min_entry_age=18,
            max_entry_age=65,
            min_term_years=5,
            max_term_years=30,
        )
        branch = Branch.objects.create(code=f"PDF-BRANCH-{plan_count}", name="ZIC Stone Town Branch")
        location = Location.objects.create(
            branch=branch,
            code=f"PDF-LOCATION-{plan_count}",
            name="Mlandege Service Centre",
            is_active=True,
        )
        self.quotation.product = parameter_product
        self.quotation.product_version = product_version
        self.quotation.agent_partner = self.partner
        self.quotation.location_master = location
        self.quotation.identity_type = "NATIONAL ID"
        self.quotation.identity_number = "NIDA-900101-001"
        self.quotation.date_of_birth = date(1990, 1, 1)
        self.quotation.gender = "FEMALE"
        self.quotation.smoker_status = "NON_SMOKER"
        self.quotation.address = "Mlandege Road, Zanzibar City"
        self.quotation.metadata = {"terms_reference": "ZIC OL Terms v2026.1"}
        self.quotation.save()

        configurations = []
        for index in range(plan_count):
            plan = OLPlan.objects.create(
                product_version=product_version,
                code=f"EDU-{index + 1:02d}",
                name=f"Elimu Bora Plan {index + 1}",
                description="Education savings with protection and maturity benefit.",
                minimum_sum_assured=Decimal("10000.00"),
                maximum_sum_assured=Decimal("10000000.00"),
            )
            configuration = OLQuotationPlanConfiguration.objects.create(
                quotation=self.quotation,
                product_version=product_version,
                plan=plan,
                sub_product_code=f"SUB-{index + 1:02d}",
                section_number=index + 1,
                base_sum_assured=Decimal("250000.00") + index * Decimal("1000.00"),
                term_years=20,
                payment_period_years=15,
                premium_frequency="ANNUAL",
                quote_basis="SUM_ASSURED",
                estimated_maturity_value=Decimal("500000.00") + index * Decimal("1000.00"),
                premium_factor="NONE",
                joint_life=index == 0,
                mortgage=index == 0,
                personal_accident=index == 0,
                premium_waiver=index == 0,
                estimated_bonus_rate=Decimal("2.500000"),
                premium_amount=Decimal("50000.00") + index * Decimal("1000.00"),
                coverage_rules={"with_profit": True, "investment_linked": False},
            )
            configurations.append(configuration)

        OLQuotationMember.objects.create(
            quotation=self.quotation,
            member_type="POLICYHOLDER",
            partner=self.partner,
            first_name="Asha",
            last_name="Ali",
            identity_number="NIDA-900101-001",
            date_of_birth=date(1990, 1, 1),
            age_at_quote=36,
            gender="FEMALE",
            smoker_status="NON_SMOKER",
            relationship="SELF",
            member_sum_assured=Decimal("250000.00"),
            coverage_basis="FULL",
            metadata={"coverage_percent": 100},
        )
        rider = OLRiderSetup.objects.create(
            code=f"PDF-RIDER-{plan_count}",
            name="Accidental Death Benefit",
            rider_category="ACCIDENT",
            benefit_type="ACCIDENTAL_DEATH",
            calculation_basis="SUM_ASSURED",
            min_age=18,
            max_age=65,
            min_term=1,
            max_term=30,
            waiting_period_days=30,
            allows_standalone=True,
            requires_underwriting=True,
            product=parameter_product,
            effective_from=date.today(),
        )
        selection = OLQuotationRiderSelection.objects.create(
            quotation=self.quotation,
            rider=rider,
            plan_configuration=configurations[0],
            rider_sum_assured=Decimal("100000.00"),
            rider_term_years=20,
            benefit_basis="FIXED",
            benefit_value=Decimal("100000.00"),
            loading=Decimal("5.0000"),
            discount=Decimal("0.0000"),
            maximum_cap=Decimal("100000.00"),
            premium_amount=Decimal("2500.00"),
        )
        OLQuotationBenefit.objects.create(
            quotation=self.quotation,
            plan_configuration=configurations[0],
            rider_selection=selection,
            code=f"PDF-BENEFIT-{plan_count}",
            name="Accidental Death Benefit",
            benefit_type="ACCIDENTAL_DEATH",
            basis="CAPPED",
            value=Decimal("100000.00"),
            loading=Decimal("5.0000"),
            discount=Decimal("0.0000"),
            maximum_cap=Decimal("100000.00"),
            sum_assured=Decimal("100000.00"),
            premium_amount=Decimal("2500.00"),
        )
        fund_type = OLInvestmentFundType.objects.create(
            code=f"PDF-FUND-TYPE-{plan_count}",
            name="Balanced Managed Fund",
            risk_profile="BALANCED",
        )
        fund = OLInvestmentFund.objects.create(
            code=f"PDF-FUND-{plan_count}",
            name="ZIC Balanced Growth Fund",
            fund_type=fund_type,
            currency="TZS",
            valuation_frequency="DAILY",
            unit_price=Decimal("1.250000"),
            effective_from=date.today(),
        )
        OLQuotationFundAllocation.objects.create(
            quotation=self.quotation,
            plan_configuration=configurations[0],
            fund=fund,
            allocation_percentage=Decimal("100.0000"),
            allocation_amount=Decimal("500000.00"),
        )
        installment = OLQuotationInstallmentConfiguration.objects.create(
            quotation=self.quotation,
            plan_configuration=configurations[0],
            frequency="ANNUAL",
            annuity_period_years=2,
            number_of_installments=2,
            after_maturity_benefits=True,
            before_maturity_benefits=False,
            installment_amount=Decimal("250000.00"),
            first_due_date=date(2046, 1, 1),
            currency="TZS",
        )
        for sequence, rate in ((1, Decimal("60.0000")), (2, Decimal("40.0000"))):
            OLQuotationInstallmentRateRow.objects.create(
                installment_configuration=installment,
                sequence=sequence,
                description=f"Education installment {sequence}",
                rate_percent=rate,
                paid_up_rate=Decimal("55.0000"),
                period_from=sequence,
                period_to=sequence,
                rate=rate,
                charge=Decimal("250000.00") * rate / Decimal("100"),
            )
        OLQuotationFinancialSummary.objects.create(
            quotation=self.quotation,
            total_sum_assured=Decimal("250000.00"),
            total_premium=Decimal("52500.00"),
            total_rider_premium=Decimal("2500.00"),
            total_benefit_premium=Decimal("2500.00"),
            base_premium=Decimal("50000.00"),
            total_loading=Decimal("2500.00"),
            total_discount=Decimal("0.00"),
            total_tax=Decimal("750.00"),
            installment_charge=Decimal("500.00"),
            estimated_maturity_value=Decimal("500000.00"),
            recalculation_required=False,
            projections=[
                {"policy_year": 1, "premiums_paid": "50000.00", "bonuses": "1250.00", "surrender_value": "10000.00", "paid_up_value": "12000.00"},
                {"policy_year": 2, "premiums_paid": "100000.00", "bonuses": "2500.00", "surrender_value": "25000.00", "paid_up_value": "30000.00"},
            ],
            installment_payouts=[
                {"sequence": 1, "payout_amount": "300000.00"},
                {"sequence": 2, "payout_amount": "200000.00"},
            ],
            currency="TZS",
        )
        self.quotation.total_sum_assured = Decimal("250000.00")
        self.quotation.total_premium = Decimal("52500.00")
        self.quotation.save(update_fields=["total_sum_assured", "total_premium", "updated_at"])
        return configurations

    def _rendered_pdf_text(self, data):
        instance = DocumentInstance.objects.get(pk=data["id"])
        with default_storage.open(instance.file_reference, "rb") as handle:
            pdf = handle.read()
        reader = PdfReader(BytesIO(pdf))
        extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
        return instance, reader, " ".join(extracted.split())

    def test_complete_quotation_pdf_contains_every_block_and_repository_logo(self):
        self._prepare_complete_quotation(plan_count=4)
        data = self.render_document()
        instance, reader, text = self._rendered_pdf_text(data)
        for expected in (
            "QUOTATION",
            "OL-UNIFIED-DOC-001",
            "Personal Details",
            "Prospect Details",
            "Plan & Sub-Products",
            "EDU-01",
            "With Profit",
            "Joint Life",
            "Member Coverage Details",
            "Riders & Benefits",
            "Accidental Death Benefit",
            "Investment Fund Allocations",
            "ZIC Balanced Growth Fund",
            "Financial Summary",
            "Premium per Frequency",
            "Tanzanian shillings",
            "Policy-Year Projections",
            "Installment Payout Schedule",
            "Education installment 1",
            "Validity, Terms & Disclaimer",
            "does not constitute an offer",
            "Customer",
            "Agent / Intermediary",
            "Company Representative",
            "DRAFT",
        ):
            self.assertIn(expected, text, expected)
        self.assertGreaterEqual(len(reader.pages), 2)
        image_count = 0
        for page in reader.pages:
            resources = page.get("/Resources")
            if not resources:
                continue
            xobjects = resources.get_object().get("/XObject")
            if not xobjects:
                continue
            for reference in xobjects.get_object().values():
                image = reference.get_object()
                if image.get("/Subtype") == "/Image":
                    image_count += 1
        self.assertGreaterEqual(image_count, 1)
        self.assertEqual(instance.template_version, 1)

    def test_many_plan_quotation_repeats_plan_table_headers_across_pages(self):
        self._prepare_complete_quotation(plan_count=40)
        data = self.render_document()
        _, reader, text = self._rendered_pdf_text(data)
        self.assertGreaterEqual(len(reader.pages), 3)
        pages_with_plan_header = sum("Plan code" in " ".join((page.extract_text() or "").split()) for page in reader.pages)
        self.assertGreaterEqual(pages_with_plan_header, 2)
        self.assertIn("EDU-40", text)

    def test_template_variables_schema_rejects_missing_required_context(self):
        with self.assertRaisesRegex(Exception, "missing variables: plans"):
            DocumentEngine._validate_context({"quote": {}}, {"quote": "object", "plans": "array"})

    def test_proposal_summary_renders_required_blocks_without_uuid_values(self):
        self._prepare_complete_quotation(plan_count=2)
        proposal = OLProposal.objects.create(
            quotation=self.quotation,
            proposal_number="OL-PROP-UNIFIED-001",
            status="ACTIVE",
            prospect_snapshot={
                "name": "Asha Ali",
                "identity_type": "National ID",
                "identity_number": "NIDA-900101-001",
            },
            plans_snapshot=[{"code": "EDU-01", "name": "Elimu Bora Plan 1"}],
            financial_summary_snapshot={"total_premium": "52500.00"},
            created_by=self.admin,
        )
        response = self.client.post(
            f"/api/v1/documents/render/PROPOSAL_SUMMARY/{proposal.pk}/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        data = response.data["data"]
        instance, reader, text = self._rendered_pdf_text(data)
        for expected in (
            "PROPOSAL SUMMARY",
            "OL-PROP-UNIFIED-001",
            "Prospect and quotation details",
            "Proposed plans",
            "EDU-01",
            "Underwriting and approval",
            "Financial summary",
            "does not constitute an offer",
            "Customer",
            "Company Representative",
        ):
            self.assertIn(expected, text, expected)
        self.assertNotRegex(text, r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
        self.assertEqual(instance.metadata["branding_version"], 0)
        self.assertGreaterEqual(len(reader.pages), 1)

    def test_commitment_statement_renders_required_blocks_without_uuid_values(self):
        commitment = OLCommitment.objects.create(
            commitment_number="OL-CMT-UNIFIED-001",
            source_type="MANUAL",
            source_reference="MANUAL-REFERENCE-001",
            partner=self.partner,
            partner_name_snapshot="Asha Ali",
            product_name_snapshot="ZIC Education Product",
            plan_name_snapshot="Elimu Bora Plan",
            currency="TZS",
            premium_frequency="ANNUAL",
            installment_number=1,
            installment_count=12,
            due_date=date.today() + timedelta(days=30),
            premium_amount=Decimal("50000.00"),
            amount_paid=Decimal("10000.00"),
            amount_waived=Decimal("0.00"),
            status="DUE",
            created_by=self.admin,
            updated_by=self.admin,
        )
        response = self.client.post(
            f"/api/v1/documents/render/COMMITMENT_STATEMENT/{commitment.pk}/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        instance, reader, text = self._rendered_pdf_text(response.data["data"])
        for expected in (
            "COMMITMENT STATEMENT",
            "OL-CMT-UNIFIED-001",
            "Commitment details",
            "Asha Ali",
            "ZIC Education Product",
            "Elimu Bora Plan",
            "Payment summary",
            "Premium amount",
            "Outstanding balance",
            "Statement notes",
            "Finance Officer",
            "Company Representative",
        ):
            self.assertIn(expected, text, expected)
        self.assertNotRegex(text, r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
        self.assertGreaterEqual(len(reader.pages), 1)

    def test_future_document_types_return_machine_readable_pending_error(self):
        for document_type in (
            "POLICY_CONTRACT",
            "DISCHARGE_VOUCHER",
            "COMMISSION_STATEMENT",
            "DEBIT_NOTE",
            "PREMIUM_STATEMENT",
        ):
            response = self.client.post(
                f"/api/v1/documents/render/{document_type}/00000000-0000-0000-0000-000000000000/",
                {},
                format="json",
            )
            self.assertEqual(response.status_code, 409, (document_type, response.data))
            self.assertEqual(response.data["code"], "TEMPLATE_PENDING")
            self.assertIn("System Parameters", response.data["message"])

    def test_branding_update_versions_audits_and_is_used_by_next_render(self):
        first = self.client.post(
            "/api/v1/documents/branding/",
            {
                "company_name": "ZIC Branded Version One",
                "address": "Version One Address",
                "accent_colors": '{"primary":"#101010"}',
            },
            format="multipart",
        )
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(first.data["data"]["version"], 1)
        first_render = self.render_document()
        first_instance = DocumentInstance.objects.get(pk=first_render["id"])
        self.assertEqual(first_instance.metadata["branding_version"], 1)
        with default_storage.open(first_instance.preview_reference, "rb") as handle:
            self.assertIn(b"ZIC Branded Version One", handle.read())

        second = self.client.post(
            "/api/v1/documents/branding/",
            {
                "company_name": "ZIC Branded Version Two",
                "address": "Version Two Address",
                "accent_colors": '{"accent":"#202020"}',
            },
            format="multipart",
        )
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(second.data["data"]["version"], 2)
        self.assertFalse(BrandingConfiguration.objects.get(code="COMPANY_BRANDING", version=1).is_active)
        self.assertTrue(BrandingConfiguration.objects.get(code="COMPANY_BRANDING", version=2).is_active)
        self.assertTrue(AuditLog.objects.filter(action="BRANDING_VERSION_CREATED").exists())
        self.assertTrue(AuditLog.objects.filter(action="BRANDING_VERSION_RETIRED").exists())
        second_render = self.render_document()
        second_instance = DocumentInstance.objects.get(pk=second_render["id"])
        self.assertEqual(second_instance.metadata["branding_version"], 2)
        with default_storage.open(second_instance.preview_reference, "rb") as handle:
            html = handle.read().decode("utf-8")
        self.assertIn("ZIC Branded Version Two", html)
        self.assertIn("Version Two Address", html)
        self.assertEqual(second_instance.template_version, 1)

    def test_branding_get_returns_effective_version_and_history(self):
        BrandingConfiguration.objects.create(
            code="COMPANY_BRANDING",
            version=9,
            company_name="ZIC Existing Branding",
            accent_colors={"primary": "#abcdef"},
            is_active=True,
            created_by=self.admin,
        )
        response = self.client.get("/api/v1/documents/branding/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["data"]["version"], 9)
        self.assertEqual(response.data["data"]["company_name"], "ZIC Existing Branding")
        self.assertEqual(response.data["data"]["accent_colors"]["primary"], "#abcdef")

    def _prompt5_sources(self):
        self._prepare_complete_quotation(plan_count=4)
        proposal = OLProposal.objects.create(
            quotation=self.quotation,
            proposal_number="OL-PROP-PROMPT5-001",
            status="ACTIVE",
            prospect_snapshot={
                "name": "Asha Ali",
                "identity_type": "National ID",
                "identity_number": "NIDA-900101-001",
            },
            plans_snapshot=[{"code": "EDU-01", "name": "Elimu Bora Plan 1"}],
            financial_summary_snapshot={"total_premium": "52500.00"},
            created_by=self.admin,
        )
        commitment = OLCommitment.objects.create(
            commitment_number="OL-CMT-PROMPT5-001",
            source_type="MANUAL",
            source_reference="MANUAL-PROMPT5-001",
            partner=self.partner,
            partner_name_snapshot="Asha Ali",
            product_name_snapshot="ZIC Education Product",
            plan_name_snapshot="Elimu Bora Plan",
            currency="TZS",
            premium_frequency="ANNUAL",
            installment_number=1,
            installment_count=12,
            due_date=date.today() + timedelta(days=30),
            premium_amount=Decimal("50000.00"),
            amount_paid=Decimal("10000.00"),
            amount_waived=Decimal("0.00"),
            status="DUE",
            created_by=self.admin,
            updated_by=self.admin,
        )
        OLCommitmentAllocation.objects.create(
            commitment=commitment,
            receipt_reference="RCPT-PROMPT5-001",
            amount=Decimal("10000.00"),
            payment_mode="BANK_TRANSFER",
            currency="TZS",
            exchange_rate=Decimal("1.000000"),
            allocated_by=self.admin,
            source_channel="API",
        )
        return proposal, commitment

    @staticmethod
    def _image_resource_count(reader):
        count = 0
        for page in reader.pages:
            resources = page.get("/Resources")
            if not resources:
                continue
            xobjects = resources.get_object().get("/XObject")
            if not xobjects:
                continue
            for reference in xobjects.get_object().values():
                if reference.get_object().get("/Subtype") == "/Image":
                    count += 1
        return count

    def _prompt5_render_and_download(self, document_type, object_id, expected_pages, expected_text):
        response = self.client.post(
            f"/api/v1/documents/render/{document_type}/{object_id}/",
            {},
            format="json",
            HTTP_X_CORRELATION_ID=f"prompt5-{document_type.lower()}",
        )
        self.assertEqual(response.status_code, 201, response.data)
        data = response.data["data"]
        self.assertEqual(data["mime_type"], "application/pdf")
        self.assertGreaterEqual(data["page_count"], expected_pages)
        self.assertEqual(data["template_version"], 1)
        self.assertTrue(data["signed_download_url"])
        signed = urlparse(data["signed_download_url"])
        ticket = parse_qs(signed.query)["ticket"][0]
        download = self.client.get(f"{signed.path}?ticket={ticket}")
        self.assertEqual(download.status_code, 200, f"Download returned HTTP {download.status_code}")
        self.assertEqual(download["Content-Type"], "application/pdf")
        pdf = b"".join(download.streaming_content)
        self.assertGreater(len(pdf), 2000)
        reader = PdfReader(BytesIO(pdf))
        self.assertGreaterEqual(len(reader.pages), expected_pages)
        text_by_page = [" ".join((page.extract_text() or "").split()) for page in reader.pages]
        text = " ".join(text_by_page)
        for expected in expected_text:
            self.assertIn(expected, text, f"{document_type} missing {expected!r}")
        self.assertIn("Zanzibar Insurance Corporation Test", text)
        self.assertIn("Template v1", text)
        self.assertGreaterEqual(self._image_resource_count(reader), 1)
        for page_number in range(1, len(reader.pages) + 1):
            self.assertIn(f"Page {page_number} of {len(reader.pages)}", text)
        instance = DocumentInstance.objects.get(pk=data["id"])
        self.assertEqual(instance.generated_by_id, self.admin.pk)
        self.assertEqual(instance.correlation_id, f"prompt5-{document_type.lower()}")
        self.assertTrue(AuditLog.objects.filter(
            action="DOCUMENT_GENERATED",
            object_id=str(instance.pk),
            user=self.admin,
            source_channel="API",
        ).exists())
        self.assertTrue(AuditLog.objects.filter(
            action="DOCUMENT_TICKET_DOWNLOADED",
            object_id=str(instance.pk),
            user=self.admin,
            source_channel="API",
        ).exists())
        return data, instance, reader, text

    def test_prompt5_pdf_verification_matrix_covers_all_implemented_types(self):
        proposal, commitment = self._prompt5_sources()
        cases = (
            (
                "OL_QUOTATION",
                self.quotation.pk,
                2,
                (
                    "QUOTATION", "OL-UNIFIED-DOC-001", "Zanzibar Insurance Corporation Test",
                    "Plan & Sub-Products", "Member Coverage", "Riders & Benefits",
                    "Investment Fund Allocations", "Financial Summary", "Policy-Year Projections",
                    "Installment Payout Schedule", "Customer", "Agent / Intermediary",
                    "Company Representative", "does not constitute an offer",
                ),
            ),
            (
                "PROPOSAL_SUMMARY",
                proposal.pk,
                1,
                (
                    "PROPOSAL SUMMARY", "OL-PROP-PROMPT5-001", "Asha Ali", "Proposed plans",
                    "Plan code", "Underwriting and approval", "Financial summary",
                    "Customer", "Agent / Intermediary", "Company Representative",
                    "does not constitute an offer",
                ),
            ),
            (
                "COMMITMENT_STATEMENT",
                commitment.pk,
                1,
                (
                    "COMMITMENT STATEMENT", "OL-CMT-PROMPT5-001", "Asha Ali",
                    "Commitment details", "Payment summary", "Payment allocations",
                    "Receipt reference", "RCPT-PROMPT5-001", "Finance Officer",
                    "Company Representative", "does not constitute",
                ),
            ),
        )
        for document_type, object_id, expected_pages, expected_text in cases:
            with self.subTest(document_type=document_type):
                self._prompt5_render_and_download(document_type, object_id, expected_pages, expected_text)

    def test_prompt5_unauthenticated_render_and_download_are_teachable(self):
        proposal, _ = self._prompt5_sources()
        anonymous = APIClient()
        render_response = anonymous.post(
            f"/api/v1/documents/render/PROPOSAL_SUMMARY/{proposal.pk}/",
            {},
            format="json",
        )
        self.assertEqual(render_response.status_code, 401)
        self.assertIn("Authentication credentials were not provided", str(render_response.data))
        self.assertTrue(render_response["WWW-Authenticate"].startswith("Bearer"))
        data = self.render_document()
        signed = urlparse(data["signed_download_url"])
        download_response = anonymous.get(signed.path, {"ticket": "not-a-valid-ticket"})
        self.assertEqual(download_response.status_code, 403)
        self.assertIn("ticket", str(download_response.data).lower())

    def test_prompt5_signed_ticket_tamper_and_expiry_are_rejected(self):
        data = self.render_document()
        signed = urlparse(data["signed_download_url"])
        ticket = parse_qs(signed.query)["ticket"][0]
        tampered_ticket = f"{ticket[:-1]}{'A' if ticket[-1] != 'A' else 'B'}"
        tampered = APIClient().get(signed.path, {"ticket": tampered_ticket})
        self.assertEqual(tampered.status_code, 403)
        self.assertIn("invalid", str(tampered.data).lower())
        with patch.object(DocumentEngine, "TICKET_MAX_AGE_SECONDS", -1):
            expired = APIClient().get(signed.path, {"ticket": ticket})
        self.assertEqual(expired.status_code, 403)
        self.assertIn("expired", str(expired.data).lower())

    def test_prompt5_permission_matrix_denies_each_document_type_to_staff_without_entitlement(self):
        proposal, commitment = self._prompt5_sources()
        self.client.force_authenticate(self.denied_user)
        for document_type, object_id in (
            ("OL_QUOTATION", self.quotation.pk),
            ("PROPOSAL_SUMMARY", proposal.pk),
            ("COMMITMENT_STATEMENT", commitment.pk),
        ):
            with self.subTest(document_type=document_type):
                response = self.client.post(
                    f"/api/v1/documents/render/{document_type}/{object_id}/",
                    {},
                    format="json",
                )
                self.assertEqual(response.status_code, 403, response.data)
                self.assertIn("permission", str(response.data).lower())
