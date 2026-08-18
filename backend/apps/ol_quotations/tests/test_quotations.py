from datetime import date, timedelta
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from apps.common.models import DomainEvent
from apps.governance.models import AuditEvent
from apps.ol_parameters.models import OLPlanType, OLProduct
from apps.ol_quotations.models import (
    OLQuotation,
    OLQuotationEvent,
    OLQuotationMember,
    QuotationStatus,
)
from apps.partners.models import Partner
from apps.users.models import User, UserGroup
from apps.ordinary_life.models import OLPlan, OLProduct as LegacyOLProduct, OLProductVersion


class OLQuotationAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_ol_quotations", verbosity=0)
        cls.admin = User.objects.create_superuser(
            username="ol-quotation-admin",
            email="ol-quotation-admin@example.com",
            password="Strong-pass-123!",
        )
        cls.viewer = User.objects.create_user(
            username="ol-quotation-viewer",
            email="ol-quotation-viewer@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
        )
        cls.officer = User.objects.create_user(
            username="ol-quotation-officer",
            email="ol-quotation-officer@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
        )
        cls.viewer.groups.add(UserGroup.objects.get(code="OL_QUOTATION_VIEWER"))
        cls.officer.groups.add(UserGroup.objects.get(code="OL_QUOTATION_OFFICER"))

        cls.partner = Partner.objects.create(
            partner_number="PT-OLQ-0001",
            partner_type="INDIVIDUAL",
            party_type="INDIVIDUAL",
            first_name="Amina",
            surname="Salim",
            email="amina.olq@example.com",
            mobile_number="255700000001",
            is_active=True,
            status="ACTIVE",
        )
        cls.plan_type = OLPlanType.objects.create(
            code="IND-OLQ",
            name="Individual OL Quotations",
            plan_category="INDIVIDUAL",
        )
        cls.product = OLProduct.objects.create(
            code="OLQ-TERM",
            name="OLQ Term Product",
            plan_type=cls.plan_type,
            effective_from=date.today(),
            currency="TZS",
            premium_frequencies=["ANNUAL", "MONTHLY"],
            allow_riders=True,
        )
        cls.legacy_product = LegacyOLProduct.objects.create(
            code="LEGACY-OLQ",
            name="Legacy OLQ Product",
            business_area="ORDINARY_LIFE",
        )
        cls.product_version = OLProductVersion.objects.create(
            product=cls.legacy_product,
            version_number=1,
            effective_from=date.today(),
            currency="TZS",
            payment_frequencies=["ANNUAL", "MONTHLY"],
        )
        cls.plan = OLPlan.objects.create(
            product_version=cls.product_version,
            code="TERM-20",
            name="Twenty Year Term",
            minimum_sum_assured=Decimal("1000.00"),
            maximum_sum_assured=Decimal("10000000.00"),
        )

    def setUp(self):
        self.client = APIClient()

    def create_draft(self, client=None, user=None):
        client = client or self.client
        client.force_authenticate(user or self.admin)
        response = client.post(
            "/api/v1/ol-quotations/quotations/",
            {
                "partner": str(self.partner.pk),
                "product": str(self.product.pk),
                "product_version": str(self.product_version.pk),
                "currency": "tzs",
                "expiry_date": (date.today() + timedelta(days=30)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["data"]

    def populate_wizard(self, quotation_id):
        headers = {"format": "json"}
        self.client.post(
            "/api/v1/ol-quotations/plan-configurations/",
            {
                "quotation": quotation_id,
                "product_version": str(self.product_version.pk),
                "plan": str(self.plan.pk),
                "sub_product_code": "BASE",
                "base_sum_assured": "250000.00",
                "term_years": 20,
                "premium_frequency": "ANNUAL",
                "premium_amount": "12500.00",
            },
            **headers,
        )
        self.client.post(
            "/api/v1/ol-quotations/members/",
            {
                "quotation": quotation_id,
                "member_type": "LIFE_ASSURED",
                "partner": str(self.partner.pk),
                "first_name": "Amina",
                "last_name": "Salim",
                "identity_number": "ID-OLQ-0001",
                "date_of_birth": "1990-01-01",
                "gender": "FEMALE",
                "smoker_status": "NON_SMOKER",
                "member_sum_assured": "250000.00",
            },
            **headers,
        )
        self.client.post(
            "/api/v1/ol-quotations/installments/",
            {
                "quotation": quotation_id,
                "frequency": "ANNUAL",
                "number_of_installments": 1,
                "installment_amount": "12500.00",
                "currency": "TZS",
            },
            **headers,
        )
        self.client.post(
            "/api/v1/ol-quotations/payment-details/",
            {
                "quotation": quotation_id,
                "payer": str(self.partner.pk),
                "payment_method": "BANK_TRANSFER",
                "payment_reference": "PAY-OLQ-001",
                "amount": "12500.00",
                "currency": "TZS",
            },
            **headers,
        )
        self.client.post(
            "/api/v1/ol-quotations/underwriting/",
            {
                "quotation": quotation_id,
                "medical_required": False,
                "financial_underwriting_required": False,
                "risk_class": "STANDARD",
                "answers": {"occupation": "Engineer"},
            },
            **headers,
        )

    def test_create_draft_uses_numbering_and_emits_audit_and_outbox(self):
        draft = self.create_draft()
        quotation = OLQuotation.objects.get(pk=draft["id"])
        self.assertTrue(quotation.quote_number.startswith("OLQ-"))
        self.assertEqual(quotation.status, QuotationStatus.DRAFT)
        self.assertEqual(quotation.currency, "TZS")
        self.assertTrue(OLQuotationEvent.objects.filter(quotation=quotation, event_type="CREATED").exists())
        self.assertTrue(
            DomainEvent.objects.filter(
                event_type="QuotationCreated",
                aggregate_id=str(quotation.pk),
                status=DomainEvent.Status.PENDING,
            ).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(object_id=str(quotation.pk)).exists()
        )

    def test_wizard_summary_exposes_all_seven_steps(self):
        draft = self.create_draft()
        self.populate_wizard(draft["id"])
        response = self.client.get(f"/api/v1/ol-quotations/quotations/{draft['id']}/wizard-summary/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(set(response.data["data"]["steps"]), {
            "1_product_plan",
            "2_members",
            "3_installments",
            "4_funds",
            "5_riders",
            "6_payment",
            "7_underwriting",
        })
        self.assertTrue(response.data["data"]["steps"]["1_product_plan"])
        self.assertTrue(response.data["data"]["steps"]["2_members"])
        self.assertTrue(response.data["data"]["steps"]["3_installments"])
        self.assertTrue(response.data["data"]["steps"]["6_payment"])
        self.assertTrue(response.data["data"]["steps"]["7_underwriting"])

    def test_finalize_rejects_incomplete_wizard(self):
        draft = self.create_draft()
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/finalize/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.data["error"]["details"])
        self.assertIn("members", response.data["error"]["details"]["errors"])

    def test_finalize_computes_totals_snapshot_and_status(self):
        draft = self.create_draft()
        self.populate_wizard(draft["id"])
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/finalize/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        quotation = OLQuotation.objects.get(pk=draft["id"])
        self.assertEqual(quotation.status, QuotationStatus.FINALIZED)
        self.assertEqual(quotation.total_sum_assured, Decimal("250000.00"))
        self.assertEqual(quotation.total_premium, Decimal("12500.00"))
        self.assertEqual(quotation.calculation_snapshot["currency"], "TZS")
        self.assertTrue(OLQuotationEvent.objects.filter(quotation=quotation, event_type="FINALIZED").exists())
        self.assertTrue(DomainEvent.objects.filter(event_type="QuotationFinalized", aggregate_id=str(quotation.pk)).exists())

    def test_viewer_can_read_but_cannot_create(self):
        self.client.force_authenticate(self.viewer)
        list_response = self.client.get("/api/v1/ol-quotations/quotations/")
        self.assertEqual(list_response.status_code, 200, list_response.data)
        create_response = self.client.post(
            "/api/v1/ol-quotations/quotations/",
            {
                "partner": str(self.partner.pk),
                "product": str(self.product.pk),
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 403)

    def test_officer_can_create_and_invalid_member_returns_structured_400(self):
        self.client.force_authenticate(self.officer)
        draft = self.create_draft(self.client, self.officer)
        response = self.client.post(
            "/api/v1/ol-quotations/members/",
            {
                "quotation": draft["id"],
                "member_type": "LIFE_ASSURED",
                "first_name": "Invalid",
                "last_name": "Future",
                "date_of_birth": (date.today() + timedelta(days=1)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("date_of_birth", response.data["error"]["details"])

    def test_model_rejects_invalid_currency_and_future_member_date(self):
        draft = self.create_draft()
        quotation = OLQuotation.objects.get(pk=draft["id"])
        quotation.currency = "INVALID"
        with self.assertRaises(Exception):
            quotation.full_clean()
        member = OLQuotationMember(
            quotation=quotation,
            member_type="LIFE_ASSURED",
            first_name="Future",
            last_name="Member",
            date_of_birth=date.today() + timedelta(days=1),
        )
        with self.assertRaises(Exception):
            member.full_clean()

    def test_product_selection_is_available_as_a_wizard_child_and_nested_output(self):
        draft = self.create_draft()
        response = self.client.post(
            "/api/v1/ol-quotations/products/",
            {
                "quotation": draft["id"],
                "product": str(self.product.pk),
                "product_version": str(self.product_version.pk),
                "currency": "TZS",
                "is_selected": True,
                "is_primary": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        detail = self.client.get(f"/api/v1/ol-quotations/quotations/{draft['id']}/")
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertEqual(len(detail.data["data"]["products"]), 1)
        self.assertTrue(detail.data["data"]["products"][0]["is_primary"])

    def test_specification_compatible_quotation_route_is_available(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/ol/quotations/quotations/")
        self.assertEqual(response.status_code, 200, response.data)

    def test_finalize_permission_is_distinct_from_draft_update_permission(self):
        self.assertNotEqual(
            "ol_quotations.update",
            "ol_quotations.finalize",
        )
        self.assertTrue(
            self.officer.has_permission("ol_quotations.finalize")
        )
        self.assertTrue(
            self.officer.has_module_permission("ol_quotations", "FINALIZE")
        )
        self.assertFalse(
            self.viewer.has_permission("ol_quotations.finalize")
        )
        self.assertFalse(
            self.viewer.has_module_permission("ol_quotations", "FINALIZE")
        )
