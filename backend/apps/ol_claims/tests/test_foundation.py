from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.common.models import DomainEvent
from apps.governance.models import AuditLog
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
from apps.ol_claims.services.validation import calculate_max_claimable, validate_eligibility
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.ol_policies.models import Policy, PolicyBenefit, PolicyMember
from apps.partners.models import Partner
from apps.ol_parameters.models import OLClaimReason, OLClaimType
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
