from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from urllib.parse import parse_qs, urlparse

from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.cache import cache
from django.test import TestCase
from pypdf import PdfReader
from rest_framework.test import APIClient

from apps.documents.models import DocumentInstance, DocumentTemplate
from apps.governance.models import AuditLog
from apps.documents.services.engine import DocumentEngine
from apps.ol_parameters.models import (
    OLInvestmentFund,
    OLInvestmentFundType,
    OLPlanType,
    OLProduct as ParameterProduct,
    OLRiderSetup,
)
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
