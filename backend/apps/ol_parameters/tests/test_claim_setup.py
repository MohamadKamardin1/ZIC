from datetime import date

from django.contrib import admin
from django.core import management
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.governance.models import AuditLog
from apps.ol_parameters.models import (
    OLClaimReason,
    OLClaimStatus,
    OLClaimType,
    OLCorrespondentType,
    OLDischargeType,
    OLParameterTableRegistry,
)
from apps.users.models import User


class OLClaimSetupTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="ol-claim-setup-admin",
            email="ol-claim-setup-admin@example.com",
            password="Strong-pass-123!",
            is_superuser=True,
            is_staff=True,
            is_active=True,
            is_approved=True,
        )
        self.client.force_authenticate(self.user)
        self.base_claim_type = OLClaimType(
            code="BASE_DEATH_CLAIM",
            name="Base Death Claim",
            description="Base claim type for focused tests.",
            claim_category="DEATH",
            calculation_basis="SUM_ASSURED",
            duplicate_check_rule="POLICY_AND_TYPE",
            waiting_period_days=0,
            payable_to_rules={"default": "beneficiary"},
            require_documents=["DEATH_CERTIFICATE"],
            effective_from=date(2026, 1, 1),
            is_active=True,
        )
        self.base_claim_type.full_clean()
        self.base_claim_type.save()

    def claim_type_payload(self, code="DEATH_CLAIM", effective_to=None):
        return {
            "code": code,
            "name": "Death Claim",
            "description": "Death claim configuration.",
            "claim_category": "DEATH",
            "calculation_basis": "SUM_ASSURED",
            "duplicate_check_rule": "POLICY_AND_TYPE",
            "waiting_period_days": 0,
            "payable_to_rules": {"default": "beneficiary", "requires_verified_beneficiary": True},
            "allow_waiver_of_premium": False,
            "require_documents": ["DEATH_CERTIFICATE", "IDENTITY_DOCUMENT"],
            "require_approval": True,
            "effective_from": "2026-01-01",
            "effective_to": effective_to,
            "is_active": True,
        }

    def reason_payload(self, code="NATURAL_DEATH", claim_type=None):
        return {
            "code": code,
            "name": "Natural Death",
            "description": "Natural death claim reason.",
            "claim_type": str((claim_type or self.base_claim_type).pk),
            "reason_category": "EVENT",
            "effective_from": "2026-01-01",
            "effective_to": None,
            "is_active": True,
        }

    def status_payload(self, code="REGISTERED", allowed_transitions=None, is_terminal=False):
        return {
            "code": code,
            "name": code.replace("_", " ").title(),
            "description": "Claim workflow status.",
            "display_order": 10,
            "badge_type": "NEUTRAL",
            "is_terminal": is_terminal,
            "is_payable": False,
            "allowed_transitions": allowed_transitions or [],
            "effective_from": "2026-01-01",
            "effective_to": None,
            "is_active": True,
        }

    def discharge_payload(self, code="FULL_FINAL_DISCHARGE"):
        return {
            "code": code,
            "name": "Full and Final Discharge",
            "description": "Full and final claim discharge.",
            "discharge_category": "FULL_AND_FINAL",
            "template_code": "OL_CLAIM_FULL_FINAL",
            "variables": {"claim_number": "string", "payee_name": "string"},
            "effective_from": "2026-01-01",
            "effective_to": None,
            "is_active": True,
        }

    def correspondent_payload(self, code="CLAIM_ACKNOWLEDGEMENT_EMAIL"):
        return {
            "code": code,
            "name": "Claim Acknowledgement Email",
            "description": "Claim acknowledgement correspondence.",
            "correspondence_category": "CLAIM_ACKNOWLEDGEMENT",
            "communication_channel": "EMAIL",
            "purpose": "Acknowledge claim registration",
            "effective_from": "2026-01-01",
            "effective_to": None,
            "is_active": True,
        }

    def test_all_claim_setup_catalogs_support_crud_filters_export_and_deactivation(self):
        claim_type_response = self.client.post(
            "/api/v1/ol-parameters/claim-types/",
            self.claim_type_payload(),
            format="json",
            HTTP_X_REQUEST_ID="claim-type-create",
        )
        self.assertEqual(claim_type_response.status_code, 201, claim_type_response.data)
        claim_type = OLClaimType.objects.get(code="DEATH_CLAIM")

        reason_response = self.client.post(
            "/api/v1/ol-parameters/claim-reasons/",
            self.reason_payload(claim_type=claim_type),
            format="json",
            HTTP_X_REQUEST_ID="claim-reason-create",
        )
        self.assertEqual(reason_response.status_code, 201, reason_response.data)

        registered_response = self.client.post(
            "/api/v1/ol-parameters/claim-statuses/",
            self.status_payload(),
            format="json",
            HTTP_X_REQUEST_ID="claim-status-create",
        )
        self.assertEqual(registered_response.status_code, 201, registered_response.data)
        status = OLClaimStatus.objects.get(code="REGISTERED")

        discharge_response = self.client.post(
            "/api/v1/ol-parameters/discharge-types/",
            self.discharge_payload(),
            format="json",
            HTTP_X_REQUEST_ID="discharge-create",
        )
        self.assertEqual(discharge_response.status_code, 201, discharge_response.data)
        discharge = OLDischargeType.objects.get(code="FULL_FINAL_DISCHARGE")

        correspondent_response = self.client.post(
            "/api/v1/ol-parameters/correspondent-types/",
            self.correspondent_payload(),
            format="json",
            HTTP_X_REQUEST_ID="correspondent-create",
        )
        self.assertEqual(correspondent_response.status_code, 201, correspondent_response.data)
        correspondent = OLCorrespondentType.objects.get(code="CLAIM_ACKNOWLEDGEMENT_EMAIL")

        update = self.client.patch(
            f"/api/v1/ol-parameters/claim-types/{claim_type.pk}/",
            {"require_approval": False},
            format="json",
            HTTP_X_REQUEST_ID="claim-type-update",
        )
        self.assertEqual(update.status_code, 200, update.data)
        claim_type.refresh_from_db()
        self.assertFalse(claim_type.require_approval)

        endpoints = [
            ("claim-types", "claim_category=DEATH", "DEATH_CLAIM"),
            ("claim-reasons", "reason_category=EVENT", "NATURAL_DEATH"),
            ("claim-statuses", "badge_type=NEUTRAL", "REGISTERED"),
            ("discharge-types", "discharge_category=FULL_AND_FINAL", "FULL_FINAL_DISCHARGE"),
            ("correspondent-types", "communication_channel=EMAIL", "CLAIM_ACKNOWLEDGEMENT_EMAIL"),
        ]
        for slug, query, expected_code in endpoints:
            listing = self.client.get(f"/api/v1/ol-parameters/{slug}/?{query}")
            self.assertEqual(listing.status_code, 200, listing.data)
            self.assertGreaterEqual(listing.data["pagination"]["total"], 1)
            self.assertTrue(any(row["code"] == expected_code for row in listing.data["data"]))
            export = self.client.get(f"/api/v1/ol-parameters/{slug}/export/?{query}")
            self.assertEqual(export.status_code, 200)
            self.assertIn("text/csv", export["Content-Type"])
            self.assertIn(expected_code, export.content.decode())

        for slug, obj in [
            ("claim-reasons", OLClaimReason.objects.get(code="NATURAL_DEATH")),
            ("claim-statuses", status),
            ("discharge-types", discharge),
            ("correspondent-types", correspondent),
        ]:
            retrieve = self.client.get(f"/api/v1/ol-parameters/{slug}/{obj.pk}/")
            self.assertEqual(retrieve.status_code, 200, retrieve.data)

        deactivate = self.client.post(
            f"/api/v1/ol-parameters/claim-types/{claim_type.pk}/deactivate/",
            {},
            format="json",
            HTTP_X_REQUEST_ID="claim-type-deactivate",
        )
        self.assertEqual(deactivate.status_code, 200, deactivate.data)
        claim_type.refresh_from_db()
        self.assertFalse(claim_type.is_active)

    def test_status_transition_graph_requires_existing_targets_and_supports_transition_queries(self):
        target_response = self.client.post(
            "/api/v1/ol-parameters/claim-statuses/",
            self.status_payload("UNDER_ASSESSMENT"),
            format="json",
        )
        self.assertEqual(target_response.status_code, 201, target_response.data)

        source_response = self.client.post(
            "/api/v1/ol-parameters/claim-statuses/",
            self.status_payload("REGISTERED", ["UNDER_ASSESSMENT"]),
            format="json",
        )
        self.assertEqual(source_response.status_code, 201, source_response.data)
        source = OLClaimStatus.objects.get(code="REGISTERED")
        target = OLClaimStatus.objects.get(code="UNDER_ASSESSMENT")
        self.assertTrue(source.can_transition_to(target))
        source.validate_transition_to(target)
        with self.assertRaises(ValidationError):
            source.validate_transition_to("CLOSED")

        invalid = self.client.post(
            "/api/v1/ol-parameters/claim-statuses/",
            self.status_payload("INVALID_GRAPH", ["UNKNOWN_STATUS"]),
            format="json",
        )
        self.assertEqual(invalid.status_code, 400, invalid.data)

        terminal = self.client.post(
            "/api/v1/ol-parameters/claim-statuses/",
            self.status_payload("CLOSED", ["REGISTERED"], is_terminal=True),
            format="json",
        )
        self.assertEqual(terminal.status_code, 400, terminal.data)

    def test_json_category_and_effective_date_validation_reject_bad_configuration(self):
        invalid_claim_type = self.claim_type_payload("INVALID_JSON")
        invalid_claim_type["payable_to_rules"] = ["beneficiary"]
        response = self.client.post("/api/v1/ol-parameters/claim-types/", invalid_claim_type, format="json")
        self.assertEqual(response.status_code, 400, response.data)

        invalid_documents = self.claim_type_payload("INVALID_DOCUMENTS")
        invalid_documents["require_documents"] = {"document": "death_certificate"}
        response = self.client.post("/api/v1/ol-parameters/claim-types/", invalid_documents, format="json")
        self.assertEqual(response.status_code, 400, response.data)

        invalid_discharge = self.discharge_payload("INVALID_VARIABLES")
        invalid_discharge["variables"] = ["claim_number"]
        response = self.client.post("/api/v1/ol-parameters/discharge-types/", invalid_discharge, format="json")
        self.assertEqual(response.status_code, 400, response.data)

        invalid_date = self.claim_type_payload("INVALID_DATES", effective_to="2025-12-31")
        response = self.client.post("/api/v1/ol-parameters/claim-types/", invalid_date, format="json")
        self.assertEqual(response.status_code, 400, response.data)

        invalid_category = self.claim_type_payload("INVALID_CATEGORY")
        invalid_category["claim_category"] = "UNSUPPORTED"
        response = self.client.post("/api/v1/ol-parameters/claim-types/", invalid_category, format="json")
        self.assertEqual(response.status_code, 400, response.data)

    def test_unique_codes_permissions_and_audit_logs_are_enforced(self):
        created = self.client.post(
            "/api/v1/ol-parameters/claim-types/",
            self.claim_type_payload(),
            format="json",
            HTTP_X_REQUEST_ID="claim-audit-create",
        )
        self.assertEqual(created.status_code, 201, created.data)
        claim_type = OLClaimType.objects.get(code="DEATH_CLAIM")
        self.assertTrue(
            AuditLog.objects.filter(
                app_label="ol_parameters",
                model_name="olclaimtype",
                object_id=str(claim_type.pk),
                action="CREATE",
                correlation_id="claim-audit-create",
            ).exists()
        )

        duplicate = self.client.post("/api/v1/ol-parameters/claim-types/", self.claim_type_payload(), format="json")
        self.assertEqual(duplicate.status_code, 400, duplicate.data)

        updated = self.client.patch(
            f"/api/v1/ol-parameters/claim-types/{claim_type.pk}/",
            {"description": "Updated claim type."},
            format="json",
            HTTP_X_REQUEST_ID="claim-audit-update",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertTrue(
            AuditLog.objects.filter(
                app_label="ol_parameters",
                model_name="olclaimtype",
                object_id=str(claim_type.pk),
                action="UPDATE",
                correlation_id="claim-audit-update",
            ).exists()
        )

        restricted_user = User.objects.create_user(
            username="ol-claim-setup-viewer",
            email="ol-claim-setup-viewer@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
        )
        restricted_client = APIClient()
        restricted_client.force_authenticate(restricted_user)
        for slug in ("claim-types", "claim-reasons", "claim-statuses", "discharge-types", "correspondent-types"):
            self.assertEqual(restricted_client.get(f"/api/v1/ol-parameters/{slug}/").status_code, 403)

    def test_seed_is_idempotent_and_registers_all_claim_contracts(self):
        management.call_command("seed_ol_claim_setup", verbosity=0)
        first_counts = (
            OLClaimType.objects.count(),
            OLClaimReason.objects.count(),
            OLClaimStatus.objects.count(),
            OLDischargeType.objects.count(),
            OLCorrespondentType.objects.count(),
            OLParameterTableRegistry.objects.filter(parameter_group="CLAIM_SETUP").count(),
        )
        management.call_command("seed_ol_claim_setup", verbosity=0)
        second_counts = (
            OLClaimType.objects.count(),
            OLClaimReason.objects.count(),
            OLClaimStatus.objects.count(),
            OLDischargeType.objects.count(),
            OLCorrespondentType.objects.count(),
            OLParameterTableRegistry.objects.filter(parameter_group="CLAIM_SETUP").count(),
        )
        self.assertEqual(first_counts, second_counts)
        self.assertEqual(first_counts, (7, 6, 9, 3, 4, 5))
        self.assertEqual(
            list(OLClaimStatus.objects.get(code="REGISTERED").allowed_transitions),
            ["DOCUMENTS_PENDING", "UNDER_ASSESSMENT"],
        )

    def test_admin_registration_exposes_table_first_columns_for_all_catalogs(self):
        expected = {
            OLClaimType: {"claim_category", "calculation_basis", "require_approval"},
            OLClaimReason: {"claim_type", "reason_category"},
            OLClaimStatus: {"display_order", "badge_type", "is_terminal"},
            OLDischargeType: {"discharge_category", "template_code"},
            OLCorrespondentType: {"correspondence_category", "communication_channel"},
        }
        for model, columns in expected.items():
            self.assertIn(model, admin.site._registry)
            list_display = set(admin.site._registry[model].list_display)
            self.assertTrue(columns.issubset(list_display), model.__name__)
