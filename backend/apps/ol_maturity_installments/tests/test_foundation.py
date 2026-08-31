from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.common.models import DomainEvent
from apps.ol_maturity_installments.admin import (
    OLInstallmentItemAdmin,
    OLMaturityInstallmentConfigAdmin,
    OLMaturityInstallmentPlanAdmin,
)
from apps.ol_maturity_installments.errors import (
    INSTALLMENT_ERROR_REGISTRY,
    not_found,
    registry_error,
)
from apps.ol_maturity_installments.events import (
    INSTALLMENT_PLAN_CREATED,
    emit_installment_plan_created,
)
from apps.ol_maturity_installments.models import (
    InstallmentItemStatus,
    InstallmentPlanStatus,
    OLInstallmentItem,
    OLMaturityInstallmentConfig,
    OLMaturityInstallmentPlan,
)
from apps.ol_maturity_installments.permissions import (
    ACTIONS,
    OLMaturityInstallmentPermission,
    has_ol_maturity_installment_permission,
)
from apps.ol_policies.models import MaturityClaim, Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner
from apps.users.models import UserPermission


class OLMaturityInstallmentFoundationTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="installments-admin",
            email="installments-admin@example.com",
            password="Strong-installments-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-MIP-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Asha Mwinyi",
            email="asha.installments@example.com",
            mobile_number="+255711100001",
            phone="+255711100001",
        )
        self.agent = Partner.objects.create(
            partner_number="ZIC-MIP-A-0001",
            partner_type="AGENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Juma Installments Agent",
            email="juma.installments@example.com",
            mobile_number="+255711100002",
            phone="+255711100002",
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-MIP-FOUNDATION-0001",
            quote_name="Maturity installments foundation quote",
            quote_date=date(2026, 1, 1),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-MIP-FOUNDATION-0001",
            status="POLICY_ISSUED",
            partner=self.partner,
            agent_partner=self.agent,
            currency="TZS",
        )
        self.policy = Policy.objects.create(
            policy_number="POL-MIP-FOUNDATION-0001",
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
        self.maturity_claim = MaturityClaim.objects.create(
            policy=self.policy,
            claim_date=date(2026, 1, 15),
            maturity_value=Decimal("25000000.00"),
            loan_deduction=Decimal("0.00"),
            net_payout=Decimal("25000000.00"),
            payout_method="INSTALLMENTS",
            status="APPROVED",
            created_by=self.user,
        )
        self.client.force_authenticate(self.user)

    def make_plan(self, *, item_count=3, status=InstallmentPlanStatus.CREATED):
        plan = OLMaturityInstallmentPlan.objects.create(
            policy_ref=self.policy,
            maturity_claim_ref=self.maturity_claim,
            partner=self.partner,
            currency="TZS",
            total_maturity_value=Decimal("30000.00"),
            total_payable_amount=Decimal("30000.00"),
            installment_count=item_count,
            frequency="MONTHLY",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 4, 1),
            status=status,
            parameter_snapshot={"installment_rate_factor": "0.10000000"},
            source_channel="WEB",
            created_by=self.user,
        )
        for number in range(1, item_count + 1):
            OLInstallmentItem.objects.create(
                plan_ref=plan,
                installment_number=number,
                due_date=date(2026, 1, 15) + timedelta(days=30 * number),
                amount=Decimal("10000.00"),
                created_by=self.user,
            )
        OLMaturityInstallmentConfig.objects.create(
            plan_ref=plan,
            calculation_basis="INSTALLMENT_RATE_ANNUITY",
            installment_rate_snapshot={"code": "IR-ENDOW-10", "rate_factor": "0.10000000", "frequency": "MONTHLY"},
            paid_up_rate_snapshot={"table_code": "PU-ENDOW-V1", "rate_factor": "0.85000000"},
            parameters_used=["OLAnticipatedEndowmentInstallmentRate", "OLPaidUpRate"],
            assumptions={"currency": "TZS", "rounding": "2dp_last_item_absorbs_remainder"},
            configured_by=self.user,
            created_by=self.user,
        )
        return plan

    def test_plan_creation_relationships_and_status_enum(self):
        plan = self.make_plan()
        self.assertTrue(plan.plan_number.startswith("MIP-"))
        self.assertEqual(plan.policy_ref, self.policy)
        self.assertEqual(plan.maturity_claim_ref, self.maturity_claim)
        self.assertEqual(plan.partner, self.partner)
        self.assertEqual(plan.currency, "TZS")
        self.assertEqual(plan.total_payable_amount, Decimal("30000.00"))
        self.assertEqual(plan.installment_count, 3)
        self.assertEqual(plan.status, InstallmentPlanStatus.CREATED)
        self.assertEqual(plan.items.count(), 3)
        self.assertEqual(plan.items.get(installment_number=1).due_date, date(2026, 2, 14))
        self.assertEqual(plan.config.calculation_basis, "INSTALLMENT_RATE_ANNUITY")
        self.assertEqual(plan.config.installment_rate_snapshot["rate_factor"], "0.10000000")

        plan.status = "NOT_A_PLAN_STATUS"
        with self.assertRaises(ValidationError):
            plan.full_clean()

    def test_item_status_enum_and_unique_installment_number(self):
        plan = self.make_plan(item_count=2)
        items = list(plan.items.order_by("installment_number"))
        self.assertEqual(items[0].status, InstallmentItemStatus.SCHEDULED)
        self.assertEqual(items[1].installment_number, 2)
        items[0].status = "NOT_AN_ITEM_STATUS"
        with self.assertRaises(ValidationError):
            items[0].full_clean()

        duplicate = OLInstallmentItem(
            plan_ref=plan,
            installment_number=1,
            due_date=date(2026, 5, 1),
            amount=Decimal("10000.00"),
        )
        with self.assertRaises(Exception):
            duplicate.full_clean()
            duplicate.save()

    def test_plan_clean_rejects_mismatched_amounts_and_dates(self):
        plan = OLMaturityInstallmentPlan(
            policy_ref=self.policy,
            partner=self.partner,
            currency="TZS",
            total_maturity_value=Decimal("30000.00"),
            total_payable_amount=Decimal("31000.00"),
            installment_count=3,
            frequency="MONTHLY",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            plan.full_clean()

    def test_error_registry_has_required_teachable_shape(self):
        required_codes = {
            "PLAN_POLICY_NOT_MATURED",
            "PLAN_CALCULATION_MISMATCH",
            "INSTALLMENT_ALREADY_PAID",
            "INSTALLMENT_PAYOUT_FAILED",
            "PLAN_PARAMETER_MISSING",
        }
        self.assertTrue(required_codes.issubset(INSTALLMENT_ERROR_REGISTRY))
        for definition in INSTALLMENT_ERROR_REGISTRY.values():
            self.assertTrue(definition["message"])
            self.assertGreaterEqual(definition["status_code"], 400)
            self.assertTrue(definition["resolution_steps"])
        error = registry_error("PLAN_CALCULATION_MISMATCH")
        self.assertEqual(error.error_code, "PLAN_CALCULATION_MISMATCH")
        self.assertTrue(error.resolution_steps)
        self.assertEqual(error.doc_ref, "docs/OL_MATURITY_INSTALLMENTS_DESIGN.md")

        not_found_error = not_found()
        self.assertEqual(not_found_error.error_code, "INSTALLMENT_PLAN_NOT_FOUND")
        self.assertTrue(not_found_error.resolution_steps)

    def test_permission_catalog_and_roles_are_registered(self):
        call_command("seed_ol_maturity_installment_permissions", verbosity=0)
        expected = {f"ol_maturity_installments.{action}" for action in ACTIONS}
        actual = set(
            UserPermission.objects.filter(module="ol_maturity_installments").values_list("codename", flat=True)
        )
        self.assertSetEqual(actual, expected)
        self.assertEqual(OLMaturityInstallmentPermission.code_for("list"), "ol_maturity_installments.view")
        self.assertEqual(
            OLMaturityInstallmentPermission.code_for("process_payment"),
            "ol_maturity_installments.process_payment",
        )
        self.assertTrue(has_ol_maturity_installment_permission(self.user, "configure"))
        self.assertEqual(
            UserPermission.objects.filter(module="ol_maturity_installments", is_active=True).count(),
            len(ACTIONS),
        )

    def test_all_models_are_registered_in_admin(self):
        for model, model_admin in (
            (OLMaturityInstallmentPlan, OLMaturityInstallmentPlanAdmin),
            (OLInstallmentItem, OLInstallmentItemAdmin),
            (OLMaturityInstallmentConfig, OLMaturityInstallmentConfigAdmin),
        ):
            self.assertTrue(admin.site.is_registered(model))
            self.assertIsInstance(admin.site._registry[model], model_admin)

    def test_domain_event_helper_can_record_plan_event(self):
        plan = self.make_plan()
        event = emit_installment_plan_created(
            plan,
            actor=self.user,
            reason="Maturity installment plan approved and created.",
            source_channel="WEB",
        )
        self.assertEqual(event.event_type, INSTALLMENT_PLAN_CREATED)
        self.assertEqual(event.aggregate_type, "OLMaturityInstallmentPlan")
        self.assertEqual(event.aggregate_id, str(plan.pk))
        self.assertEqual(event.payload["plan_number"], plan.plan_number)
        self.assertEqual(event.payload["policy_number"], self.policy.policy_number)
        self.assertEqual(event.payload["maturity_claim_number"], self.maturity_claim.claim_number)
        self.assertEqual(event.payload["source_channel"], "WEB")
        self.assertEqual(DomainEvent.objects.filter(pk=event.pk).count(), 1)

    def test_list_and_detail_return_human_readable_plan_fields(self):
        plan = self.make_plan()
        list_response = self.client.get("/api/v1/ol/installment-plans/")
        self.assertEqual(list_response.status_code, 200, list_response.data)
        row = list_response.data["data"]["results"][0]
        self.assertEqual(row["plan_number"], plan.plan_number)
        self.assertEqual(row["policy_number"], self.policy.policy_number)
        self.assertEqual(row["policyholder_name"], "Asha Mwinyi")
        self.assertEqual(row["policyholder_display"], "ZIC-MIP-P-0001 — Asha Mwinyi")
        self.assertEqual(row["maturity_claim_number"], self.maturity_claim.claim_number)
        self.assertEqual(row["currency"], "TZS")
        self.assertEqual(row["installment_count"], 3)
        self.assertEqual(row["frequency_display"], "Monthly")
        self.assertIn("status_display", row)
        self.assertNotIn(str(self.partner.pk), row["policyholder_display"])

        detail_response = self.client.get(f"/api/v1/ol/installment-plans/{plan.pk}/")
        self.assertEqual(detail_response.status_code, 200, detail_response.data)
        detail = detail_response.data["data"]
        self.assertEqual(detail["plan_number"], plan.plan_number)
        self.assertEqual(len(detail["items"]), 3)
        self.assertEqual(detail["items"][0]["installment_number"], 1)
        self.assertEqual(detail["config"]["calculation_basis"], "INSTALLMENT_RATE_ANNUITY")
        self.assertEqual(detail["policy_context"]["policy_number"], self.policy.policy_number)
        self.assertEqual(detail["maturity_claim_context"]["claim_number"], self.maturity_claim.claim_number)
        self.assertIn("audit_timeline", detail)
        self.assertEqual(detail["allowed_actions"], ["view", "print", "cancel"])

    def test_unknown_plan_returns_structured_error_without_identifier_leak(self):
        response = self.client.get(f"/api/v1/ol/installment-plans/{uuid4()}/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error_code"], "INSTALLMENT_PLAN_NOT_FOUND")
        self.assertTrue(response.data["resolution_steps"])
        self.assertEqual(response.data["doc_ref"], "docs/OL_MATURITY_INSTALLMENTS_DESIGN.md")

    def test_list_filters_search_and_pagination(self):
        plan = self.make_plan()
        self.make_plan(item_count=1)
        response = self.client.get(f"/api/v1/ol/installment-plans/?q={plan.plan_number}&status=CREATED&page_size=10")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(response.data["data"]["results"][0]["plan_number"], plan.plan_number)
        self.assertNotIn(str(plan.policy_ref.pk), str(response.data["data"]["results"][0]["policy_number"]))
