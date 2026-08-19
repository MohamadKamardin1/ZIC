from datetime import date, timedelta
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from apps.common.models import DomainEvent
from apps.governance.models import AuditEvent
from apps.ol_parameters.models import (
    OLAnticipatedEndowmentInstallmentRate,
    OLBonusRate,
    OLJointLifeAgeBasis,
    OLJointLifeSetup,
    OLMemberCoverConfiguration,
    OLJointLifeType,
    OLInvestmentFund,
    OLInvestmentFundType,
    OLBeneficialType,
    OLRiderSetup,
    OLPlanType,
    OLProduct,
    OLPaidUpRate,
)
from apps.ol_quotations.models import (
    OLQuotation,
    OLQuotationEvent,
    OLQuotationMember,
    OLQuotationRiderSelection,
    OLQuotationBenefit,
    QuotationStatus,
)
from apps.partner_onboarding.models import Branch, Location
from apps.partners.models import Partner, PartnerKYCProfile, PartnerType, PartnerTypeAssignment
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
            identification_type="NIN",
            identification_number="ID-OLQ-0001",
            date_of_birth=date(1990, 1, 1),
            is_active=True,
            status="ACTIVE",
        )
        cls.branch = Branch.objects.create(code="OLQ-BR", name="OL Quotations Branch")
        cls.location = Location.objects.create(
            branch=cls.branch,
            code="OLQ-LC",
            name="Quotation Location",
            is_active=True,
        )
        cls.agent_type = PartnerType.objects.create(
            code="AGENT",
            name="Ordinary Life Agent",
            is_active=True,
        )
        cls.agent_assignment = PartnerTypeAssignment.objects.create(
            partner=cls.partner,
            partner_type=cls.agent_type,
            status="ACTIVE",
        )
        PartnerKYCProfile.objects.create(
            assignment=cls.agent_assignment,
            kyc_status="VERIFIED",
        )
        cls.inactive_agent = Partner.objects.create(
            partner_number="PT-OLQ-INACTIVE",
            partner_type="INDIVIDUAL",
            party_type="INDIVIDUAL",
            first_name="Inactive",
            surname="Agent",
            email="inactive.agent.olq@example.com",
            mobile_number="255700000099",
            is_active=False,
            status="INACTIVE",
        )
        PartnerTypeAssignment.objects.create(
            partner=cls.inactive_agent,
            partner_type=cls.agent_type,
            status="ACTIVE",
        )
        cls.plan_type = OLPlanType.objects.create(
            code="IND-OLQ",
            name="Individual OL Quotations",
            plan_category="INDIVIDUAL",
        )
        cls.product = OLProduct.objects.create(
            code="LEGACY-OLQ",
            name="OLQ Term Product",
            plan_type=cls.plan_type,
            effective_from=date.today(),
            currency="TZS",
            premium_frequencies=["ANNUAL", "MONTHLY"],
            allow_riders=True,
            allow_bonus=True,
            allow_loans=True,
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
            min_entry_age=18,
            max_entry_age=65,
            min_term_years=5,
            max_term_years=20,
        )
        cls.plan = OLPlan.objects.create(
            product_version=cls.product_version,
            code="TERM-20",
            name="Twenty Year Term",
            minimum_sum_assured=Decimal("1000.00"),
            maximum_sum_assured=Decimal("10000000.00"),
        )
        OLBonusRate.objects.create(
            code="OLQ-BONUS-TEST",
            name="OLQ Test Bonus",
            product=cls.product,
            bonus_type="REVERSIONARY",
            rate=Decimal("2.50000000"),
            declaration_frequency="ANNUAL",
            effective_from=date.today(),
            is_active=True,
        )
        OLJointLifeSetup.objects.create(
            code="OLQ-JOINT-TEST",
            name="OLQ Test Joint Life",
            product=cls.product,
            joint_life_type=OLJointLifeType.FIRST_DEATH,
            age_basis=OLJointLifeAgeBasis.YOUNGER_LIFE,
            survivor_benefit_rule="FULL_BENEFIT",
            premium_adjustment_factor=Decimal("1.100000"),
            underwriting_rule="STANDARD",
            effective_from=date.today(),
            is_active=True,
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

    def personal_details_payload(self, identity_number="ID-OLQ-0001", date_of_birth="1990-01-01"):
        return {
            "quote_name": "Amina Personal Details Quote",
            "quote_date": date.today().isoformat(),
            "identity_type": "NIN",
            "identity_number": identity_number,
            "date_of_birth": date_of_birth,
            "gender": "FEMALE",
            "smoker_status": "NON_SMOKER",
            "location_id": str(self.location.pk),
            "agent_id": str(self.partner.pk),
            "address": "Stone Town, Zanzibar",
        }

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

    def test_work_queue_list_returns_table_columns_and_action_metadata(self):
        draft = self.create_draft()
        response = self.client.get("/api/v1/ol/quotations/quotations/?per_page=10")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["pagination"]["total"], 1)
        row = response.data["data"][0]
        self.assertEqual(row["id"], draft["id"])
        self.assertEqual(
            {
                "quote_number",
                "quote_name",
                "prospect_name",
                "plans_summary",
                "plan_count",
                "total_premium",
                "currency",
                "status",
                "status_badge",
                "version",
                "quote_date",
                "agent",
                "created_by",
                "row_actions",
            },
            set(row) - {"id"},
        )
        self.assertEqual(row["status_badge"]["code"], QuotationStatus.DRAFT)
        self.assertTrue(row["row_actions"]["view"]["visible"])
        self.assertTrue(row["row_actions"]["edit"]["visible"])
        self.assertTrue(row["row_actions"]["finalize"]["visible"])
        self.assertFalse(row["row_actions"]["revise"]["visible"])
        self.assertFalse(row["row_actions"]["print"]["visible"])
        self.assertFalse(row["row_actions"]["convert_to_proposal"]["visible"])
        self.assertTrue(row["row_actions"]["delete"]["visible"])

    def test_work_queue_search_and_filters_cover_identity_plan_agent_location_and_date(self):
        draft = self.create_draft()
        quotation = OLQuotation.objects.get(pk=draft["id"])
        quotation.quote_name = "Amina Annual Protection"
        quotation.identity_number = "NIDA-QUEUE-001"
        quotation.location = "Zanzibar Urban"
        quotation.quote_date = date(2026, 1, 15)
        quotation.agent = self.officer
        quotation.save(update_fields=["quote_name", "identity_number", "location", "quote_date", "agent", "updated_at"])
        self.populate_wizard(draft["id"])

        for query in ["Amina Annual", "NIDA-QUEUE-001"]:
            response = self.client.get(f"/api/v1/ol/quotations/quotations/?search={query}")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["pagination"]["total"], 1, query)

        for query in [
            "status=DRAFT",
            "status=DRAFT,FINALIZED",
            "plan=TERM-20",
            "agent=ol-quotation-officer",
            "location=Urban",
            "quote_date_from=2026-01-01&quote_date_to=2026-01-31",
        ]:
            response = self.client.get(f"/api/v1/ol/quotations/quotations/?{query}")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["pagination"]["total"], 1, query)

        response = self.client.get("/api/v1/ol/quotations/quotations/?quote_date_from=not-a-date")
        self.assertEqual(response.status_code, 400, response.data)

    def test_work_queue_action_visibility_changes_by_status_and_permissions(self):
        draft = self.create_draft()
        self.populate_wizard(draft["id"])
        finalized = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/finalize/", {}, format="json"
        )
        self.assertEqual(finalized.status_code, 200, finalized.data)

        row = self.client.get("/api/v1/ol-quotations/quotations/").data["data"][0]
        actions = row["row_actions"]
        self.assertFalse(actions["edit"]["visible"])
        self.assertTrue(actions["revise"]["visible"])
        self.assertTrue(actions["print"]["visible"])
        self.assertFalse(actions["convert_to_proposal"]["visible"])
        self.assertFalse(actions["delete"]["visible"])

        quotation = OLQuotation.objects.get(pk=draft["id"])
        quotation.partner_verified = True
        quotation.save(update_fields=["partner_verified", "updated_at"])
        row = self.client.get("/api/v1/ol-quotations/quotations/").data["data"][0]
        self.assertTrue(row["row_actions"]["convert_to_proposal"]["visible"])

        self.client.force_authenticate(self.viewer)
        row = self.client.get("/api/v1/ol-quotations/quotations/").data["data"][0]
        self.assertFalse(row["row_actions"]["edit"]["visible"])
        self.assertFalse(row["row_actions"]["finalize"]["visible"])
        self.assertFalse(row["row_actions"]["print"]["visible"])
        self.assertTrue(row["row_actions"]["view"]["visible"])

    def test_work_queue_actions_are_enforced_and_audited(self):
        draft = self.create_draft()
        self.populate_wizard(draft["id"])
        response = self.client.get(f"/api/v1/ol-quotations/quotations/{draft['id']}/print/")
        self.assertEqual(response.status_code, 400, response.data)

        finalized = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/finalize/", {}, format="json"
        )
        self.assertEqual(finalized.status_code, 200, finalized.data)
        response = self.client.get(f"/api/v1/ol-quotations/quotations/{draft['id']}/print/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(AuditEvent.objects.filter(object_id=str(draft["id"]), action="PRINT").exists())

        revised = self.client.post(f"/api/v1/ol-quotations/quotations/{draft['id']}/revise/", {}, format="json")
        self.assertEqual(revised.status_code, 200, revised.data)
        self.assertEqual(revised.data["data"]["status"], QuotationStatus.DRAFT)
        self.assertTrue(OLQuotationEvent.objects.filter(quotation_id=draft["id"], event_type="REVISED").exists())

        deleted = self.client.delete(f"/api/v1/ol-quotations/quotations/{draft['id']}/")
        self.assertEqual(deleted.status_code, 200, deleted.data)
        self.assertTrue(AuditEvent.objects.filter(object_id=str(draft["id"]), action="DELETE").exists())

    def test_work_queue_summary_returns_kpi_counts(self):
        draft = self.create_draft()
        finalized_draft = self.create_draft()
        self.populate_wizard(finalized_draft["id"])
        finalized = self.client.post(
            f"/api/v1/ol-quotations/quotations/{finalized_draft['id']}/finalize/", {}, format="json"
        )
        self.assertEqual(finalized.status_code, 200, finalized.data)
        converted = OLQuotation.objects.get(pk=finalized_draft["id"])
        converted.partner_verified = True
        converted.save(update_fields=["partner_verified", "updated_at"])
        converted_response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{finalized_draft['id']}/convert/", {}, format="json"
        )
        self.assertEqual(converted_response.status_code, 200, converted_response.data)

        expired = self.create_draft()
        expired_obj = OLQuotation.objects.get(pk=expired["id"])
        expired_obj.status = QuotationStatus.EXPIRED
        expired_obj.save(update_fields=["status", "updated_at"])

        response = self.client.get("/api/v1/ol-quotations/quotations/summary/")
        self.assertEqual(response.status_code, 200, response.data)
        summary = response.data["data"]
        self.assertEqual(summary["drafts"], 1)
        self.assertEqual(summary["finalized"], 0)
        self.assertEqual(summary["converted"], 1)
        self.assertEqual(summary["expired"], 1)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(draft["id"] is not None, True)

    def test_admin_work_queue_columns_filters_and_search_contract(self):
        from django.contrib import admin

        quotation_admin = admin.site._registry[OLQuotation]
        self.assertTrue(
            {
                "quote_number",
                "quote_name",
                "prospect_name",
                "plans_summary",
                "plan_count",
                "total_premium",
                "currency",
                "status_badge",
                "version",
                "quote_date",
                "agent",
                "created_by",
            }.issubset(set(quotation_admin.list_display))
        )
        self.assertTrue({"status", "quote_date", "product", "agent", "location"}.issubset(set(quotation_admin.list_filter)))
        self.assertTrue({"quote_number", "quote_name", "identity_number", "location"}.issubset(set(quotation_admin.search_fields)))

    def test_personal_details_save_valid(self):
        draft = self.create_draft()
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/personal-details/",
            self.personal_details_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        quotation = OLQuotation.objects.get(pk=draft["id"])
        self.assertEqual(quotation.quote_name, "Amina Personal Details Quote")
        self.assertEqual(quotation.identity_number, "ID-OLQ-0001")
        self.assertEqual(quotation.location_master_id, self.location.pk)
        self.assertEqual(quotation.agent_partner_id, self.partner.pk)
        self.assertTrue(OLQuotationEvent.objects.filter(
            quotation=quotation,
            event_type="PERSONAL_DETAILS_UPDATED",
        ).exists())
        self.assertTrue(DomainEvent.objects.filter(
            event_type="QuotationPersonalDetailsUpdated",
            aggregate_id=str(quotation.pk),
        ).exists())

    def test_personal_details_age_computation(self):
        draft = self.create_draft()
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/personal-details/",
            self.personal_details_payload(date_of_birth="1990-08-20"),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        expected_age = date.today().year - 1990 - ((date.today().month, date.today().day) < (8, 20))
        self.assertEqual(response.data["data"]["age_at_quote"], expected_age)
        self.assertEqual(OLQuotation.objects.get(pk=draft["id"]).age_at_quote, expected_age)

    def test_personal_details_invalid_dob_future(self):
        draft = self.create_draft()
        future = (date.today() + timedelta(days=1)).isoformat()
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/personal-details/",
            self.personal_details_payload(date_of_birth=future),
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("date_of_birth", str(response.data))

    def test_personal_details_agent_options_active_only(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(
            "/api/v1/ol-quotations/quotations/personal-details-options/"
        )
        self.assertEqual(response.status_code, 200, response.data)
        options = response.data["data"]
        agent_ids = {item["id"] for item in options["agents"]}
        self.assertIn(str(self.partner.pk), agent_ids)
        self.assertNotIn(str(self.inactive_agent.pk), agent_ids)
        self.assertEqual(
            {item["value"] for item in options["smoker_statuses"]},
            {"SMOKER", "NON_SMOKER"},
        )

    def test_personal_details_partner_exists_hook_true(self):
        draft = self.create_draft()
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/personal-details/",
            self.personal_details_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertTrue(data["partner_exists"])
        self.assertEqual(data["partner_id"], str(self.partner.pk))
        self.assertTrue(data["compliant"])
        quotation = OLQuotation.objects.get(pk=draft["id"])
        self.assertEqual(quotation.linked_partner_id, self.partner.pk)
        self.assertTrue(quotation.partner_verified)

    def test_personal_details_partner_exists_hook_false(self):
        draft = self.create_draft()
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/personal-details/",
            self.personal_details_payload(identity_number="NO-MATCH-OLQ"),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertFalse(data["partner_exists"])
        self.assertIsNone(data["partner_id"])
        self.assertFalse(data["compliant"])

    def test_personal_details_step_completion_flag(self):
        draft = self.create_draft()
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/personal-details/",
            self.personal_details_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        quotation = OLQuotation.objects.get(pk=draft["id"])
        self.assertTrue(quotation.wizard_step_completion["1_personal_details"])
        self.assertTrue(response.data["data"]["duplicate_active_quotation_warning"] is False)
        self.assertEqual(response.data["data"]["quote_name"], "Amina Personal Details Quote")


    def plan_selection_payload(self, **overrides):
        payload = {
            "plans": [
                {
                    "product_version_id": str(self.product_version.pk),
                    "plan_id": str(self.plan.pk),
                    "term_years": 20,
                    "payment_period_years": 20,
                    "premium_frequency": "ANNUAL",
                    "quote_basis": "SUM_ASSURED",
                    "premium_factor": "NONE",
                    "estimated_maturity_value": "1000.00",
                    "base_sum_assured": "1000.00",
                }
            ]
        }
        payload.update(overrides)
        return payload

    def test_plan_search_returns_active_plan_card_and_parameter_badges(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/ol/plans/search/?search=TERM-20")
        self.assertEqual(response.status_code, 200, response.data)
        plans = response.data["data"]["plans"]
        self.assertEqual(len(plans), 1)
        card = plans[0]
        self.assertEqual(card["code"], "TERM-20")
        self.assertIn("WITH_PROFIT", card["badges"])
        self.assertIn("JOINT_LIFE", card["badges"])
        self.assertEqual(card["payment_frequencies"], ["ANNUAL", "MONTHLY"])

    def test_plan_selection_creates_multiple_configurations_in_selection_order(self):
        second_plan = OLPlan.objects.create(
            product_version=self.product_version,
            code="TERM-10",
            name="Ten Year Term",
            description="Shorter configured term.",
            minimum_sum_assured=Decimal("2000.00"),
            maximum_sum_assured=Decimal("10000000.00"),
        )
        draft = self.create_draft()
        payload = {
            "plans": [
                {
                    "product_version_id": str(self.product_version.pk),
                    "plan_id": str(self.plan.pk),
                    "term_years": 20,
                    "payment_period_years": 20,
                    "premium_frequency": "ANNUAL",
                    "quote_basis": "SUM_ASSURED",
                    "premium_factor": "NONE",
                    "estimated_maturity_value": "1000.00",
                    "base_sum_assured": "1000.00",
                },
                {
                    "product_version_id": str(self.product_version.pk),
                    "plan_id": str(second_plan.pk),
                    "term_years": 10,
                    "payment_period_years": 10,
                    "premium_frequency": "MONTHLY",
                    "quote_basis": "SUM_ASSURED",
                    "premium_factor": "NONE",
                    "estimated_maturity_value": "2000.00",
                    "base_sum_assured": "2000.00",
                },
            ]
        }
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/plans/",
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        configurations = response.data["data"]["configurations"]
        self.assertEqual([row["section_number"] for row in configurations], [1, 2])
        self.assertEqual([str(row["plan"]) for row in configurations], [str(self.plan.pk), str(second_plan.pk)])
        self.assertTrue(response.data["data"]["wizard_step_complete"])
        self.assertTrue(
            DomainEvent.objects.filter(
                event_type="QuotationPlanSelectionUpdated",
                aggregate_id=draft["id"],
            ).exists()
        )

    def test_plan_selection_defaults_bonus_rate_from_ol_bonus_parameter(self):
        draft = self.create_draft()
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/plans/",
            self.plan_selection_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        configuration = response.data["data"]["configurations"][0]
        self.assertEqual(Decimal(configuration["estimated_bonus_rate"]), Decimal("2.500000"))

    def test_plan_options_are_sourced_from_product_and_parameter_catalogs(self):
        draft = self.create_draft()
        response = self.client.get(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/plan-options/",
            {"plan_id": str(self.plan.pk)},
        )
        self.assertEqual(response.status_code, 200, response.data)
        options = response.data["data"]
        self.assertEqual(
            options["payment_frequencies"],
            [
                {"value": "ANNUAL", "label": "Annual"},
                {"value": "MONTHLY", "label": "Monthly"},
            ],
        )
        self.assertEqual(
            {item["value"] for item in options["quote_bases"]},
            {"SUM_ASSURED", "PREMIUM"},
        )
        self.assertEqual(
            {item["value"] for item in options["premium_factors"]},
            {"NONE", "STANDARD"},
        )
        self.assertTrue(options["plan_features"]["joint_life"])
        self.assertEqual(options["selected_plan_id"], str(self.plan.pk))

    def test_plan_selection_rejects_term_outside_product_setup(self):
        draft = self.create_draft()
        payload = self.plan_selection_payload(
            plans=[{
                **self.plan_selection_payload()["plans"][0],
                "term_years": 25,
            }]
        )
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/plans/",
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("term_years", str(response.data))

    def test_plan_selection_rejects_entry_age_outside_product_setup(self):
        draft = self.create_draft()
        personal = self.personal_details_payload(identity_number="AGE-TOO-OLD", date_of_birth="1940-01-01")
        personal_response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/personal-details/",
            personal,
            format="json",
        )
        self.assertEqual(personal_response.status_code, 200, personal_response.data)
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/plans/",
            self.plan_selection_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("age_at_quote", str(response.data))

    def test_plan_selection_rejects_frequency_not_allowed_by_product_setup(self):
        draft = self.create_draft()
        payload = self.plan_selection_payload(
            plans=[{
                **self.plan_selection_payload()["plans"][0],
                "premium_frequency": "WEEKLY",
            }]
        )
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/plans/",
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("premium_frequency", str(response.data))

    def test_plan_configuration_patch_updates_section_and_preserves_order(self):
        draft = self.create_draft()
        selection = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/plans/",
            self.plan_selection_payload(),
            format="json",
        )
        self.assertEqual(selection.status_code, 200, selection.data)
        configuration_id = selection.data["data"]["configurations"][0]["id"]
        response = self.client.patch(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/plans/{configuration_id}/",
            {
                "payment_period_years": 10,
                "estimated_maturity_value": "1500.00",
                "base_sum_assured": "1500.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        configuration = response.data["data"]["configuration"]
        self.assertEqual(configuration["payment_period_years"], 10)
        self.assertEqual(configuration["section_number"], 1)
        self.assertTrue(response.data["data"]["wizard_step_complete"])
        self.assertTrue(
            AuditEvent.objects.filter(
                object_id=draft["id"],
                action="PLAN_CONFIGURATION_UPDATED",
            ).exists()
        )

    def create_member_cover_configuration(self, **overrides):
        values = {
            "code": "OLQ-CHILD-COVER",
            "name": "Child Member Cover",
            "description": "Configured child dependent cover for quotation tests.",
            "product": self.legacy_product,
            "plan": self.plan,
            "cover_type": "DEPENDENT",
            "member_relation": "CHILD",
            "min_age": 1,
            "max_age": 17,
            "waiting_period_days": 30,
            "benefit_limit": Decimal("5000.00"),
            "premium_basis": "MEMBER_PREMIUM",
            "coverage_basis": "SUM_ASSURED",
            "effective_from": date.today(),
            "is_active": True,
        }
        values.update(overrides)
        return OLMemberCoverConfiguration.objects.create(**values)

    def prepare_member_coverage_quotation(self, *, with_configuration=False):
        if with_configuration:
            self.create_member_cover_configuration()
        draft = self.create_draft()
        personal_response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/personal-details/",
            self.personal_details_payload(),
            format="json",
        )
        self.assertEqual(personal_response.status_code, 200, personal_response.data)
        plan_response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/plans/",
            self.plan_selection_payload(),
            format="json",
        )
        self.assertEqual(plan_response.status_code, 200, plan_response.data)
        return draft

    def test_member_coverage_principal_is_automatic_and_no_extra_banner_is_returned(self):
        draft = self.prepare_member_coverage_quotation()
        response = self.client.get(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/members/"
        )
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertFalse(data["requires_additional_coverage"])
        self.assertEqual(
            data["info_banner"],
            "Selected plans do not require additional member coverage configuration. Principal member is configured automatically.",
        )
        self.assertIsNotNone(data["principal_member"])
        self.assertEqual(data["principal_member"]["relation"], "POLICYHOLDER")
        self.assertEqual(data["principal_member"]["date_of_birth"], "1990-01-01")
        self.assertEqual(data["principal_member"]["gender"], "FEMALE")
        self.assertEqual(len(data["additional_members"]), 0)
        self.assertTrue(
            OLQuotationMember.objects.filter(
                quotation_id=draft["id"],
                metadata__is_principal=True,
            ).exists()
        )

    def test_member_coverage_required_configuration_allows_additional_member(self):
        draft = self.prepare_member_coverage_quotation(with_configuration=True)
        state = self.client.get(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/members/"
        )
        self.assertEqual(state.status_code, 200, state.data)
        state_data = state.data["data"]
        self.assertTrue(state_data["requires_additional_coverage"])
        self.assertEqual(state_data["allowed_configurations"][0]["relation"], "CHILD")
        self.assertEqual(state_data["allowed_configurations"][0]["waiting_period_days"], 30)

        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/members/",
            {
                "full_name": "Asha Salim",
                "relation": "CHILD",
                "date_of_birth": "2015-01-01",
                "gender": "FEMALE",
                "sum_assured": "4000.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        data = response.data["data"]
        self.assertEqual(len(data["additional_members"]), 1)
        member = data["additional_members"][0]
        self.assertEqual(member["full_name"], "Asha Salim")
        self.assertEqual(member["relation"], "CHILD")
        self.assertEqual(member["waiting_period_days"], 30)
        self.assertEqual(member["coverage_basis"], "SUM_ASSURED")
        self.assertEqual(member["sum_assured"], "4000.00")
        self.assertTrue(data["wizard_step_complete"])
        self.assertTrue(
            AuditEvent.objects.filter(
                object_id=draft["id"],
                action="MEMBER_COVERAGE_UPDATED",
            ).exists()
        )
        self.assertTrue(
            DomainEvent.objects.filter(
                event_type="QuotationMemberCoverageUpdated",
                aggregate_id=draft["id"],
            ).exists()
        )

    def test_member_coverage_rejects_relation_age_and_benefit_limit_violations(self):
        draft = self.prepare_member_coverage_quotation(with_configuration=True)
        endpoint = f"/api/v1/ol-quotations/quotations/{draft['id']}/members/"
        base_payload = {
            "full_name": "Asha Salim",
            "relation": "CHILD",
            "date_of_birth": "2015-01-01",
            "gender": "FEMALE",
            "sum_assured": "4000.00",
        }

        relation_response = self.client.post(
            endpoint,
            {**base_payload, "relation": "SPOUSE"},
            format="json",
        )
        self.assertEqual(relation_response.status_code, 400, relation_response.data)
        self.assertIn("relation", str(relation_response.data))

        age_response = self.client.post(
            endpoint,
            {**base_payload, "full_name": "Older Salim", "date_of_birth": "1990-01-01"},
            format="json",
        )
        self.assertEqual(age_response.status_code, 400, age_response.data)
        self.assertIn("date_of_birth", str(age_response.data))

        limit_response = self.client.post(
            endpoint,
            {**base_payload, "full_name": "Limit Salim", "sum_assured": "5000.01"},
            format="json",
        )
        self.assertEqual(limit_response.status_code, 400, limit_response.data)
        self.assertIn("sum_assured", str(limit_response.data))

    def test_member_coverage_rejects_duplicates_and_principal_mutation(self):
        draft = self.prepare_member_coverage_quotation(with_configuration=True)
        endpoint = f"/api/v1/ol-quotations/quotations/{draft['id']}/members/"
        payload = {
            "full_name": "Asha Salim",
            "relation": "CHILD",
            "date_of_birth": "2015-01-01",
            "gender": "FEMALE",
            "sum_assured": "4000.00",
        }
        first = self.client.post(endpoint, payload, format="json")
        self.assertEqual(first.status_code, 201, first.data)
        duplicate = self.client.post(endpoint, payload, format="json")
        self.assertEqual(duplicate.status_code, 400, duplicate.data)
        self.assertIn("member", str(duplicate.data))

        principal_id = first.data["data"]["principal_member"]["id"]
        principal_patch = self.client.patch(
            f"{endpoint}{principal_id}/",
            {"full_name": "Cannot Change"},
            format="json",
        )
        self.assertEqual(principal_patch.status_code, 400, principal_patch.data)
        self.assertIn("principal", str(principal_patch.data).lower())

    def test_member_coverage_update_and_remove_only_affect_additional_member(self):
        draft = self.prepare_member_coverage_quotation(with_configuration=True)
        endpoint = f"/api/v1/ol-quotations/quotations/{draft['id']}/members/"
        response = self.client.post(
            endpoint,
            {
                "full_name": "Asha Salim",
                "relation": "CHILD",
                "date_of_birth": "2015-01-01",
                "gender": "FEMALE",
                "sum_assured": "4000.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        member_id = response.data["data"]["additional_members"][0]["id"]
        update = self.client.patch(
            f"{endpoint}{member_id}/",
            {"full_name": "Asha Updated", "sum_assured": "4500.00"},
            format="json",
        )
        self.assertEqual(update.status_code, 200, update.data)
        self.assertEqual(update.data["data"]["additional_members"][0]["full_name"], "Asha Updated")
        self.assertEqual(update.data["data"]["additional_members"][0]["sum_assured"], "4500.00")

        remove = self.client.delete(f"{endpoint}{member_id}/")
        self.assertEqual(remove.status_code, 200, remove.data)
        self.assertEqual(len(remove.data["data"]["additional_members"]), 0)
        self.assertIsNotNone(remove.data["data"]["principal_member"])


    def prepare_installment_quotation(self):
        draft = self.create_draft()
        personal_response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/personal-details/",
            self.personal_details_payload(),
            format="json",
        )
        self.assertEqual(personal_response.status_code, 200, personal_response.data)
        plan_response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/plans/",
            self.plan_selection_payload(),
            format="json",
        )
        self.assertEqual(plan_response.status_code, 200, plan_response.data)
        plan_config_id = plan_response.data["data"]["configurations"][0]["id"]
        return {**draft, "plan_config_id": plan_config_id}

    def test_installment_state_returns_plan_rows_with_ready_status(self):
        draft = self.prepare_installment_quotation()
        response = self.client.get(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/installments/"
        )
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(len(data["rows"]), 1)
        self.assertEqual(data["rows"][0]["status"], "READY_TO_CONFIGURE")
        self.assertTrue(data["requires_configuration"])
        self.assertFalse(data["wizard_complete"])

    def test_installment_template_without_parameter_data_returns_banner(self):
        draft = self.prepare_installment_quotation()
        response = self.client.get(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/installments/"
            f"{draft['plan_config_id']}/template/"
        )
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertFalse(data["has_template"])
        self.assertIn("No templates available", data["banner"])
        self.assertEqual(data["rate_rows"], [])

    def test_installment_template_with_parameter_data_returns_prefilled_rows(self):
        OLAnticipatedEndowmentInstallmentRate.objects.create(
            code="OLQ-ENDOW-01",
            name="OLQ Annual Endowment Installment",
            product=self.legacy_product,
            plan=self.plan,
            installment_type="ANTICIPATED_ENDOWMENT",
            frequency="ANNUAL",
            age_from=18,
            age_to=65,
            term_from=20,
            term_to=20,
            policy_year_from=1,
            policy_year_to=1,
            rate_factor=Decimal("100.00000000"),
            currency="TZS",
            effective_from=date.today(),
            is_active=True,
        )
        draft = self.prepare_installment_quotation()
        response = self.client.get(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/installments/"
            f"{draft['plan_config_id']}/template/"
        )
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertTrue(data["has_template"])
        self.assertEqual(data["available_payment_modes"], ["ANNUAL", "MONTHLY"])
        self.assertEqual(len(data["rate_rows"]), 1)
        self.assertEqual(data["rate_rows"][0]["sequence"], 1)
        self.assertEqual(data["rate_rows"][0]["rate_percent"], "100.0000")

    def test_installment_configure_saves_valid_configuration(self):
        draft = self.prepare_installment_quotation()
        endpoint = (
            f"/api/v1/ol-quotations/quotations/{draft['id']}/installments/"
            f"{draft['plan_config_id']}/configure/"
        )
        response = self.client.post(
            endpoint,
            {
                "annuity_period_years": 5,
                "payment_mode": "ANNUAL",
                "after_maturity_benefits": True,
                "before_maturity_benefits": False,
                "rate_rows": [
                    {
                        "sequence": 1,
                        "description": "First installment",
                        "rate_percent": "40.0000",
                    },
                    {
                        "sequence": 2,
                        "description": "Second installment",
                        "rate_percent": "60.0000",
                    },
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(data["total_number_of_installments"], 2)
        self.assertTrue(data["wizard_step_complete"])
        configuration = data["configuration"]
        self.assertEqual(configuration["frequency"], "ANNUAL")
        self.assertEqual(configuration["annuity_period_years"], 5)
        self.assertEqual(len(configuration["rate_rows"]), 2)

    def test_installment_configure_rejects_rate_sum_not_100(self):
        draft = self.prepare_installment_quotation()
        endpoint = (
            f"/api/v1/ol-quotations/quotations/{draft['id']}/installments/"
            f"{draft['plan_config_id']}/configure/"
        )
        response = self.client.post(
            endpoint,
            {
                "annuity_period_years": 5,
                "payment_mode": "ANNUAL",
                "rate_rows": [
                    {
                        "sequence": 1,
                        "description": "Incomplete allocation",
                        "rate_percent": "90.0000",
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("rate_rows", str(response.data))

    def test_installment_configure_rejects_annuity_period_exceeding_term(self):
        draft = self.prepare_installment_quotation()
        endpoint = (
            f"/api/v1/ol-quotations/quotations/{draft['id']}/installments/"
            f"{draft['plan_config_id']}/configure/"
        )
        response = self.client.post(
            endpoint,
            {
                "annuity_period_years": 25,
                "payment_mode": "ANNUAL",
                "rate_rows": [
                    {
                        "sequence": 1,
                        "description": "Full allocation",
                        "rate_percent": "100.0000",
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("annuity_period_years", str(response.data))

    def test_installment_configure_paid_up_rate_defaults_from_parameter(self):
        OLPaidUpRate.objects.create(
            code="OLQ-PAID-UP-01",
            name="OLQ Paid-Up Rate",
            product=self.legacy_product,
            plan=self.plan,
            table_code="OLQ-PAID-UP",
            rate_table_version="V1",
            gender="FEMALE",
            smoker_status="NON_SMOKER",
            age_from=18,
            age_to=65,
            term_from=20,
            term_to=20,
            policy_year_from=1,
            policy_year_to=1,
            rate_factor=Decimal("0.75000000"),
            row_order=1,
            effective_from=date.today(),
            is_active=True,
        )
        draft = self.prepare_installment_quotation()
        endpoint = (
            f"/api/v1/ol-quotations/quotations/{draft['id']}/installments/"
            f"{draft['plan_config_id']}/configure/"
        )
        response = self.client.post(
            endpoint,
            {
                "annuity_period_years": 5,
                "payment_mode": "ANNUAL",
                "rate_rows": [
                    {
                        "sequence": 1,
                        "description": "Full allocation",
                        "rate_percent": "100.0000",
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        rate_row = response.data["data"]["configuration"]["rate_rows"][0]
        self.assertEqual(rate_row["paid_up_rate"], "0.75000000")

    def test_installment_state_shows_configured_after_save(self):
        draft = self.prepare_installment_quotation()
        configure_endpoint = (
            f"/api/v1/ol-quotations/quotations/{draft['id']}/installments/"
            f"{draft['plan_config_id']}/configure/"
        )
        configure_response = self.client.post(
            configure_endpoint,
            {
                "annuity_period_years": 5,
                "payment_mode": "MONTHLY",
                "rate_rows": [
                    {
                        "sequence": 1,
                        "description": "Configured installment",
                        "rate_percent": "100.0000",
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(configure_response.status_code, 200, configure_response.data)
        state_response = self.client.get(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/installments/"
        )
        self.assertEqual(state_response.status_code, 200, state_response.data)
        row = state_response.data["data"]["rows"][0]
        self.assertEqual(row["status"], "CONFIGURED")
        self.assertEqual(row["payment_mode"], "MONTHLY")
        self.assertEqual(row["total_number_of_installments"], 1)
        self.assertTrue(state_response.data["data"]["wizard_complete"])

    def create_investment_funds(self, *, inactive=False):
        fund_type = OLInvestmentFundType.objects.create(
            code=f"FUND-TYPE-{self._testMethodName.upper()[:12]}",
            name="Balanced Fund Type",
            risk_profile="BALANCED",
            is_active=True,
        )
        first = OLInvestmentFund.objects.create(
            code=f"FUND-A-{self._testMethodName.upper()[:12]}",
            name="Balanced Fund A",
            description="Primary investment fund.",
            fund_type=fund_type,
            currency="TZS",
            valuation_frequency="DAILY",
            unit_price=Decimal("100.000000"),
            effective_from=date.today(),
            is_active=True,
        )
        second = OLInvestmentFund.objects.create(
            code=f"FUND-B-{self._testMethodName.upper()[:12]}",
            name="Balanced Fund B",
            description="Secondary investment fund.",
            fund_type=fund_type,
            currency="TZS",
            valuation_frequency="MONTHLY",
            unit_price=Decimal("105.000000"),
            effective_from=date.today(),
            is_active=not inactive,
        )
        return first, second

    def prepare_investment_fund_quotation(self):
        self.product.investment_linked = True
        self.product.save(update_fields=["investment_linked", "updated_at"])
        return self.prepare_installment_quotation()

    def test_investment_funds_non_investment_plan_returns_not_applicable(self):
        draft = self.prepare_installment_quotation()
        state_response = self.client.get(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/investment-funds/"
        )
        self.assertEqual(state_response.status_code, 200, state_response.data)
        state = state_response.data["data"]
        self.assertTrue(state["not_applicable"])
        self.assertTrue(state["wizard_complete"])
        self.assertEqual(state["plan_rows"][0]["status"], "NOT_APPLICABLE")

        options_response = self.client.get(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/investment-funds/options/",
            {"plan_config_id": draft["plan_config_id"]},
        )
        self.assertEqual(options_response.status_code, 200, options_response.data)
        self.assertTrue(options_response.data["data"]["not_applicable"])
        self.assertEqual(options_response.data["data"]["funds"], [])

    def test_investment_funds_reject_allocation_sum_not_100(self):
        first, second = self.create_investment_funds()
        draft = self.prepare_investment_fund_quotation()
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/investment-funds/",
            {
                "allocations": [
                    {
                        "plan_config_id": draft["plan_config_id"],
                        "fund_id": str(first.pk),
                        "allocation_percent": "60.0000",
                    },
                    {
                        "plan_config_id": draft["plan_config_id"],
                        "fund_id": str(second.pk),
                        "allocation_percent": "30.0000",
                    },
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("100", str(response.data))

    def test_investment_funds_reject_inactive_fund(self):
        _, inactive = self.create_investment_funds(inactive=True)
        draft = self.prepare_investment_fund_quotation()
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/investment-funds/",
            {
                "allocations": [
                    {
                        "plan_config_id": draft["plan_config_id"],
                        "fund_id": str(inactive.pk),
                        "allocation_percent": "100.0000",
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("inactive", str(response.data).lower())

    def test_investment_funds_save_retrieve_and_options_are_parameter_driven(self):
        first, second = self.create_investment_funds()
        draft = self.prepare_investment_fund_quotation()
        options_response = self.client.get(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/investment-funds/options/",
            {"plan_config_id": draft["plan_config_id"]},
        )
        self.assertEqual(options_response.status_code, 200, options_response.data)
        options = options_response.data["data"]
        self.assertFalse(options["not_applicable"])
        self.assertEqual(options["quotation_currency"], "TZS")
        self.assertEqual({row["code"] for row in options["funds"]}, {first.code, second.code})
        self.assertEqual(options["funds"][0]["fund_type_name"], "Balanced Fund Type")
        self.assertIn("risk_profile", options["funds"][0])
        self.assertIn("valuation_frequency", options["funds"][0])

        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/investment-funds/",
            {
                "allocations": [
                    {
                        "plan_config_id": draft["plan_config_id"],
                        "fund_id": str(first.pk),
                        "allocation_percent": "40.0000",
                        "allocated_amount": "400.00",
                    },
                    {
                        "plan_config_id": draft["plan_config_id"],
                        "fund_id": str(second.pk),
                        "allocation_percent": "60.0000",
                        "allocated_amount": "600.00",
                    },
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertFalse(data["not_applicable"])
        self.assertTrue(data["wizard_step_complete"])
        row = data["state"]["plan_rows"][0]
        self.assertEqual(row["status"], "CONFIGURED")
        self.assertEqual(row["allocation_total"], "100.0000")
        self.assertEqual(len(row["allocations"]), 2)
        self.assertTrue(
            DomainEvent.objects.filter(
                event_type="QuotationInvestmentFundAllocationsUpdated",
                aggregate_id=draft["id"],
            ).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                action="INVESTMENT_FUND_ALLOCATIONS_UPDATED",
                object_id=str(draft["id"]),
            ).exists()
        )

        state_response = self.client.get(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/investment-funds/"
        )
        self.assertEqual(state_response.status_code, 200, state_response.data)
        state_row = state_response.data["data"]["plan_rows"][0]
        self.assertEqual(state_row["status"], "CONFIGURED")
        self.assertEqual(
            {allocation["fund_code"] for allocation in state_row["allocations"]},
            {first.code, second.code},
        )
        self.assertTrue(state_response.data["data"]["wizard_complete"])
        quotation = OLQuotation.objects.get(pk=draft["id"])
        self.assertTrue(quotation.wizard_step_completion["5_investment_funds"])
        self.assertEqual(quotation.fund_allocations.count(), 2)

    def test_investment_fund_currency_incompatibility_is_rejected(self):
        fund_type = OLInvestmentFundType.objects.create(
            code=f"FUND-TYPE-{self._testMethodName.upper()[:12]}",
            name="Foreign Currency Fund Type",
            risk_profile="CONSERVATIVE",
            is_active=True,
        )
        fund = OLInvestmentFund.objects.create(
            code=f"FUND-USD-{self._testMethodName.upper()[:12]}",
            name="USD Fund",
            fund_type=fund_type,
            currency="USD",
            valuation_frequency="DAILY",
            unit_price=Decimal("1.000000"),
            effective_from=date.today(),
            is_active=True,
        )
        draft = self.prepare_investment_fund_quotation()
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/investment-funds/",
            {
                "allocations": [
                    {
                        "plan_config_id": draft["plan_config_id"],
                        "fund_id": str(fund.pk),
                        "allocation_percent": "100.0000",
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("compatible", str(response.data).lower())


    def create_quotation_rider(self, *, code=None, min_age=18, max_age=65, rider_category="ACCIDENT", benefit_type="ACCIDENTAL_DEATH", allows_standalone=False, plan=None):
        code = code or f"RIDER-{self._testMethodName.upper()[:18]}"
        return OLRiderSetup.objects.create(
            code=code,
            name="Accidental Death Rider",
            description="Quotation rider fixture.",
            rider_category=rider_category,
            benefit_type=benefit_type,
            calculation_basis="SUM_ASSURED",
            min_age=min_age,
            max_age=max_age,
            min_term=5,
            max_term=20,
            min_sum_assured=Decimal("100.00"),
            max_sum_assured=Decimal("10000000.00"),
            waiting_period_days=30,
            allows_standalone=allows_standalone,
            requires_underwriting=True,
            product=None,
            plan=plan if plan is not None else self.plan,
            effective_from=date.today(),
            is_active=True,
        )

    def create_quotation_benefit_type(self, *, code=None):
        return OLBeneficialType.objects.create(
            code=code or f"BENEFIT-{self._testMethodName.upper()[:18]}",
            name="Accidental Death Benefit",
            description="Quotation benefit type fixture.",
            category="BENEFIT",
            calculation_basis="PERCENTAGE",
            default_ratio=Decimal("100.0000"),
            allows_multiple=True,
            effective_from=date.today(),
            is_active=True,
        )

    def prepare_rider_quotation(self, *, personal_accident=False, premium_waiver=False):
        draft = self.create_draft()
        personal_response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/personal-details/",
            self.personal_details_payload(),
            format="json",
        )
        self.assertEqual(personal_response.status_code, 200, personal_response.data)
        plan_payload = self.plan_selection_payload()
        plan_payload["plans"][0]["personal_accident"] = personal_accident
        plan_payload["plans"][0]["premium_waiver"] = premium_waiver
        plan_response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/plans/",
            plan_payload,
            format="json",
        )
        self.assertEqual(plan_response.status_code, 200, plan_response.data)
        return {**draft, "plan_config_id": plan_response.data["data"]["configurations"][0]["id"]}

    def test_rider_options_are_filtered_by_selected_plan_applicability(self):
        applicable = self.create_quotation_rider(code="RIDER-APPLICABLE", plan=self.plan)
        other_plan = OLPlan.objects.create(
            product_version=self.product_version,
            code="TERM-OTHER-RIDER",
            name="Other Rider Plan",
            minimum_sum_assured=Decimal("1000.00"),
            maximum_sum_assured=Decimal("10000000.00"),
        )
        self.create_quotation_rider(code="RIDER-OTHER-PLAN", plan=other_plan)
        draft = self.prepare_rider_quotation()
        response = self.client.get(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/riders/options/?plan_config_id={draft['plan_config_id']}"
        )
        self.assertEqual(response.status_code, 200, response.data)
        codes = {row["code"] for row in response.data["data"]["riders"]}
        self.assertIn(applicable.code, codes)
        self.assertNotIn("RIDER-OTHER-PLAN", codes)

    def test_attach_rider_validates_age_and_persists_benefit(self):
        rider = self.create_quotation_rider(code="RIDER-VALID-AGE")
        benefit_type = self.create_quotation_benefit_type()
        draft = self.prepare_rider_quotation()
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/riders/",
            {
                "selections": [
                    {
                        "rider_id": str(rider.pk),
                        "plan_config_id": draft["plan_config_id"],
                        "rider_sum_assured": "1000.00",
                        "rider_term_years": 20,
                        "beneficial_type_id": str(benefit_type.pk),
                        "benefit_basis": "CAPPED",
                        "benefit_value": "1000.00",
                        "maximum_cap": "1500.00",
                        "benefits": [
                            {
                                "beneficial_type_id": str(benefit_type.pk),
                                "basis": "CAPPED",
                                "value": "1000.00",
                                "maximum_cap": "1500.00",
                            }
                        ],
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["data"]["wizard_step_complete"])
        self.assertEqual(response.data["data"]["state"]["plan_rows"][0]["riders"][0]["benefit_basis"], "CAPPED")
        self.assertEqual(OLQuotationRiderSelection.objects.filter(quotation_id=draft["id"]).count(), 1)
        self.assertEqual(OLQuotationBenefit.objects.filter(quotation_id=draft["id"]).count(), 1)
        self.assertTrue(AuditEvent.objects.filter(action__icontains="CREATE").exists())

    def test_attach_rider_rejects_age_outside_parameter_range(self):
        rider = self.create_quotation_rider(code="RIDER-AGE-INVALID", min_age=40, max_age=50)
        draft = self.prepare_rider_quotation()
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/riders/",
            {
                "selections": [
                    {
                        "rider_id": str(rider.pk),
                        "plan_config_id": draft["plan_config_id"],
                        "rider_sum_assured": "1000.00",
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("age", str(response.data).lower())

    def test_benefit_basis_validation_rejects_invalid_ratio_and_capped_payloads(self):
        rider = self.create_quotation_rider(code="RIDER-BASIS-VALIDATION")
        draft = self.prepare_rider_quotation()
        ratio_response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/riders/",
            {
                "selections": [{
                    "rider_id": str(rider.pk),
                    "plan_config_id": draft["plan_config_id"],
                    "rider_sum_assured": "1000.00",
                    "benefit_basis": "RATIO",
                    "benefit_value": "101.00",
                }]
            },
            format="json",
        )
        self.assertEqual(ratio_response.status_code, 400, ratio_response.data)
        capped_response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/riders/",
            {
                "selections": [{
                    "rider_id": str(rider.pk),
                    "plan_config_id": draft["plan_config_id"],
                    "rider_sum_assured": "1000.00",
                    "benefit_basis": "CAPPED",
                    "benefit_value": "1000.00",
                }]
            },
            format="json",
        )
        self.assertEqual(capped_response.status_code, 400, capped_response.data)
        self.assertIn("cap", str(capped_response.data).lower())

    def test_plan_pa_and_wp_flags_synchronize_to_parameter_riders(self):
        pa = self.create_quotation_rider(
            code="RIDER-PA-SYNC",
            rider_category="ACCIDENT",
            benefit_type="ACCIDENTAL_DEATH",
        )
        wp = self.create_quotation_rider(
            code="RIDER-WP-SYNC",
            rider_category="WAIVER",
            benefit_type="WAIVER_PREMIUM",
        )
        draft = self.prepare_rider_quotation(personal_accident=True, premium_waiver=True)
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/riders/",
            {"selections": []},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        synced = OLQuotationRiderSelection.objects.filter(quotation_id=draft["id"], metadata__synchronized_option__isnull=False)
        self.assertEqual(synced.count(), 2)
        self.assertEqual({row.rider_id for row in synced}, {pa.pk, wp.pk})
        self.assertTrue(response.data["data"]["wizard_step_complete"])
        state_response = self.client.get(f"/api/v1/ol-quotations/quotations/{draft['id']}/riders/")
        self.assertEqual(state_response.status_code, 200, state_response.data)
        self.assertEqual(len(state_response.data["data"]["plan_rows"][0]["riders"]), 2)

    def test_rider_options_endpoint_returns_benefit_type_parameters(self):
        rider = self.create_quotation_rider(code="RIDER-OPTION-BENEFIT")
        benefit_type = self.create_quotation_benefit_type(code="BENEFIT-OPTION-TYPE")
        draft = self.prepare_rider_quotation()
        response = self.client.get(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/riders/options/"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn(rider.code, {row["code"] for row in response.data["data"]["riders"]})
        self.assertIn(benefit_type.code, {row["code"] for row in response.data["data"]["benefit_types"]})

    def test_duplicate_rider_attachment_is_rejected(self):
        rider = self.create_quotation_rider(code="RIDER-DUPLICATE")
        draft = self.prepare_rider_quotation()
        payload = {"selections": [{"rider_id": str(rider.pk), "plan_config_id": draft["plan_config_id"], "rider_sum_assured": "1000.00"}]}
        first = self.client.post(f"/api/v1/ol-quotations/quotations/{draft['id']}/riders/", payload, format="json")
        self.assertEqual(first.status_code, 200, first.data)
        duplicate = self.client.post(f"/api/v1/ol-quotations/quotations/{draft['id']}/riders/", {"selections": payload["selections"] * 2}, format="json")
        self.assertEqual(duplicate.status_code, 400, duplicate.data)
        self.assertIn("duplicate", str(duplicate.data).lower())

    def test_rider_configuration_is_rejected_for_inactive_parameter(self):
        rider = self.create_quotation_rider(code="RIDER-INACTIVE")
        rider.is_active = False
        rider.save(update_fields=["is_active", "updated_at"])
        draft = self.prepare_rider_quotation()
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/riders/",
            {"selections": [{"rider_id": str(rider.pk), "plan_config_id": draft["plan_config_id"], "rider_sum_assured": "1000.00"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("inactive", str(response.data).lower())

    def test_rider_state_is_empty_and_complete_when_no_optional_rider_selected(self):
        draft = self.prepare_rider_quotation()
        response = self.client.get(f"/api/v1/ol-quotations/quotations/{draft['id']}/riders/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["data"]["wizard_complete"])
        self.assertEqual(response.data["data"]["plan_rows"][0]["status"], "READY_TO_CONFIGURE")

    def test_standalone_rule_rejects_unscoped_rider_selection(self):
        rider = self.create_quotation_rider(code="RIDER-NO-STANDALONE", allows_standalone=False)
        draft = self.create_draft()
        personal_response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/personal-details/",
            self.personal_details_payload(),
            format="json",
        )
        self.assertEqual(personal_response.status_code, 200, personal_response.data)
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/riders/",
            {"selections": [{"rider_id": str(rider.pk), "rider_sum_assured": "1000.00"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("selected plan", str(response.data).lower())

    def test_loaded_and_discounted_benefits_validate_percentage_limits(self):
        rider = self.create_quotation_rider(code="RIDER-LOAD-DISCOUNT")
        draft = self.prepare_rider_quotation()
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/riders/",
            {"selections": [{
                "rider_id": str(rider.pk),
                "plan_config_id": draft["plan_config_id"],
                "rider_sum_assured": "1000.00",
                "benefit_basis": "LOADED",
                "benefit_value": "1000.00",
                "loading": "101.00",
            }]},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("loading", str(response.data).lower())

    def test_rider_step_writes_domain_event(self):
        rider = self.create_quotation_rider(code="RIDER-EVENT")
        draft = self.prepare_rider_quotation()
        response = self.client.post(
            f"/api/v1/ol-quotations/quotations/{draft['id']}/riders/",
            {"selections": [{"rider_id": str(rider.pk), "plan_config_id": draft["plan_config_id"], "rider_sum_assured": "1000.00"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(DomainEvent.objects.filter(event_type="QuotationRidersAndBenefitsUpdated").exists())
        self.assertTrue(AuditEvent.objects.filter(action__icontains="CREATE").exists())


if __name__ == "__main__":
    pass
