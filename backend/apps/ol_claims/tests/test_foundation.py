from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.common.models import DomainEvent
from apps.governance.models import ApprovalRequest, AuditLog
from apps.ol_claims.admin import (
    OLClaimAdmin,
    OLClaimDocumentAdmin,
    OLClaimFileNoteAdmin,
    OLClaimItemAdmin,
    OLClaimRequisitionAdmin,
    OLClaimantAdmin,
)
from apps.ol_claims.errors import CLAIM_ERROR_REGISTRY, registry_error
from apps.ol_claims.models import (
    ClaimMedicalStatus,
    ClaimStatus,
    ClaimantType,
    OLClaim,
    OLClaimDocument,
    OLClaimFileNote,
    OLClaimItem,
    OLClaimRequisition,
    OLClaimant,
)
from apps.ol_claims.options import claim_type_options
from apps.ol_claims.permissions import ACTIONS, OLClaimPermission, has_ol_claim_permission
from apps.ol_claims.services.document_service import can_proceed_to_assessment, get_required_documents
from apps.ol_claims.services.assessment import add_file_note, assess_claim
from apps.ol_claims.services.loan_offset import apply_loan_offset, calculate_net_payout
from apps.ol_claims.services.requisition import raise_requisition
from apps.ol_claims.services.medical import evaluate_medical_requirements, record_medical_result, require_medical_review
from apps.ol_claims.services.validation import calculate_max_claimable, validate_eligibility
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.ol_policies.models import LoanStatus, Policy, PolicyBenefit, PolicyLoan, PolicyMember
from apps.governance.services.approval_service import ApprovalService
from apps.partners.models import Partner
from apps.ol_parameters.models import OLClaimReason, OLClaimType, OLMedicalCode, OLMedicalLimit
from apps.users.models import UserPermission


class OLClaimFoundationTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="claims-admin",
            email="claims-admin@example.com",
            password="Strong-claims-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-CLM-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Asha Mwinyi",
            email="asha.claims@example.com",
            mobile_number="+255711100001",
            phone="+255711100001",
        )
        self.agent = Partner.objects.create(
            partner_number="ZIC-CLM-A-0001",
            partner_type="AGENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Juma Claims Agent",
            email="juma.claims@example.com",
            mobile_number="+255711100002",
            phone="+255711100002",
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-CLAIMS-FOUNDATION-0001",
            quote_name="Claims foundation quote",
            quote_date=date(2026, 1, 1),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-CLAIMS-FOUNDATION-0001",
            status="AWAITING_FIRST_PREMIUM",
            partner=self.partner,
            agent_partner=self.agent,
            currency="TZS",
        )
        self.policy = Policy.objects.create(
            policy_number="POL-CLAIMS-FOUNDATION-0001",
            proposal_ref=proposal,
            partner=self.partner,
            agent=self.agent,
            product_plan_ref="OL_TERM_STANDARD",
            currency="TZS",
            sum_assured=Decimal("25000000.00"),
            premium_amount=Decimal("125000.00"),
            premium_frequency="ANNUALLY",
            term_years=10,
            risk_commencement_date=date(2026, 1, 15),
            maturity_date=date(2036, 1, 14),
            status="ACTIVE",
        )
        self.client.force_authenticate(self.user)

    def make_claim(self):
        claim = OLClaim.objects.create(
            policy_ref=self.policy,
            claim_type="DEATH",
            claim_date=date(2026, 4, 1),
            cause_of_claim="Natural causes",
            description="Foundation claim fixture.",
            registered_by=self.user,
            created_by=self.user,
            source_channel="WEB",
        )
        claimant = OLClaimant.objects.create(
            claim=claim,
            claimant_type=ClaimantType.INSURED,
            relationship="Principal member",
            name="Asha Mwinyi",
            identity_number="NIDA-CLAIMS-0001",
            age=36,
            gender="FEMALE",
            created_by=self.user,
        )
        claim.claimant_ref = claimant
        claim.save(update_fields=["claimant_ref", "updated_at"])
        OLClaimItem.objects.create(
            claim=claim,
            benefit_type="DEATH_BENEFIT",
            sum_assured=Decimal("25000000.00"),
            calculated_amount=Decimal("25000000.00"),
            created_by=self.user,
        )
        OLClaimDocument.objects.create(
            claim=claim,
            document_type="DEATH_CERTIFICATE",
            file_reference="claims/2026/death-certificate.pdf",
            mandatory_flag=True,
            uploaded_by=self.user,
            created_by=self.user,
        )
        OLClaimFileNote.objects.create(
            claim=claim,
            note_text="Initial foundation review note.",
            created_by=self.user,
        )
        OLClaimRequisition.objects.create(
            claim=claim,
            amount=Decimal("25000000.00"),
            bank_details_json={"bank_name": "Zanzibar Bank"},
            status="DRAFT",
            created_by=self.user,
        )
        return claim

    def test_claim_creation_relationships_and_status_enum(self):
        claim = self.make_claim()
        self.assertTrue(claim.claim_number.startswith("CLM-"))
        self.assertEqual(claim.status, ClaimStatus.REGISTERED)
        self.assertEqual(claim.claimant_ref.claim, claim)
        self.assertEqual(claim.items.get().benefit_type, "DEATH_BENEFIT")
        self.assertEqual(claim.documents.get().document_type, "DEATH_CERTIFICATE")
        self.assertEqual(claim.file_notes.get().created_by, self.user)
        self.assertEqual(claim.requisition.amount, Decimal("25000000.00"))

        claim.status = "NOT_A_CLAIM_STATUS"
        with self.assertRaises(ValidationError):
            claim.full_clean()

    def test_error_registry_has_required_teachable_shape(self):
        required_codes = {
            "CLAIM_POLICY_INACTIVE",
            "CLAIM_DUPLICATE",
            "CLAIM_WAITING_PERIOD_ACTIVE",
            "CLAIM_BENEFIT_NOT_COVERED",
            "CLAIM_MANDATORY_DOC_MISSING",
            "CLAIM_AMOUNT_EXCEEDS_LIMIT",
        }
        self.assertTrue(required_codes.issubset(CLAIM_ERROR_REGISTRY))
        for definition in CLAIM_ERROR_REGISTRY.values():
            self.assertTrue(definition["message"])
            self.assertGreaterEqual(definition["status_code"], 400)
            self.assertTrue(definition["resolution_steps"])
        error = registry_error("CLAIM_AMOUNT_EXCEEDS_LIMIT")
        self.assertEqual(error.error_code, "CLAIM_AMOUNT_EXCEEDS_LIMIT")
        self.assertTrue(error.resolution_steps)
        self.assertEqual(error.doc_ref, "docs/OL_CLAIMS_DESIGN.md")

    def test_list_and_detail_return_human_readable_claim_fields(self):
        claim = self.make_claim()
        list_response = self.client.get("/api/v1/ol/claims/")
        self.assertEqual(list_response.status_code, 200)
        row = list_response.data["data"]["results"][0]
        self.assertEqual(row["claim_number"], claim.claim_number)
        self.assertEqual(row["policy_number"], self.policy.policy_number)
        self.assertEqual(row["policyholder_name"], "Asha Mwinyi")
        self.assertEqual(row["policyholder_display"], "ZIC-CLM-P-0001 — Asha Mwinyi")
        self.assertEqual(row["product_display"], "OL_TERM_STANDARD")
        self.assertNotIn(str(self.partner.pk), row["policyholder_display"])
        self.assertEqual(row["allowed_actions"], ["view", "assess", "cancel", "print"])

        detail_response = self.client.get(f"/api/v1/ol/claims/{claim.pk}/")
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.data["data"]
        self.assertEqual(detail["claim_number"], claim.claim_number)
        self.assertEqual(detail["claimant"]["name"], "Asha Mwinyi")
        self.assertEqual(len(detail["items"]), 1)
        self.assertEqual(len(detail["documents"]), 1)
        self.assertEqual(len(detail["file_notes"]), 1)
        self.assertEqual(detail["requisition"]["requisition_number"].startswith("CLM-REQ-"), True)
        self.assertEqual(detail["policy_context"]["policy_number"], self.policy.policy_number)

    def test_unknown_claim_returns_structured_error_without_identifier_leak(self):
        response = self.client.get(f"/api/v1/ol/claims/{uuid4()}/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error_code"], "CLAIM_NOT_FOUND")
        self.assertTrue(response.data["resolution_steps"])
        self.assertEqual(response.data["doc_ref"], "docs/OL_CLAIMS_DESIGN.md")
        self.assertNotIn("claim could not be found", response.data["message"].lower().replace("claim", ""))

    def test_permission_catalog_and_claim_roles_are_registered(self):
        call_command("seed_ol_claim_permissions", verbosity=0)
        expected = {f"ol_claims.{action}" for action in ACTIONS}
        actual = set(UserPermission.objects.filter(module="ol_claims").values_list("codename", flat=True))
        self.assertSetEqual(actual, expected)
        self.assertEqual(OLClaimPermission.code_for("list"), "ol_claims.view")
        self.assertTrue(has_ol_claim_permission(self.user, "settle"))
        self.assertEqual(UserPermission.objects.filter(module="ol_claims", is_active=True).count(), len(ACTIONS))

    def test_all_claim_models_are_registered_in_admin(self):
        for model, model_admin in (
            (OLClaim, OLClaimAdmin),
            (OLClaimant, OLClaimantAdmin),
            (OLClaimItem, OLClaimItemAdmin),
            (OLClaimDocument, OLClaimDocumentAdmin),
            (OLClaimFileNote, OLClaimFileNoteAdmin),
            (OLClaimRequisition, OLClaimRequisitionAdmin),
        ):
            self.assertTrue(admin.site.is_registered(model))
            self.assertIsInstance(admin.site._registry[model], model_admin)

    def test_domain_event_helper_can_record_claim_event(self):
        from apps.ol_claims.events import CLAIM_REGISTERED, emit_claim_registered

        claim = self.make_claim()
        event = emit_claim_registered(
            claim,
            actor=self.user,
            reason="Initial notification received",
            source_channel="WEB",
        )
        self.assertEqual(event.event_type, CLAIM_REGISTERED)
        self.assertEqual(event.aggregate_type, "OLClaim")
        self.assertEqual(event.aggregate_id, str(claim.pk))
        self.assertEqual(event.payload["claim_number"], claim.claim_number)
        self.assertEqual(event.payload["source_channel"], "WEB")
        self.assertEqual(DomainEvent.objects.filter(pk=event.pk).count(), 1)

    def test_validation_accepts_active_policy_and_audits_each_check(self):
        claim_type = OLClaimType.objects.create(
            code="DEATH_CLAIM",
            name="Death Claim",
            description="Configured death claim.",
            claim_category="DEATH",
            calculation_basis="SUM_ASSURED",
            duplicate_check_rule="POLICY_AND_TYPE",
            waiting_period_days=0,
            payable_to_rules={"default": "beneficiary"},
            require_documents=["DEATH_CERTIFICATE"],
            require_approval=True,
            effective_from=date(2026, 1, 1),
        )
        result = validate_eligibility(
            self.policy,
            None,
            claim_type.code,
            date(2026, 4, 1),
            actor=self.user,
            source_channel="WEB",
        )
        self.assertTrue(result["eligible"])
        self.assertEqual(result["claim_category"], "DEATH")
        self.assertEqual(result["require_documents"], ["DEATH_CERTIFICATE"])
        self.assertGreaterEqual(
            AuditLog.objects.filter(entity_type="ol_claims.claim_validation", object_id=str(self.policy.pk)).count(),
            4,
        )

    def test_waiting_period_blocks_claim_with_teachable_error(self):
        claim_type = OLClaimType.objects.create(
            code="CRITICAL_ILLNESS_CLAIM",
            name="Critical Illness Claim",
            claim_category="CRITICAL_ILLNESS",
            calculation_basis="SUM_ASSURED",
            duplicate_check_rule="POLICY_AND_REASON",
            waiting_period_days=90,
            payable_to_rules={"default": "policyholder"},
            effective_from=date(2026, 1, 1),
        )
        with self.assertRaises(Exception) as raised:
            validate_eligibility(
                self.policy,
                None,
                claim_type.code,
                date(2026, 2, 1),
                actor=self.user,
            )
        self.assertEqual(raised.exception.error_code, "CLAIM_WAITING_PERIOD_ACTIVE")
        self.assertTrue(raised.exception.resolution_steps)

    def test_inactive_policy_blocks_claim_registration(self):
        claim_type = OLClaimType.objects.create(
            code="DISABILITY_CLAIM",
            name="Disability Claim",
            claim_category="DISABILITY",
            calculation_basis="BENEFIT_AMOUNT",
            duplicate_check_rule="NONE",
            waiting_period_days=0,
            payable_to_rules={"default": "policyholder"},
            effective_from=date(2026, 1, 1),
        )
        self.policy.status = "EXPIRED"
        self.policy.save(update_fields=["status"])
        with self.assertRaises(Exception) as raised:
            validate_eligibility(self.policy, None, claim_type.code, date(2026, 4, 1), actor=self.user)
        self.assertEqual(raised.exception.error_code, "CLAIM_POLICY_INACTIVE")

    def test_duplicate_settled_claim_is_blocked_by_configured_rule(self):
        claim_type = OLClaimType.objects.create(
            code="MATURITY_CLAIM",
            name="Maturity Claim",
            claim_category="MATURITY",
            calculation_basis="BENEFIT_AMOUNT",
            duplicate_check_rule="POLICY_AND_TYPE",
            waiting_period_days=0,
            payable_to_rules={"default": "policyholder"},
            effective_from=date(2026, 1, 1),
        )
        existing = OLClaim.objects.create(
            policy_ref=self.policy,
            claim_type=claim_type.code,
            claim_date=date(2026, 3, 1),
            status=ClaimStatus.SETTLED,
            registered_by=self.user,
            created_by=self.user,
        )
        claimant = OLClaimant.objects.create(
            claim=existing,
            claimant_type=ClaimantType.POLICYHOLDER,
            name="Asha Mwinyi",
            created_by=self.user,
        )
        existing.claimant_ref = claimant
        existing.save(update_fields=["claimant_ref", "updated_at"])
        with self.assertRaises(Exception) as raised:
            validate_eligibility(self.policy, claimant, claim_type.code, date(2026, 4, 1), actor=self.user)
        self.assertEqual(raised.exception.error_code, "CLAIM_DUPLICATE")

    def test_benefit_calculation_uses_configured_basis_and_amount(self):
        sum_assured_type = OLClaimType.objects.create(
            code="DEATH_CALCULATION",
            name="Death Calculation",
            claim_category="DEATH",
            calculation_basis="SUM_ASSURED",
            duplicate_check_rule="NONE",
            payable_to_rules={},
            effective_from=date(2026, 1, 1),
        )
        self.assertEqual(
            calculate_max_claimable(self.policy, "DEATH", claim_type=sum_assured_type.code),
            Decimal("25000000.00"),
        )

        benefit_type = OLClaimType.objects.create(
            code="BENEFIT_CALCULATION",
            name="Benefit Calculation",
            claim_category="CRITICAL_ILLNESS",
            calculation_basis="BENEFIT_AMOUNT",
            duplicate_check_rule="NONE",
            payable_to_rules={},
            effective_from=date(2026, 1, 1),
        )
        PolicyBenefit.objects.create(
            policy=self.policy,
            benefit_type="CRITICAL_ILLNESS",
            calculation_basis="FIXED",
            amount=Decimal("4000000.00"),
        )
        self.assertEqual(
            calculate_max_claimable(self.policy, "CRITICAL_ILLNESS", claim_type=benefit_type.code),
            Decimal("4000000.00"),
        )

    def test_claim_option_endpoints_return_active_labeled_data(self):
        claim_type = OLClaimType.objects.create(
            code="DEATH_CLAIM",
            name="Death Claim",
            claim_category="DEATH",
            calculation_basis="SUM_ASSURED",
            duplicate_check_rule="POLICY_AND_TYPE",
            waiting_period_days=0,
            payable_to_rules={},
            effective_from=date(2026, 1, 1),
        )
        OLClaimReason.objects.create(
            code="NATURAL_DEATH",
            name="Natural death",
            claim_type=claim_type,
            reason_category="EVENT",
            effective_from=date(2026, 1, 1),
        )
        OLClaimType.objects.create(
            code="INACTIVE_CLAIM",
            name="Inactive Claim",
            claim_category="OTHER",
            calculation_basis="FIXED_AMOUNT",
            duplicate_check_rule="NONE",
            payable_to_rules={},
            is_active=False,
            effective_from=date(2026, 1, 1),
        )
        PolicyMember.objects.create(
            policy=self.policy,
            member_relation="PRINCIPAL",
            name="Asha Mwinyi",
            dob=date(1990, 6, 15),
            gender="FEMALE",
            benefit_amount=Decimal("25000000.00"),
        )
        PolicyBenefit.objects.create(
            policy=self.policy,
            benefit_type="DEATH_BENEFIT",
            calculation_basis="FIXED",
            amount=Decimal("25000000.00"),
        )

        types_response = self.client.get("/api/v1/ol/claims/options/types/?q=Death&page=1&page_size=1")
        self.assertEqual(types_response.status_code, 200)
        type_items = types_response.data["data"]["items"]
        self.assertEqual(len(type_items), 1)
        self.assertEqual(type_items[0]["value"], "DEATH_CLAIM")
        self.assertEqual(type_items[0]["label"], "DEATH_CLAIM — Death Claim")
        self.assertNotIn("INACTIVE_CLAIM", str(types_response.data))

        reasons_response = self.client.get("/api/v1/ol/claims/options/reasons/?claim_type=DEATH_CLAIM")
        self.assertEqual(reasons_response.status_code, 200)
        self.assertEqual(reasons_response.data["data"]["items"][0]["label"], "NATURAL_DEATH — Natural death")

        benefits_response = self.client.get(f"/api/v1/ol/claims/options/benefits/?policy_id={self.policy.pk}")
        self.assertEqual(benefits_response.status_code, 200)
        self.assertEqual(benefits_response.data["data"]["items"][0]["label"], "DEATH_BENEFIT — Benefit")
        self.assertNotIn(str(self.policy.pk), benefits_response.data["data"]["items"][0]["label"])

        members_response = self.client.get(f"/api/v1/ol/claims/options/members/?policy_id={self.policy.pk}")
        self.assertEqual(members_response.status_code, 200)
        self.assertEqual(members_response.data["data"]["items"][0]["label"], "Asha Mwinyi — PRINCIPAL")

    def test_registration_creates_claimant_item_and_audit_event(self):
        claim_type = OLClaimType.objects.create(
            code="DEATH_CLAIM",
            name="Death Claim",
            claim_category="DEATH",
            calculation_basis="SUM_ASSURED",
            duplicate_check_rule="POLICY_AND_TYPE",
            waiting_period_days=0,
            payable_to_rules={},
            require_documents=["DEATH_CERTIFICATE"],
            effective_from=date(2026, 1, 1),
        )
        member = PolicyMember.objects.create(
            policy=self.policy,
            member_relation="PRINCIPAL",
            name="Asha Mwinyi",
            dob=date(1990, 6, 15),
            gender="FEMALE",
            benefit_amount=Decimal("25000000.00"),
        )
        response = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/claims/",
            {
                "claim_type": claim_type.code,
                "claim_date": "2026-04-01",
                "cause_of_claim": "Natural death",
                "description": "Registration test claim.",
                "member_id": str(member.pk),
                "benefit_type": "DEATH",
            },
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="claim-registration-001",
            HTTP_X_SOURCE_CHANNEL="WEB",
        )
        self.assertEqual(response.status_code, 201)
        claim = OLClaim.objects.get(claim_number=response.data["data"]["claim_number"])
        self.assertEqual(claim.status, ClaimStatus.REGISTERED)
        self.assertEqual(claim.claimant_ref.name, "Asha Mwinyi")
        self.assertEqual(claim.items.get().calculated_amount, Decimal("25000000.00"))
        self.assertEqual(claim.source_channel, "WEB")
        self.assertTrue(DomainEvent.objects.filter(event_type="ClaimRegistered", aggregate_id=str(claim.pk)).exists())
        self.assertTrue(
            AuditLog.objects.filter(
                app_label="ol_claims",
                model_name="olclaim",
                object_id=str(claim.pk),
                action_type="CREATE",
            ).exists()
        )

    def test_registration_retry_returns_original_claim_and_changed_payload_conflicts(self):
        OLClaimType.objects.create(
            code="DISABILITY_CLAIM",
            name="Disability Claim",
            claim_category="DISABILITY",
            calculation_basis="SUM_ASSURED",
            duplicate_check_rule="NONE",
            waiting_period_days=0,
            payable_to_rules={},
            effective_from=date(2026, 1, 1),
        )
        payload = {
            "claim_type": "DISABILITY_CLAIM",
            "claim_date": "2026-04-01",
            "claimant_details": {
                "claimant_type": "POLICYHOLDER",
                "name": "Asha Mwinyi",
                "relationship": "Policyholder",
                "identity_number": "NIDA-001",
                "age": 36,
                "gender": "FEMALE",
            },
        }
        first = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/claims/",
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="claim-registration-002",
        )
        retry = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/claims/",
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="claim-registration-002",
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(first.data["data"]["claim_number"], retry.data["data"]["claim_number"])
        self.assertEqual(OLClaim.objects.filter(idempotency_key="claim-registration-002").count(), 1)

        changed = {**payload, "description": "Changed after first submission."}
        conflict = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/claims/",
            changed,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="claim-registration-002",
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.data["error_code"], "CLAIM_IDEMPOTENCY_CONFLICT")
        self.assertTrue(conflict.data["resolution_steps"])

    def test_registration_requires_idempotency_and_claimant_details(self):
        response = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/claims/",
            {"claim_type": "DEATH_CLAIM", "claim_date": "2026-04-01"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error_code"], "CLAIM_IDEMPOTENCY_REQUIRED")
        self.assertTrue(response.data["resolution_steps"])

        OLClaimType.objects.create(
            code="DEATH_CLAIM",
            name="Death Claim",
            claim_category="DEATH",
            calculation_basis="SUM_ASSURED",
            duplicate_check_rule="NONE",
            waiting_period_days=0,
            payable_to_rules={},
            effective_from=date(2026, 1, 1),
        )
        response = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/claims/",
            {"claim_type": "DEATH_CLAIM", "claim_date": "2026-04-01"},
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="claim-registration-003",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error_code"], "CLAIM_CLAIMANT_REQUIRED")
        self.assertIn("claimant_details.name", response.data["field_errors"])

    def test_document_requirement_engine_blocks_until_all_required_documents_are_uploaded(self):
        claim_type = OLClaimType.objects.create(
            code="DOCUMENTED_DEATH_CLAIM",
            name="Documented Death Claim",
            claim_category="DEATH",
            calculation_basis="SUM_ASSURED",
            duplicate_check_rule="NONE",
            waiting_period_days=0,
            payable_to_rules={},
            require_documents=["DEATH_CERTIFICATE", "IDENTITY_DOCUMENT"],
            effective_from=date(2026, 1, 1),
        )
        claim = self.make_claim()
        claim.claim_type = claim_type.code
        claim.save(update_fields=["claim_type", "updated_at"])
        claim.documents.all().delete()
        self.assertEqual(get_required_documents(claim_type.code), ["DEATH_CERTIFICATE", "IDENTITY_DOCUMENT"])

        blocked = self.client.post(f"/api/v1/ol/claims/{claim.pk}/assessment-readiness/", {}, format="json")
        self.assertEqual(blocked.status_code, 422)
        self.assertEqual(blocked.data["error_code"], "CLAIM_MANDATORY_DOC_MISSING")
        self.assertEqual(
            set(blocked.data["error"]["details"]["missing_document_types"]),
            {"DEATH_CERTIFICATE", "IDENTITY_DOCUMENT"},
        )

        first = self.client.post(
            f"/api/v1/ol/claims/{claim.pk}/documents/",
            {"document_type": "DEATH_CERTIFICATE", "file": SimpleUploadedFile("death.pdf", b"pdf-evidence")},
            format="multipart",
            HTTP_X_SOURCE_CHANNEL="WEB",
        )
        self.assertEqual(first.status_code, 201)
        self.assertFalse(first.data["data"]["all_mandatory_uploaded"])

        second = self.client.post(
            f"/api/v1/ol/claims/{claim.pk}/documents/",
            {"document_type": "IDENTITY_DOCUMENT", "file_reference": "claims/evidence/identity.pdf"},
            format="json",
        )
        self.assertEqual(second.status_code, 201)
        self.assertTrue(second.data["data"]["all_mandatory_uploaded"])

        listed = self.client.get(f"/api/v1/ol/claims/{claim.pk}/documents/")
        self.assertEqual(listed.status_code, 200)
        self.assertTrue(listed.data["data"]["all_mandatory_uploaded"])
        self.assertEqual(listed.data["data"]["missing_document_types"], [])
        self.assertEqual(listed.data["data"]["uploaded"], 2)
        self.assertEqual(len(listed.data["data"]["results"]), 2)
        self.assertNotIn(str(claim.pk), listed.data["data"]["results"][0]["document_type"])

        readiness = self.client.post(f"/api/v1/ol/claims/{claim.pk}/assessment-readiness/", {}, format="json")
        self.assertEqual(readiness.status_code, 200)
        self.assertTrue(readiness.data["data"]["can_proceed_to_assessment"])
        self.assertTrue(can_proceed_to_assessment(claim.pk, actor=self.user))
        self.assertGreaterEqual(
            AuditLog.objects.filter(action_type="DOCUMENT_UPLOAD", app_label="ol_claims", model_name="claimdocument").count(),
            2,
        )

    def test_medical_parameter_sets_pending_and_blocks_assessment(self):
        claim_type = OLClaimType.objects.create(
            code="MEDICAL_REQUIRED_CLAIM",
            name="Medical Required Claim",
            claim_category="CRITICAL_ILLNESS",
            calculation_basis="SUM_ASSURED",
            duplicate_check_rule="NONE",
            waiting_period_days=0,
            payable_to_rules={"medical_required": True},
            require_documents=[],
            effective_from=date(2026, 1, 1),
        )
        claim = self.make_claim()
        claim.claim_type = claim_type.code
        claim.save(update_fields=["claim_type", "updated_at"])
        evaluated = evaluate_medical_requirements(claim, actor=self.user, source_channel="WEB")
        claim.refresh_from_db()
        self.assertTrue(evaluated["medical_required"])
        self.assertEqual(claim.medical_status, ClaimMedicalStatus.PENDING)
        self.assertEqual(claim.status, ClaimStatus.PENDING_MEDICAL)
        with self.assertRaises(Exception) as raised:
            can_proceed_to_assessment(claim.pk, actor=self.user)
        self.assertEqual(raised.exception.error_code, "CLAIM_MEDICAL_REVIEW_REQUIRED")

    def test_medical_results_clear_reject_or_apply_loading(self):
        OLClaimType.objects.create(
            code="MEDICAL_OUTCOME_CLAIM",
            name="Medical Outcome Claim",
            claim_category="DISABILITY",
            calculation_basis="SUM_ASSURED",
            duplicate_check_rule="NONE",
            waiting_period_days=0,
            payable_to_rules={},
            require_documents=[],
            effective_from=date(2026, 1, 1),
        )
        cleared = self.make_claim()
        cleared.claim_type = "MEDICAL_OUTCOME_CLAIM"
        cleared.save(update_fields=["claim_type", "updated_at"])
        require_medical_review(cleared.pk, actor=self.user, reason="Review requested.")
        cleared = record_medical_result(cleared.pk, result="CLEARED", reason="Evidence supports the claim.", actor=self.user)
        self.assertEqual(cleared.medical_status, ClaimMedicalStatus.CLEARED)
        self.assertEqual(cleared.status, ClaimStatus.REGISTERED)

        rejected = self.make_claim()
        rejected.claim_type = "MEDICAL_OUTCOME_CLAIM"
        rejected.save(update_fields=["claim_type", "updated_at"])
        require_medical_review(rejected.pk, actor=self.user, reason="Review requested.")
        rejected = record_medical_result(rejected.pk, result="REJECTED", reason="Evidence does not support the claim.", actor=self.user)
        self.assertEqual(rejected.medical_status, ClaimMedicalStatus.REJECTED)
        self.assertEqual(rejected.status, ClaimStatus.REJECTED)

        loading = self.make_claim()
        loading.claim_type = "MEDICAL_OUTCOME_CLAIM"
        loading.save(update_fields=["claim_type", "updated_at"])
        before_amount = loading.items.get().calculated_amount
        require_medical_review(loading.pk, actor=self.user, reason="Review requested.")
        loading = record_medical_result(loading.pk, result="LOADING", loading_factor=Decimal("1.2500"), actor=self.user)
        loading.refresh_from_db()
        self.assertEqual(loading.medical_status, ClaimMedicalStatus.LOADING)
        self.assertEqual(loading.status, ClaimStatus.REGISTERED)
        self.assertEqual(loading.items.get().calculated_amount, (before_amount * Decimal("1.25")).quantize(Decimal("0.01")))
        self.assertEqual(loading.medical_loading_factor, Decimal("1.2500"))

    def test_medical_limit_parameter_triggers_review_when_claim_exceeds_limit(self):
        claim_type = OLClaimType.objects.create(
            code="LIMITED_MEDICAL_CLAIM",
            name="Limited Medical Claim",
            claim_category="MEDICAL",
            calculation_basis="SUM_ASSURED",
            duplicate_check_rule="NONE",
            waiting_period_days=0,
            payable_to_rules={},
            require_documents=[],
            effective_from=date(2026, 1, 1),
        )
        medical_code = OLMedicalCode.objects.create(
            code="MEDICAL_EXAM",
            name="Medical examination",
            medical_category="EXAMINATION",
            effective_from=date(2026, 1, 1),
        )
        OLMedicalLimit.objects.create(
            code="MEDICAL_LIMIT_1M",
            name="Medical limit above one million",
            medical_code=medical_code,
            age_from=0,
            age_to=150,
            sum_assured_from=Decimal("1000000.00"),
            sum_assured_to=Decimal("100000000.00"),
            limit_type="MEDICAL",
            limit_amount=Decimal("1000000.00"),
            required_frequency="ANNUAL",
            mandatory_flag=False,
            effective_from=date(2026, 1, 1),
        )
        claim = self.make_claim()
        claim.claim_type = claim_type.code
        claim.save(update_fields=["claim_type", "updated_at"])
        evaluated = evaluate_medical_requirements(claim, actor=self.user)
        self.assertTrue(evaluated["medical_required"])
        self.assertIn("MEDICAL_LIMIT_1M", claim.medical_reason)

    def _assessment_claim_type(self):
        return OLClaimType.objects.create(
            code="ASSESSABLE_CLAIM",
            name="Assessable Claim",
            claim_category="DEATH",
            calculation_basis="SUM_ASSURED",
            duplicate_check_rule="NONE",
            waiting_period_days=0,
            payable_to_rules={},
            require_documents=[],
            allow_waiver_of_premium=True,
            effective_from=date(2026, 1, 1),
        )

    def test_assessment_updates_amount_status_fraud_waiver_and_note(self):
        claim_type = self._assessment_claim_type()
        claim = self.make_claim()
        claim.claim_type = claim_type.code
        claim.save(update_fields=["claim_type", "updated_at"])
        response = self.client.post(
            f"/api/v1/ol/claims/{claim.pk}/assess/",
            {
                "assessed_amount": "20000000.00",
                "assessment_notes": "Evidence reviewed and liability confirmed.",
                "fraud_flag": True,
                "fraud_flag_reason": "Identity and payment evidence require enhanced review.",
                "waiver_of_premium_days": 30,
            },
            format="json",
            HTTP_X_SOURCE_CHANNEL="WEB",
        )
        self.assertEqual(response.status_code, 200)
        claim.refresh_from_db()
        self.assertEqual(claim.status, ClaimStatus.ASSESSED)
        self.assertTrue(claim.fraud_flag)
        self.assertEqual(claim.fraud_flag_reason, "Identity and payment evidence require enhanced review.")
        self.assertEqual(claim.items.get().approved_amount, Decimal("20000000.00"))
        self.assertTrue(claim.waiver_of_premium_applied)
        self.assertEqual(claim.waiver_of_premium_days, 30)
        self.assertEqual(claim.policy_ref.contract_snapshot["premium_waiver"]["claim_number"], claim.claim_number)
        self.assertTrue(DomainEvent.objects.filter(event_type="ClaimAssessed", aggregate_id=str(claim.pk)).exists())
        self.assertTrue(AuditLog.objects.filter(action_type="ASSESS", app_label="ol_claims", model_name="olclaim").exists())

        note_response = self.client.post(
            f"/api/v1/ol/claims/{claim.pk}/notes/",
            {"note_text": "Assessment completed by Claims Administration."},
            format="json",
        )
        self.assertEqual(note_response.status_code, 201)
        notes = self.client.get(f"/api/v1/ol/claims/{claim.pk}/notes/")
        self.assertEqual(notes.status_code, 200)
        self.assertEqual(notes.data["data"][0]["note_text"], "Assessment completed by Claims Administration.")

    def test_assessment_rejects_amount_above_calculated_maximum_and_missing_fraud_reason(self):
        claim_type = self._assessment_claim_type()
        too_high = self.make_claim()
        too_high.claim_type = claim_type.code
        too_high.save(update_fields=["claim_type", "updated_at"])
        response = self.client.post(
            f"/api/v1/ol/claims/{too_high.pk}/assess/",
            {"assessed_amount": "25000001.00", "assessment_notes": "Reviewed."},
            format="json",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "CLAIM_ASSESSMENT_AMOUNT_INVALID")
        self.assertIn("assessed_amount", response.data["field_errors"])
        too_high.refresh_from_db()
        self.assertEqual(too_high.status, ClaimStatus.REGISTERED)

        fraud_claim = self.make_claim()
        fraud_claim.claim_type = claim_type.code
        fraud_claim.save(update_fields=["claim_type", "updated_at"])
        response = self.client.post(
            f"/api/v1/ol/claims/{fraud_claim.pk}/assess/",
            {"assessed_amount": "20000000.00", "assessment_notes": "Reviewed.", "fraud_flag": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error_code"], "CLAIM_FRAUD_REASON_REQUIRED")
        self.assertIn("fraud_flag_reason", response.data["field_errors"])

    def test_assessment_service_rejects_empty_internal_note(self):
        claim = self.make_claim()
        with self.assertRaises(Exception) as raised:
            add_file_note(claim.pk, note_text="", actor=self.user)
        self.assertEqual(raised.exception.error_code, "CLAIM_NOTE_REQUIRED")

    def test_financial_summary_deducts_active_loans_and_applies_offset(self):
        claim_type = self._assessment_claim_type()
        claim = self.make_claim()
        claim.claim_type = claim_type.code
        claim.save(update_fields=["claim_type", "updated_at"])
        assess_claim(claim.pk, assessed_amount=Decimal("20000000.00"), assessment_notes="Benefit confirmed.", actor=self.user)
        loan = PolicyLoan.objects.create(
            policy=claim.policy_ref,
            principal_amount=Decimal("5000000.00"),
            outstanding_principal=Decimal("5000000.00"),
            outstanding_interest=Decimal("1000000.00"),
            currency="TZS",
            status=LoanStatus.DISBURSED,
        )
        summary = calculate_net_payout(claim.pk)
        self.assertEqual(summary["gross_amount"], Decimal("20000000.00"))
        self.assertEqual(summary["loan_offset"], Decimal("6000000.00"))
        self.assertEqual(summary["net_payout"], Decimal("14000000.00"))
        self.assertFalse(summary["loan_offset_applied"])

        api_summary = self.client.get(f"/api/v1/ol/claims/{claim.pk}/financial-summary/")
        self.assertEqual(api_summary.status_code, 200)
        self.assertEqual(api_summary.data["data"]["net_payout"], Decimal("14000000.00"))
        self.assertEqual(api_summary.data["data"]["loan_breakdown"], [])

        offset = apply_loan_offset(claim.pk, actor=self.user, source_channel="WEB")
        self.assertEqual(offset.offset_amount, Decimal("6000000.00"))
        self.assertEqual(offset.net_payout, Decimal("14000000.00"))
        loan.refresh_from_db()
        self.assertEqual(loan.outstanding_principal, Decimal("0.00"))
        self.assertEqual(loan.outstanding_interest, Decimal("0.00"))
        self.assertEqual(loan.status, LoanStatus.REPAID)
        self.assertEqual(loan.repayments.count(), 1)
        self.assertTrue(DomainEvent.objects.filter(event_type="ClaimLoanOffsetApplied", aggregate_id=str(claim.pk)).exists())
        self.assertTrue(AuditLog.objects.filter(action_type="LOAN_OFFSET", app_label="ol_claims", model_name="claimloanoffset").exists())
        self.assertEqual(calculate_net_payout(claim.pk)["loan_offset_applied"], True)

    def test_financial_summary_closes_loan_when_balance_exceeds_gross(self):
        claim_type = self._assessment_claim_type()
        claim = self.make_claim()
        claim.claim_type = claim_type.code
        claim.save(update_fields=["claim_type", "updated_at"])
        assess_claim(claim.pk, assessed_amount=Decimal("20000000.00"), assessment_notes="Benefit confirmed.", actor=self.user)
        loan = PolicyLoan.objects.create(
            policy=claim.policy_ref,
            principal_amount=Decimal("30000000.00"),
            outstanding_principal=Decimal("30000000.00"),
            outstanding_interest=Decimal("5000000.00"),
            currency="TZS",
            status=LoanStatus.PARTIALLY_REPAID,
        )
        offset = apply_loan_offset(claim.pk, actor=self.user)
        self.assertEqual(offset.offset_amount, Decimal("20000000.00"))
        self.assertEqual(offset.net_payout, Decimal("0.00"))
        loan.refresh_from_db()
        self.assertEqual(loan.outstanding_principal, Decimal("0.00"))
        self.assertEqual(loan.outstanding_interest, Decimal("0.00"))
        self.assertEqual(loan.status, LoanStatus.REPAID)

    def _assessed_claim_without_requisition(self):
        claim = self.make_claim()
        claim.requisition.delete()
        claim.refresh_from_db()
        claim_type = self._assessment_claim_type()
        claim.claim_type = claim_type.code
        claim.save(update_fields=["claim_type", "updated_at"])
        assess_claim(claim.pk, assessed_amount=Decimal("20000000.00"), assessment_notes="Benefit confirmed.", actor=self.user)
        return claim

    def test_raise_requisition_links_front_office_payment_seam(self):
        claim = self._assessed_claim_without_requisition()
        response = self.client.post(
            f"/api/v1/ol/claims/{claim.pk}/raise-requisition/",
            {
                "bank_details": {
                    "recipient_name": "Asha Mwinyi",
                    "account_name": "Asha Mwinyi",
                    "account_number": "0123456789",
                    "bank_name": "Zanzibar Bank",
                },
                "narration": "Approved death benefit payment.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        requisition = OLClaimRequisition.objects.get(claim=claim)
        claim.refresh_from_db()
        self.assertEqual(claim.status, ClaimStatus.REQUISITIONED)
        self.assertEqual(requisition.status, "REQUISITIONED")
        self.assertEqual(requisition.amount, Decimal("20000000.00"))
        self.assertTrue(requisition.payment_requisition.requisition_number.startswith("FO-CLM-"))
        self.assertEqual(requisition.payment_requisition.department, "CLAIMS")
        self.assertEqual(requisition.payment_requisition.status, "PENDING")
        self.assertTrue(requisition.approval_required)
        self.assertTrue(ApprovalRequest.objects.filter(entity_id=requisition.pk, module="OL_CLAIMS", status="PENDING").exists())
        self.assertTrue(DomainEvent.objects.filter(event_type="ClaimRequisitioned", aggregate_id=str(claim.pk)).exists())
        self.assertTrue(AuditLog.objects.filter(action_type="CLAIM_REQUISITIONED", object_id=str(claim.pk)).exists())
        self.assertEqual(response.data["data"]["payment_requisition_number"], requisition.payment_requisition.requisition_number)

    def test_requisition_requires_assessed_positive_net_payout(self):
        claim = self.make_claim()
        claim.requisition.delete()
        claim.refresh_from_db()
        response = self.client.post(
            f"/api/v1/ol/claims/{claim.pk}/raise-requisition/",
            {"bank_details": {"account_number": "0123456789", "account_name": "Asha Mwinyi"}, "narration": "Payment."},
            format="json",
        )
        self.assertEqual(response.status_code, 422, response.data)
        self.assertEqual(response.data["error_code"], "CLAIM_REQUISITION_REQUIRED")

    def test_approval_event_updates_claim_and_requisition(self):
        claim = self._assessed_claim_without_requisition()
        requisition = raise_requisition(
            claim.pk,
            bank_details={"account_number": "0123456789", "account_name": "Asha Mwinyi"},
            narration="Approved death benefit payment.",
            actor=self.user,
            source_channel="WEB",
        )
        approval = ApprovalRequest.objects.get(pk=requisition.approval_request_id)
        ApprovalService.approve(approval.pk, reviewed_by=self.user, comments="Payment approved.")
        claim.refresh_from_db()
        requisition.refresh_from_db()
        requisition.payment_requisition.refresh_from_db()
        self.assertEqual(claim.status, ClaimStatus.APPROVED)
        self.assertEqual(requisition.status, "APPROVED")
        self.assertEqual(requisition.payment_requisition.status, "APPROVED")
        self.assertTrue(DomainEvent.objects.filter(event_type="ClaimApproved", aggregate_id=str(claim.pk)).exists())
        self.assertTrue(AuditLog.objects.filter(action_type="CLAIM_PAYMENT_APPROVED", object_id=str(claim.pk)).exists())

    def test_rejection_event_updates_claim_and_requisition(self):
        claim = self._assessed_claim_without_requisition()
        requisition = raise_requisition(
            claim.pk,
            bank_details={"account_number": "0123456789", "account_name": "Asha Mwinyi"},
            narration="Death benefit payment review.",
            actor=self.user,
        )
        approval = ApprovalRequest.objects.get(pk=requisition.approval_request_id)
        ApprovalService.reject(approval.pk, reviewed_by=self.user, comments="Bank verification failed.")
        claim.refresh_from_db()
        requisition.refresh_from_db()
        requisition.payment_requisition.refresh_from_db()
        self.assertEqual(claim.status, ClaimStatus.REJECTED)
        self.assertEqual(requisition.status, "REJECTED")
        self.assertEqual(requisition.payment_requisition.status, "REJECTED")
        self.assertTrue(DomainEvent.objects.filter(event_type="ClaimRejected", aggregate_id=str(claim.pk)).exists())
        self.assertTrue(AuditLog.objects.filter(action_type="CLAIM_PAYMENT_REJECTED", object_id=str(claim.pk)).exists())
