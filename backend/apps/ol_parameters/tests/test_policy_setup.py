from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.governance.models import AuditLog
from apps.ol_parameters.models import (
    OLAnticipatedEndowmentInstallmentRate,
    OLBeneficialType,
    OLGracePeriod,
    OLMemberCoverConfiguration,
    OLParameterTableRegistry,
    OLCommitmentStatus,
    OLPaidUpRate,
    OLPaidUpSetup,
    OLSurrenderSetup,
    OLSurrenderValueRate,
    OLPolicyRenewalStatus,
    OLPolicyStatus,
)
from apps.users.models import User
from apps.ordinary_life.models import OLPlan, OLProduct, OLProductVersion


class OLPolicySetupTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="ol-policy-setup-admin",
            email="ol-policy-setup-admin@example.com",
            password="Strong-pass-123!",
            is_superuser=True,
            is_staff=True,
            is_active=True,
            is_approved=True,
        )
        self.client.force_authenticate(self.user)

    def _product_scope(self):
        product = OLProduct.objects.create(code="TERM_LIFE", name="Term Life")
        version = OLProductVersion.objects.create(
            product=product,
            version_number=1,
            effective_from=date(2026, 1, 1),
        )
        plan = OLPlan.objects.create(
            product_version=version,
            code="TERM_STANDARD",
            name="Term Standard",
        )
        return product, plan

    def test_anticipated_rate_rejects_invalid_ranges_and_mismatched_plan_scope(self):
        product, plan = self._product_scope()
        other_product = OLProduct.objects.create(code="WHOLE_LIFE", name="Whole Life")

        invalid_range = OLAnticipatedEndowmentInstallmentRate(
            code="RATE_INVALID",
            name="Invalid rate",
            effective_from=date(2026, 1, 1),
            product=product,
            age_from=60,
            age_to=30,
            rate_factor=Decimal("1.10000000"),
        )
        with self.assertRaises(ValidationError):
            invalid_range.full_clean()

        mismatched_scope = OLAnticipatedEndowmentInstallmentRate(
            code="RATE_MISMATCH",
            name="Mismatched scope",
            effective_from=date(2026, 1, 1),
            product=other_product,
            plan=plan,
            rate_factor=Decimal("1.10000000"),
        )
        with self.assertRaises(ValidationError):
            mismatched_scope.full_clean()

    def test_grace_period_requires_ordered_lifecycle_days(self):
        grace = OLGracePeriod(
            code="GRACE_INVALID",
            name="Invalid grace",
            effective_from=date(2026, 1, 1),
            grace_days=30,
            warning_days=35,
            pre_lapse_days=10,
            lapse_days=20,
        )
        with self.assertRaises(ValidationError):
            grace.full_clean()

    def test_policy_status_transition_rules_and_graph_validation(self):
        active = OLPolicyStatus(
            code="ACTIVE",
            name="Active",
            effective_from=date(2026, 1, 1),
        )
        active.full_clean()
        active.save()

        draft = OLPolicyStatus(
            code="DRAFT",
            name="Draft",
            effective_from=date(2026, 1, 1),
            allowed_transitions=["ACTIVE"],
        )
        draft.full_clean()
        draft.save()

        terminal_with_transition = OLPolicyStatus(
            code="CANCELLED",
            name="Cancelled",
            effective_from=date(2026, 1, 1),
            is_terminal=True,
            allowed_transitions=["ACTIVE"],
        )
        with self.assertRaises(ValidationError):
            terminal_with_transition.full_clean()

        unknown_target = OLPolicyStatus(
            code="PENDING",
            name="Pending",
            effective_from=date(2026, 1, 1),
            allowed_transitions=["MISSING"],
        )
        with self.assertRaises(ValidationError):
            unknown_target.full_clean()

        response = self.client.get("/api/v1/ol-parameters/policy-statuses/validate-transitions/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["valid"])

    def test_policy_setup_tables_expose_crud_filter_export_and_soft_deactivation(self):
        create_response = self.client.post(
            "/api/v1/ol-parameters/grace-periods/",
            {
                "code": "MONTHLY_STANDARD",
                "name": "Monthly Standard",
                "description": "Monthly premium grace configuration.",
                "effective_from": "2026-01-01",
                "premium_frequency": "MONTHLY",
                "grace_days": 30,
                "warning_days": 15,
                "pre_lapse_days": 7,
                "lapse_days": 30,
                "minimum_due_amount": "0.00",
            },
            format="json",
            HTTP_X_REQUEST_ID="ol-policy-grace-create",
        )
        self.assertEqual(create_response.status_code, 201, create_response.data)
        grace = OLGracePeriod.objects.get(code="MONTHLY_STANDARD")

        list_response = self.client.get(
            "/api/v1/ol-parameters/grace-periods/?premium_frequency=MONTHLY&search=Monthly"
        )
        self.assertEqual(list_response.status_code, 200, list_response.data)
        self.assertEqual(len(list_response.data["data"]), 1)
        self.assertEqual(list_response.data["data"][0]["code"], "MONTHLY_STANDARD")

        update_response = self.client.patch(
            f"/api/v1/ol-parameters/grace-periods/{grace.pk}/",
            {"name": "Monthly Standard Updated"},
            format="json",
            HTTP_X_REQUEST_ID="ol-policy-grace-update",
        )
        self.assertEqual(update_response.status_code, 200, update_response.data)
        grace.refresh_from_db()
        self.assertEqual(grace.name, "Monthly Standard Updated")

        export_response = self.client.get("/api/v1/ol-parameters/grace-periods/export/")
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("text/csv", export_response["Content-Type"])
        self.assertIn("MONTHLY_STANDARD", export_response.content.decode())

        deactivate_response = self.client.post(
            f"/api/v1/ol-parameters/grace-periods/{grace.pk}/deactivate/",
            {},
            format="json",
            HTTP_X_REQUEST_ID="ol-policy-grace-deactivate",
        )
        self.assertEqual(deactivate_response.status_code, 200, deactivate_response.data)
        grace.refresh_from_db()
        self.assertFalse(grace.is_active)
        self.assertTrue(
            AuditLog.objects.filter(
                app_label="ol_parameters",
                model_name="olgraceperiod",
                object_id=str(grace.pk),
                action="DEACTIVATE",
                correlation_id="ol-policy-grace-deactivate",
            ).exists()
        )

    def test_policy_status_api_and_registry_metadata_are_available(self):
        response = self.client.post(
            "/api/v1/ol-parameters/policy-statuses/",
            {
                "code": "ACTIVE",
                "name": "Active",
                "description": "Active policy status.",
                "effective_from": "2026-01-01",
                "display_order": 1,
                "badge_type": "POSITIVE",
                "is_terminal": False,
                "allowed_transitions": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

        registry = OLParameterTableRegistry.objects.create(
            slug="policy-statuses",
            label="Policy Statuses",
            parameter_group="Policy Setup",
            model_label="ol_parameters.OLPolicyStatus",
            visible_columns=["code", "name", "is_terminal"],
            searchable_fields=["code", "name"],
            filter_fields=["is_active", "is_terminal"],
            default_ordering=["display_order", "code"],
            allowed_actions=["list", "retrieve", "create", "update", "deactivate", "export"],
            export_support=True,
            permission_code="ol_parameters.view",
        )
        self.assertEqual(registry.slug, "policy-statuses")

    def test_policy_setup_seed_is_idempotent_and_covers_all_catalogs(self):
        call_command("seed_ol_policy_setup")
        counts = {
            "policy_statuses": OLPolicyStatus.objects.count(),
            "renewal_statuses": OLPolicyRenewalStatus.objects.count(),
            "beneficial_types": OLBeneficialType.objects.count(),
            "grace_periods": OLGracePeriod.objects.count(),
            "member_cover": OLMemberCoverConfiguration.objects.count(),
            "registry": OLParameterTableRegistry.objects.filter(parameter_group="Policy Setup").count(),
        }
        self.assertGreaterEqual(counts["policy_statuses"], 8)
        self.assertGreaterEqual(counts["renewal_statuses"], 4)
        self.assertGreaterEqual(counts["beneficial_types"], 7)
        self.assertGreaterEqual(counts["grace_periods"], 1)
        self.assertGreaterEqual(counts["member_cover"], 1)
        self.assertEqual(counts["registry"], 11)

        call_command("seed_ol_policy_setup")
        self.assertEqual(OLPolicyStatus.objects.count(), counts["policy_statuses"])
        self.assertEqual(OLPolicyRenewalStatus.objects.count(), counts["renewal_statuses"])
        self.assertEqual(OLBeneficialType.objects.count(), counts["beneficial_types"])
        self.assertEqual(OLGracePeriod.objects.count(), counts["grace_periods"])
        self.assertEqual(OLMemberCoverConfiguration.objects.count(), counts["member_cover"])
        self.assertEqual(OLParameterTableRegistry.objects.filter(parameter_group="Policy Setup").count(), counts["registry"])

    def test_all_policy_setup_entities_are_registered_for_audit(self):
        for model, code in (
            (OLBeneficialType, "BENEFICIARY_AUDIT"),
            (OLMemberCoverConfiguration, "MEMBER_AUDIT"),
        ):
            record = model.objects.create(code=code, name=code.title(), effective_from=date(2026, 1, 1))
            self.assertTrue(
                AuditLog.objects.filter(
                    app_label="ol_parameters",
                    model_name=model._meta.model_name,
                    object_id=str(record.pk),
                    action="CREATE",
                ).exists()
            )

    def test_crud_create_and_retrieve_is_available_for_all_six_entities(self):
        product, plan = self._product_scope()
        cases = [
            (
                "anticipated-endowment-rates",
                {
                    "code": "RATE_API",
                    "name": "API Endowment Rate",
                    "effective_from": "2026-01-01",
                    "product": str(product.pk),
                    "plan": str(plan.pk),
                    "installment_type": "ANTICIPATED_ENDOWMENT",
                    "frequency": "ANNUAL",
                    "age_from": 18,
                    "age_to": 65,
                    "term_from": 10,
                    "term_to": 20,
                    "policy_year_from": 1,
                    "policy_year_to": 5,
                    "rate_factor": "1.05000000",
                    "currency": "TZS",
                },
            ),
            (
                "grace-periods",
                {
                    "code": "GRACE_API",
                    "name": "API Grace Period",
                    "effective_from": "2026-01-01",
                    "premium_frequency": "ANNUAL",
                    "grace_days": 30,
                    "warning_days": 15,
                    "pre_lapse_days": 7,
                    "lapse_days": 30,
                },
            ),
            (
                "policy-statuses",
                {
                    "code": "STATUS_API",
                    "name": "API Policy Status",
                    "effective_from": "2026-01-01",
                    "display_order": 1,
                    "badge_type": "NEUTRAL",
                    "is_terminal": False,
                    "allowed_transitions": [],
                },
            ),
            (
                "policy-renewal-statuses",
                {
                    "code": "RENEWAL_API",
                    "name": "API Renewal Status",
                    "effective_from": "2026-01-01",
                    "display_order": 1,
                    "renewal_action": "PENDING",
                },
            ),
            (
                "beneficial-types",
                {
                    "code": "BENEFICIAL_API",
                    "name": "API Beneficial Type",
                    "effective_from": "2026-01-01",
                    "category": "BENEFICIARY",
                    "calculation_basis": "PERCENTAGE",
                    "default_ratio": "100.0000",
                    "allows_multiple": True,
                },
            ),
            (
                "member-cover-configurations",
                {
                    "code": "MEMBER_COVER_API",
                    "name": "API Member Cover",
                    "effective_from": "2026-01-01",
                    "cover_type": "DEPENDENT",
                    "member_relation": "SPOUSE",
                    "min_age": 18,
                    "max_age": 65,
                    "waiting_period_days": 30,
                    "benefit_limit": "1000000.00",
                    "premium_basis": "MEMBER_PREMIUM",
                    "coverage_basis": "SUM_ASSURED",
                },
            ),
        ]

        for slug, payload in cases:
            response = self.client.post(
                f"/api/v1/ol-parameters/{slug}/",
                payload,
                format="json",
            )
            self.assertEqual(response.status_code, 201, {"slug": slug, "data": response.data})
            self.assertEqual(response.data["code"], payload["code"])
            record_id = response.data["id"]
            retrieve_response = self.client.get(f"/api/v1/ol-parameters/{slug}/{record_id}/")
            self.assertEqual(retrieve_response.status_code, 200, retrieve_response.data)
            self.assertEqual(retrieve_response.data["code"], payload["code"])

    def test_policy_setup_read_requires_ol_parameters_view_permission(self):
        unpermissioned = User.objects.create_user(
            username="ol-policy-setup-no-access",
            email="ol-policy-setup-no-access@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
        )
        self.client.force_authenticate(unpermissioned)
        response = self.client.get("/api/v1/ol-parameters/policy-statuses/")
        self.assertEqual(response.status_code, 403, response.data)

    @override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
    def test_admin_changelists_are_available_for_all_six_entities(self):
        self.client.force_login(self.user)
        model_names = (
            "olanticipatedendowmentinstallmentrate",
            "olgraceperiod",
            "olpolicystatus",
            "olpolicyrenewalstatus",
            "olbeneficialtype",
            "olmembercoverconfiguration",
        )
        for model_name in model_names:
            response = self.client.get(
                reverse(f"admin:ol_parameters_{model_name}_changelist")
            )
            self.assertEqual(response.status_code, 200, {"model": model_name, "status": response.status_code})

    def test_member_cover_age_range_and_beneficial_ratio_are_validated(self):
        invalid_cover = OLMemberCoverConfiguration(
            code="MEMBER_INVALID",
            name="Invalid Member Cover",
            effective_from=date(2026, 1, 1),
            min_age=70,
            max_age=18,
        )
        with self.assertRaises(ValidationError):
            invalid_cover.full_clean()

        invalid_ratio = OLBeneficialType(
            code="BENEFICIAL_INVALID",
            name="Invalid Beneficial Type",
            effective_from=date(2026, 1, 1),
            default_ratio=Decimal("120.0000"),
        )
        with self.assertRaises(ValidationError):
            invalid_ratio.full_clean()

    def test_part2_model_invariants_and_effective_date_overlaps_are_enforced(self):
        invalid_surrender = OLSurrenderSetup(
            code="SURRENDER_INVALID",
            name="Invalid Surrender",
            effective_from=date(2026, 1, 1),
            surrender_charge_type="NONE",
            surrender_charge_value=Decimal("1.00"),
        )
        with self.assertRaises(ValidationError):
            invalid_surrender.full_clean()

        invalid_paid_up = OLPaidUpSetup(
            code="PAID_UP_INVALID",
            name="Invalid Paid Up",
            effective_from=date(2026, 1, 1),
            allow_paidup=True,
            minimum_premiums_paid=0,
            minimum_policy_months=0,
        )
        with self.assertRaises(ValidationError):
            invalid_paid_up.full_clean()

        product, plan = self._product_scope()
        invalid_rate = OLSurrenderValueRate(
            code="SURRENDER_RATE_INVALID",
            name="Invalid Surrender Rate",
            effective_from=date(2026, 1, 1),
            table_code="STANDARD",
            rate_table_version="V1",
            product=product,
            plan=plan,
            age_from=70,
            age_to=18,
            policy_year_from=1,
            policy_year_to=5,
            rate_factor=Decimal("0.50000000"),
        )
        with self.assertRaises(ValidationError):
            invalid_rate.full_clean()

        first_setup = OLSurrenderSetup(
            code="SURRENDER_FIRST",
            name="First Surrender Setup",
            effective_from=date(2026, 1, 1),
            surrender_charge_type="PERCENTAGE",
            surrender_charge_value=Decimal("5.00000000"),
        )
        first_setup.full_clean()
        first_setup.save()
        overlapping_setup = OLSurrenderSetup(
            code="SURRENDER_OVERLAP",
            name="Overlapping Surrender Setup",
            effective_from=date(2026, 6, 1),
            surrender_charge_type="PERCENTAGE",
            surrender_charge_value=Decimal("4.00000000"),
        )
        with self.assertRaises(ValidationError):
            overlapping_setup.full_clean()

        first_rate = OLSurrenderValueRate(
            code="SURRENDER_RATE_FIRST",
            name="First Surrender Rate",
            effective_from=date(2026, 1, 1),
            table_code="STANDARD",
            rate_table_version="V1",
            product=product,
            plan=plan,
            policy_year_from=1,
            policy_year_to=5,
            rate_factor=Decimal("0.50000000"),
        )
        first_rate.full_clean()
        first_rate.save()
        overlapping_rate = OLSurrenderValueRate(
            code="SURRENDER_RATE_OVERLAP",
            name="Overlapping Surrender Rate",
            effective_from=date(2026, 6, 1),
            table_code="STANDARD",
            rate_table_version="V1",
            product=product,
            plan=plan,
            policy_year_from=1,
            policy_year_to=5,
            rate_factor=Decimal("0.60000000"),
        )
        with self.assertRaises(ValidationError):
            overlapping_rate.full_clean()

    def test_part2_seed_covers_all_tables_and_is_idempotent(self):
        self._product_scope()
        call_command("seed_ol_policy_setup")
        counts = {
            "commitment_statuses": OLCommitmentStatus.objects.count(),
            "surrender_setups": OLSurrenderSetup.objects.count(),
            "paid_up_setups": OLPaidUpSetup.objects.count(),
            "surrender_value_rates": OLSurrenderValueRate.objects.count(),
            "paid_up_rates": OLPaidUpRate.objects.count(),
            "registry": OLParameterTableRegistry.objects.filter(parameter_group="Policy Setup").count(),
        }
        self.assertGreaterEqual(counts["commitment_statuses"], 4)
        self.assertGreaterEqual(counts["surrender_setups"], 1)
        self.assertGreaterEqual(counts["paid_up_setups"], 1)
        self.assertGreaterEqual(counts["surrender_value_rates"], 1)
        self.assertGreaterEqual(counts["paid_up_rates"], 1)
        self.assertEqual(counts["registry"], 11)

        call_command("seed_ol_policy_setup")
        self.assertEqual(OLCommitmentStatus.objects.count(), counts["commitment_statuses"])
        self.assertEqual(OLSurrenderSetup.objects.count(), counts["surrender_setups"])
        self.assertEqual(OLPaidUpSetup.objects.count(), counts["paid_up_setups"])
        self.assertEqual(OLSurrenderValueRate.objects.count(), counts["surrender_value_rates"])
        self.assertEqual(OLPaidUpRate.objects.count(), counts["paid_up_rates"])
        self.assertEqual(OLParameterTableRegistry.objects.filter(parameter_group="Policy Setup").count(), counts["registry"])

    def test_part2_crud_create_and_retrieve_is_available_for_all_five_entities(self):
        product, plan = self._product_scope()
        cases = [
            (
                "surrender-setups",
                {
                    "code": "SURRENDER_API",
                    "name": "API Surrender Setup",
                    "effective_from": "2026-01-01",
                    "product": str(product.pk),
                    "plan": str(plan.pk),
                    "minimum_premiums_paid": 12,
                    "minimum_policy_months": 12,
                    "minimum_premium_paid_ratio": "100.0000",
                    "surrender_charge_type": "PERCENTAGE",
                    "surrender_charge_value": "5.00000000",
                    "partial_surrender_allowed": False,
                    "surrender_payout_days": 30,
                    "require_approval": True,
                },
            ),
            (
                "paid-up-setups",
                {
                    "code": "PAID_UP_API",
                    "name": "API Paid Up Setup",
                    "effective_from": "2026-01-01",
                    "product": str(product.pk),
                    "plan": str(plan.pk),
                    "minimum_premiums_paid": 12,
                    "minimum_policy_months": 12,
                    "paidup_conversion_basis": "PROPORTIONAL",
                    "allow_paidup": True,
                    "paidup_effective_rule": "NEXT_ANNIVERSARY",
                },
            ),
            (
                "surrender-value-rates",
                {
                    "code": "SURRENDER_RATE_API",
                    "name": "API Surrender Value Rate",
                    "effective_from": "2026-01-01",
                    "table_code": "STANDARD",
                    "rate_table_version": "V1",
                    "product": str(product.pk),
                    "plan": str(plan.pk),
                    "policy_year_from": 1,
                    "policy_year_to": 5,
                    "rate_factor": "0.50000000",
                    "row_order": 1,
                },
            ),
            (
                "paid-up-rates",
                {
                    "code": "PAID_UP_RATE_API",
                    "name": "API Paid Up Rate",
                    "effective_from": "2026-01-01",
                    "table_code": "STANDARD",
                    "rate_table_version": "V1",
                    "product": str(product.pk),
                    "plan": str(plan.pk),
                    "policy_year_from": 1,
                    "policy_year_to": 5,
                    "rate_factor": "0.75000000",
                    "row_order": 1,
                },
            ),
            (
                "commitment-statuses",
                {
                    "code": "COMMITMENT_API",
                    "name": "API Commitment Status",
                    "effective_from": "2026-01-01",
                    "display_order": 1,
                    "applies_to": "COMMITMENT",
                    "is_terminal": False,
                },
            ),
        ]
        for slug, payload in cases:
            response = self.client.post(
                f"/api/v1/ol-parameters/{slug}/",
                payload,
                format="json",
            )
            self.assertEqual(response.status_code, 201, {"slug": slug, "data": response.data})
            record_id = response.data["id"]
            retrieve_response = self.client.get(f"/api/v1/ol-parameters/{slug}/{record_id}/")
            self.assertEqual(retrieve_response.status_code, 200, retrieve_response.data)
            self.assertEqual(retrieve_response.data["code"], payload["code"])

    def test_part2_permission_enforcement_and_audit_coverage(self):
        unpermissioned = User.objects.create_user(
            username="ol-policy-part2-no-access",
            email="ol-policy-part2-no-access@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
        )
        self.client.force_authenticate(unpermissioned)
        response = self.client.get("/api/v1/ol-parameters/surrender-setups/")
        self.assertEqual(response.status_code, 403, response.data)

        self.client.force_authenticate(self.user)
        product, plan = self._product_scope()
        records = [
            OLSurrenderSetup(code="SURRENDER_AUDIT", name="Surrender Audit", effective_from=date(2026, 1, 1)),
            OLPaidUpSetup(code="PAID_UP_AUDIT", name="Paid Up Audit", effective_from=date(2026, 1, 1), minimum_policy_months=12),
            OLSurrenderValueRate(code="SURRENDER_RATE_AUDIT", name="Surrender Rate Audit", effective_from=date(2026, 1, 1), table_code="STANDARD", rate_table_version="V1", product=product, plan=plan, rate_factor=Decimal("0.50")),
            OLPaidUpRate(code="PAID_UP_RATE_AUDIT", name="Paid Up Rate Audit", effective_from=date(2026, 1, 1), table_code="STANDARD", rate_table_version="V1", product=product, plan=plan, rate_factor=Decimal("0.75")),
            OLCommitmentStatus(code="COMMITMENT_AUDIT", name="Commitment Audit", effective_from=date(2026, 1, 1)),
        ]
        for record in records:
            record.full_clean()
            record.save()
            self.assertTrue(
                AuditLog.objects.filter(
                    app_label="ol_parameters",
                    model_name=record._meta.model_name,
                    object_id=str(record.pk),
                    action="CREATE",
                ).exists()
            )

    @override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
    def test_admin_changelists_are_available_for_all_part2_entities(self):
        self.client.force_login(self.user)
        model_names = (
            "olsurrendersetup",
            "olpaidupsetup",
            "olsurrendervaluerate",
            "olpaiduprate",
            "olcommitmentstatus",
        )
        for model_name in model_names:
            response = self.client.get(reverse(f"admin:ol_parameters_{model_name}_changelist"))
            self.assertEqual(response.status_code, 200, {"model": model_name, "status": response.status_code})
