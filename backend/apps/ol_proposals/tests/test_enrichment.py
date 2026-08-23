from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase as DRFTestCase

from apps.common.models import DomainEvent
from apps.governance.models import AuditLog
from apps.ol_parameters.models import OLBeneficialType
from apps.ol_proposals.errors import ProposalError
from apps.ol_proposals.models import OLProposal
from apps.ol_proposals.services import enrichment_service
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner

User = get_user_model()


def make_proposal(quotation, **overrides):
    proposal = OLProposal(
        quotation=quotation,
        proposal_number=overrides.pop("proposal_number", "OLP-2026-00001"),
        status="ENRICHMENT",
        **overrides,
    )
    proposal.save()
    return proposal


class EnrichmentSectionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="enrich_ops", password="Password@12345", email="enrich_ops@zic.tz")
        self.policyholder = Partner.objects.create(
            partner_number="PT-OLP-E1", partner_type="INDIVIDUAL", party_type="INDIVIDUAL",
            first_name="Amina", surname="Salim", email="a@example.com", mobile_number="255700000011",
            identification_type="NIN", identification_number="ID-E1", date_of_birth=date(1990, 1, 1),
            is_active=True, status="ACTIVE",
        )
        self.employer = Partner.objects.create(
            partner_number="PT-OLP-E2", partner_type="CORPORATE", party_type="CORPORATE",
            company_name="Zanzibar Advisory", legal_name="Zanzibar Advisory Ltd",
            email="emp@example.com", is_active=True, status="ACTIVE",
        )
        self.quotation = OLQuotation.objects.create(quote_number="Q-ENR-0001")
        self.proposal = make_proposal(self.quotation, partner=self.policyholder)

    def test_employer_cannot_equal_policyholder(self):
        with self.assertRaises(Exception) as ctx:
            enrichment_service.apply_section(
                proposal=self.proposal, section="employer",
                data={"employer_partner": str(self.policyholder.pk), "employment_reference": "REF-1"},
                actor=self.user,
            )
        self.assertIn("employer", str(ctx.exception))

    def test_intermediary_requires_channel(self):
        with self.assertRaises(Exception) as ctx:
            enrichment_service.apply_section(
                proposal=self.proposal, section="intermediary",
                data={"agent_partner": str(self.policyholder.pk)},
                actor=self.user,
            )
        self.assertIn("channel", str(ctx.exception))

    def test_declarations_and_bank_mask(self):
        enrichment_service.apply_section(
            proposal=self.proposal,
            section="declarations",
            data={"declaration_pep_flag": True, "declaration_aml_flag": False, "existing_policies_count": 2, "occupation_risk_note": "Office work", "declarations_free_text": {"source": "Salary"}},
            actor=self.user,
        )
        enrichment_service.apply_section(
            proposal=self.proposal,
            section="bank_details",
            data={"bank_name": "CRDB", "bank_account_name": "Amina Salim", "bank_account_number": "12345678"},
            actor=self.user,
        )
        self.proposal.refresh_from_db()
        self.assertTrue(self.proposal.declaration_pep_flag)
        self.assertEqual(self.proposal.existing_policies_count, 2)
        self.assertEqual(self.proposal.bank_account_number, "12345678")
        self.assertEqual(enrichment_service.mask_account_number("12345678"), "****5678")
        self.assertTrue(AuditLog.objects.filter(action="ENRICH_DECLARATIONS", object_id=str(self.proposal.pk)).exists())
        self.assertTrue(DomainEvent.objects.filter(event_type="ProposalEnriched", aggregate_id=str(self.proposal.pk)).exists())


class BeneficiaryValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="benef_ops", password="Password@12345", email="benef_ops@zic.tz")
        self.quotation = OLQuotation.objects.create(quote_number="Q-BEN-0001")
        self.proposal = make_proposal(self.quotation, proposal_number="OLP-2026-00002")
        self.type = OLBeneficialType.objects.create(code="SPOUSE", name="Spouse", category="BENEFICIARY", effective_from=date(2020, 1, 1), is_active=True)

    def test_replace_two_primaries_at_100(self):
        created = enrichment_service.replace_beneficiaries(
            proposal=self.proposal,
            items=[
                {"person_name": "Ali Sayed", "share_percent": "50.00", "is_primary": True},
                {"person_name": "Sana Ali", "share_percent": "50.00", "is_primary": True},
            ],
            actor=self.user,
        )
        self.assertEqual(len(created), 2)
        self.assertEqual(self.proposal.beneficiaries.count(), 2)

    def test_shares_must_total_100(self):
        enrichment_service.replace_beneficiaries(proposal=self.proposal, items=[{"person_name": "Ali", "share_percent": "100.00", "is_primary": True}], actor=self.user)
        with self.assertRaises(ProposalError) as ctx:
            enrichment_service.replace_beneficiaries(proposal=self.proposal, items=[{"person_name": "Ali", "share_percent": "60.00", "is_primary": True}, {"person_name": "Sana", "share_percent": "39.00", "is_primary": True}], actor=self.user)
        self.assertEqual(ctx.exception.error_code, "PROPOSAL_BENEFICIARY_SHARES_INVALID")
        self.assertTrue(ctx.exception.resolution_steps)

    def test_minor_requires_guardian(self):
        with self.assertRaises(ProposalError) as ctx:
            enrichment_service.replace_beneficiaries(proposal=self.proposal, items=[{"person_name": "Baby Ali", "share_percent": "100.00", "is_primary": True, "is_minor": True}], actor=self.user)
        self.assertEqual(ctx.exception.error_code, "PROPOSAL_BENEFICIARY_GUARDIAN_REQUIRED")

    def test_duplicate_identity_prevented(self):
        enrichment_service.replace_beneficiaries(
            proposal=self.proposal,
            items=[
                {"person_name": "Ali", "identity_type": "NIN", "identity_number": "NIN-9", "share_percent": "50.00", "is_primary": True},
                {"person_name": "Fatma", "identity_type": "NIN", "identity_number": "NIN-8", "share_percent": "50.00", "is_primary": True},
            ],
            actor=self.user,
        )
        with self.assertRaises(ProposalError) as ctx:
            enrichment_service.replace_beneficiaries(
                proposal=self.proposal,
                items=[
                    {"person_name": "Ali", "identity_type": "NIN", "identity_number": "NIN-9", "share_percent": "50.00", "is_primary": True},
                    {"person_name": "Ali Jr", "identity_type": "NIN", "identity_number": "NIN-9", "share_percent": "50.00", "is_primary": True},
                ],
                actor=self.user,
            )
        self.assertEqual(ctx.exception.error_code, "PROPOSAL_DUPLICATE_BENEFICIARY")

    def test_completeness_lists_missing_sections(self):
        state = enrichment_service.missing_sections(self.proposal)
        self.assertIn("beneficiaries", state["missing"])
        self.assertIn("declarations", state["missing"])
        self.assertIn("bank_details", state["required_missing"])
        self.assertIn("employer", state["missing"])
        self.assertFalse(state["complete"])

        enrichment_service.replace_beneficiaries(proposal=self.proposal, items=[{"person_name": "Ali", "share_percent": "100.00", "is_primary": True}], actor=self.user)
        enrichment_service.apply_section(proposal=self.proposal, section="declarations", data={"declaration_pep_flag": False, "declaration_aml_flag": False}, actor=self.user)
        enrichment_service.apply_section(proposal=self.proposal, section="bank_details", data={"bank_name": "CRDB", "bank_account_name": "Ali", "bank_account_number": "1111"}, actor=self.user)
        state = enrichment_service.missing_sections(self.proposal)
        self.assertTrue(state["complete"])
        self.assertNotIn("bank_details", state["missing"])


class EnrichmentEndpointTests(DRFTestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(username="en_adm", password="Password@12345", email="en_adm@zic.tz")
        self.quotation = OLQuotation.objects.create(quote_number="Q-ENR-EP1")
        self.proposal = make_proposal(self.quotation, proposal_number="OLP-2026-00003")
        self.urls = {
            "enrich": f"/api/v1/ol-proposals/proposals/{self.proposal.pk}/enrich/",
            "beneficiaries": f"/api/v1/ol-proposals/proposals/{self.proposal.pk}/beneficiaries/",
            "completeness": f"/api/v1/ol-proposals/proposals/{self.proposal.pk}/completeness/",
            "options_employers": "/api/v1/ol-proposals/proposals/options/employers/",
            "options_types": "/api/v1/ol-proposals/proposals/options/beneficial-types/",
        }
        self.client.force_authenticate(self.superuser)
        OLBeneficialType.objects.create(code="CHILD", name="Child", category="BENEFICIARY", effective_from=date(2020, 1, 1), is_active=True)

    def test_enrich_patch_masks_bank_in_response(self):
        response = self.client.patch(
            self.urls["enrich"],
            {
                "declarations": {"declaration_pep_flag": False, "declaration_aml_flag": False},
                "bank_details": {"bank_name": "NMB", "bank_account_name": "Amina", "bank_account_number": "99445566"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        payload = response.data["data"]
        self.assertEqual(payload["bank_name"], "NMB")
        self.assertEqual(payload["bank_account_number"], "****5566")
        self.assertIn("completeness", payload)
        self.assertIn("beneficiaries", payload["completeness"]["missing"])

    def test_beneficiary_add_returns_created(self):
        response = self.client.post(
            self.urls["beneficiaries"],
            {"person_name": "Farida", "share_percent": "100.00", "is_primary": True},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.proposal.beneficiaries.count(), 1)

    def test_options_endpoints(self):
        employers = self.client.get(self.urls["options_employers"], {"q": ""})
        self.assertEqual(employers.status_code, 200)
        self.assertIn("results", employers.data["data"])
        types = self.client.get(self.urls["options_types"])
        self.assertEqual(types.status_code, 200)
        self.assertGreater(len(types.data["data"]["results"]), 0)