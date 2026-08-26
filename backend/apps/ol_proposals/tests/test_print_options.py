from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APITestCase as DRFTestCase

from apps.ol_commitments.models import OLCommitment
from apps.documents.models import DocumentTemplate
from apps.ol_parameters.models import (
    OLBeneficialType,
    OLCommitmentStatus,
    OLProposalDocumentRequirement,
    OLProposalStatus,
)
from apps.ol_proposals.models import (
    OLProposal,
    OLProposalBeneficiary,
    OLProposalBenefit,
    OLProposalPlanConfig,
    OLProposalRider,
    ProposalDocumentStatus,
)
from apps.ol_quotations.models import OLQuotation, OLQuotationVersion
from apps.ordinary_life.models import OLProduct
from apps.partners.models import Partner

User = get_user_model()


def seed_catalogs():
    call_command("seed_ol_proposal_statuses")
    for code, name, order in (("PENDING", "Pending", 10), ("PARTIALLY_PAID", "Partially paid", 20), ("COMPLETED", "Completed", 30)):
        OLCommitmentStatus.objects.update_or_create(
            code=code, defaults={"name": name, "applies_to": "COMMITMENT", "display_order": order, "is_active": True}
        )
    OLProposalDocumentRequirement.objects.get_or_create(
        code="PROPOSAL_DOC_IDENTITY", defaults={"name": "Identity Document", "document_type": "IDENTITY_DOCUMENT", "mandatory": True, "effective_from": date(2020, 1, 1)}
    )
    OLBeneficialType.objects.get_or_create(code="SPOUSE", defaults={"name": "Spouse", "category": "BENEFICIARY", "effective_from": date(2020, 1, 1)})


def make_partner(number, name, party_type="INDIVIDUAL"):
    return Partner.objects.create(
        partner_number=number,
        partner_type="INDIVIDUAL" if party_type == "INDIVIDUAL" else "CLIENT",
        party_type=party_type,
        first_name=name.split()[0],
        surname=" ".join(name.split()[1:]),
        legal_name=name if party_type == "CORPORATE" else "",
        company_name=name if party_type == "CORPORATE" else "",
        email=f"{name.replace(' ', '.').lower()}@example.com",
        is_active=True,
        status="ACTIVE",
    )


def build_proposal(number="OLP-2026-PR1"):
    from apps.ol_parameters.models import OLRiderSetup
    from apps.ordinary_life.models import OLPlan, OLProductVersion

    product, _ = OLProduct.objects.get_or_create(code="OL_ENDOW", defaults={"name": "Endowment"})
    product_version, _ = OLProductVersion.objects.get_or_create(
        product=product, version_number=1, defaults={"effective_from": date.today() - timedelta(days=30)}
    )
    plan, _ = OLPlan.objects.get_or_create(
        product_version=product_version, code="ENDOW-20",
        defaults={"name": "Twenty Year Endowment", "minimum_sum_assured": Decimal("10000"), "maximum_sum_assured": Decimal("1000000")},
    )
    rider_setup, _ = OLRiderSetup.objects.get_or_create(
        code="WAIVER",
        defaults={
            "name": "Premium Waiver",
            "rider_category": "WAIVER",
            "benefit_type": "WAIVER_PREMIUM",
            "effective_from": date(2020, 1, 1),
        },
    )

    partner = make_partner("PT-PR-0001", "Neema Hussein")
    employer = make_partner("PT-PR-0002", "Vision Traders Ltd", party_type="CORPORATE")
    agent = make_partner("PT-PR-0003", "Agent Joseph")
    quotation = OLQuotation.objects.create(quote_number=f"Q-PR-{number[-4:]}")
    quotation.partner = partner
    quotation.partner_verified = True
    quotation.save()
    version = OLQuotationVersion.objects.create(quotation=quotation, version_number=1, status="FINALIZED")

    proposal = OLProposal(
        quotation=quotation,
        quotation_version=version,
        proposal_number=number,
        status="ENRICHMENT",
        partner=partner,
        partner_name_snapshot="Neema Hussein",
        agent_partner=agent,
        agent_name_snapshot="Agent Joseph",
        intermediary_channel="AGENT",
        employer_partner=employer,
        employer_name_snapshot="Vision Traders Ltd",
        employment_reference="EMP-001",
        payroll_deduction=True,
        currency="TZS",
        expiry_date=date.today() + timedelta(days=30),
        declaration_pep_flag=False,
        declaration_aml_flag=False,
        existing_policies_count=2,
        occupation_risk_note="Low risk office worker.",
        declarations_free_text={"source_of_funds": "Salary"},
        financial_summary_snapshot={"total_premium": "50000.00"},
        prospect_snapshot={
            "identity_type": "NIN",
            "identity_number": "ID-PR-0001",
            "date_of_birth": "1990-01-01",
            "age_at_quote": 35,
            "gender": "FEMALE",
            "address": "Kijitonyama, Dar es Salaam",
        },
    )
    proposal.save()

    config = OLProposalPlanConfig.objects.create(
        proposal=proposal,
        product_version=product_version,
        plan=plan,
        plan_name_snapshot="Twenty Year Endowment",
        sub_product_code="ENDOW",
        base_sum_assured=Decimal("500000.00"),
        term_years=20,
        payment_period_years=20,
        premium_frequency="ANNUAL",
        premium_amount=Decimal("50000.00"),
        is_selected=True,
    )
    OLProposalBeneficiary.objects.create(
        proposal=proposal,
        person_name="Baraka Hussein",
        identity_type="NIN",
        identity_number="ID-BEN-0001",
        share_percent=Decimal("100.0000"),
        is_primary=True,
    )
    OLProposalBenefit.objects.create(
        proposal=proposal, plan_config=config, code="MATURITY", name="Maturity Benefit", basis="FIXED", value=Decimal("500000.00"), is_selected=True
    )
    OLProposalRider.objects.create(
        proposal=proposal, rider=rider_setup, rider_name_snapshot="Premium Waiver", plan_config=config,
        rider_sum_assured=Decimal("50000.00"), benefit_basis="FIXED", benefit_value=Decimal("1000.00"),
        loading=Decimal("0.0000"), premium_amount=Decimal("1000.00"), is_selected=True,
    )
    commitment = OLCommitment.objects.create(
        commitment_number=f"OLC-{number}",
        source_type="PROPOSAL",
        source_object_id=str(proposal.pk),
        source_reference=proposal.proposal_number,
        partner=proposal.partner,
        currency="TZS",
        installment_number=1,
        installment_count=1,
        due_date=date.today() + timedelta(days=7),
        premium_amount=Decimal("50000.00"),
        status="PENDING",
    )
    proposal.first_premium_commitment = commitment
    proposal.save(update_fields=["first_premium_commitment"])
    return proposal


@patch("apps.ol_proposals.services.print_service.ProposalPrintService._render_pdf", return_value=b"%PDF-proposal-printout")
class PrintServiceTests(TestCase):
    def setUp(self):
        seed_catalogs()
        self.user = User.objects.create_user(username="print_ops", password="Password@12345", email="print_ops@zic.tz")
        self.proposal = build_proposal()

    def test_printout_renders_with_all_variable_groups(self, _mock_pdf):
        from apps.ol_proposals.services.print_service import ProposalPrintService

        document = ProposalPrintService.generate(proposal=self.proposal, actor=self.user)
        self.assertEqual(document.document_type, "PROPOSAL_PRINT")
        self.assertEqual(document.status, ProposalDocumentStatus.GENERATED)
        self.assertEqual(document.template.code, "OL_PROPOSAL_PRINT")
        self.assertEqual(document.template_version, 1)

        html = default_storage.open(document.html_reference).read().decode("utf-8")
        for marker in (
            "ORDINARY LIFE PROPOSAL SUMMARY",
            "OLP-2026-PR1",
            "Neema Hussein",
            "Baraka Hussein",
            "Vision Traders Ltd",
            "Agent Joseph",
            "Twenty Year Endowment",
            "Maturity Benefit",
            "Premium Waiver",
            "50000.00",
            "PEP",
            "source_of_funds",
            "Zanzibar Insurance Corporation",
        ):
            self.assertIn(marker, html)
        self.assertIn(str(self.proposal.first_premium_commitment.due_date), html)
        variables = document.metadata["variables"]
        for group in ("company", "proposal", "policyholder", "intermediary", "employer", "plans", "benefits", "riders", "beneficiaries", "premium", "declarations"):
            self.assertIn(group, variables)

    def test_document_stores_template_version_and_source_link(self, _mock_pdf):
        from apps.ol_proposals.services.print_service import ProposalPrintService

        document = ProposalPrintService.generate(proposal=self.proposal, actor=self.user)
        self.proposal.refresh_from_db()
        self.assertEqual(document.proposal, self.proposal)
        self.assertEqual(document.template_version, document.template.version)
        self.assertEqual(document.metadata["source_version_number"], 1)
        self.assertEqual(document.metadata["template_code"], "OL_PROPOSAL_PRINT")
        self.assertTrue(document.file_reference.endswith(".pdf"))
        self.assertTrue(document.html_reference.endswith(".html"))
        self.assertEqual(document.generated_by, self.user)
        self.assertFalse(document.mandatory)


class PrintAndOptionsEndpointTests(DRFTestCase):
    def setUp(self):
        seed_catalogs()
        DocumentTemplate.objects.update_or_create(
            code="PROPOSAL_SUMMARY_UNIFIED",
            version=1,
            defaults={
                "name": "Proposal Summary",
                "document_type": "PROPOSAL_SUMMARY",
                "layout_template_path": "documents/proposal_summary.html",
                "variables_schema": {"proposal": "object", "quote": "object", "prospect": "object", "plans": "array", "financial": "object", "branding": "object"},
                "branding_config_reference": "COMPANY_BRANDING",
                "is_active": True,
            },
        )
        self.superuser = User.objects.create_superuser(username="po_adm", password="Password@12345", email="po_adm@zic.tz")
        self.proposal = build_proposal("OLP-2026-PR2")
        self.client.force_authenticate(self.superuser)
        self.base = f"/api/v1/ol-proposals/proposals/{self.proposal.pk}"

    def test_print_endpoint_generates_and_lists_document(self):
        response = self.client.post(f"{self.base}/print/", format="json")
        self.assertEqual(response.status_code, 201, response.data)
        data = response.data["data"]
        self.assertEqual(data["document_type"], "PROPOSAL_SUMMARY")
        self.assertEqual(data["unified_document_type"], "PROPOSAL_SUMMARY")
        self.assertEqual(data["status"], "GENERATED")
        self.assertEqual(data["template_code"], "PROPOSAL_SUMMARY_UNIFIED")
        self.assertEqual(data["template_version"], 1)
        self.assertTrue(data["preview_url"])
        self.assertTrue(data["signed_download_url"])
        self.assertIn("ticket=", data["signed_download_url"])

        register = self.client.get(f"{self.base}/generated-documents/")
        self.assertEqual(register.status_code, 200)
        register_rows = register.data["data"]["results"]
        self.assertEqual(len(register_rows), 1)
        entry = register_rows[0]
        self.assertEqual(entry["document_type"], "PROPOSAL_SUMMARY")
        self.assertEqual(entry["template_code"], "PROPOSAL_SUMMARY_UNIFIED")
        self.assertEqual(entry["template_version"], 1)
        self.assertTrue(entry["generated_by_display"])
        self.assertIsNotNone(entry["generated_at"])
        self.assertTrue(entry["signed_download_url"])
        self.assertIn("ticket=", entry["signed_download_url"])

    def test_options_statuses_labeled_active_only(self):
        OLProposalStatus.objects.create(
            code="INACTIVE_STATUS", name="Hidden", applies_to="PROPOSAL", display_order=99, is_active=False,
            effective_from=date.today(), allowed_transitions=[],
        )
        response = self.client.get("/api/v1/ol-proposals/proposals/options/statuses/")
        self.assertEqual(response.status_code, 200)
        rows = response.data["data"]["results"]
        self.assertTrue(rows)
        for row in rows:
            self.assertTrue(row["label"])
            self.assertEqual(row["id"], row["value"])
        codes = {row["value"] for row in rows}
        self.assertNotIn("INACTIVE_STATUS", codes)
        self.assertIn("ENRICHMENT", codes)
        self.assertEqual(response.data["data"]["label"], "Proposal status")

    def test_options_document_types_active_only(self):
        OLProposalDocumentRequirement.objects.create(
            code="PROPOSAL_DOC_HIDDEN", name="Hidden Doc", document_type="HIDDEN_DOC", mandatory=False,
            effective_from=date(2020, 1, 1), is_active=False,
        )
        response = self.client.get("/api/v1/ol-proposals/proposals/options/document-types/")
        self.assertEqual(response.status_code, 200)
        rows = response.data["data"]["results"]
        self.assertTrue(rows)
        self.assertIn("Identity Document", {row["label"] for row in rows})
        self.assertNotIn("Hidden Doc", {row["label"] for row in rows})

    def test_options_banks_and_employer_options(self):
        banks = self.client.get("/api/v1/ol-proposals/proposals/options/banks/")
        self.assertEqual(banks.status_code, 200)
        bank_rows = banks.data["data"]["results"]
        self.assertTrue(bank_rows)
        for row in bank_rows:
            self.assertTrue(row["label"])
        self.assertIn("NMB Bank Plc", {row["label"] for row in bank_rows})

        employers = self.client.get("/api/v1/ol-proposals/proposals/options/employers/")
        self.assertEqual(employers.status_code, 200)
        employer_labels = {row["label"] for row in employers.data["data"]["results"]}
        self.assertIn("Vision Traders Ltd", employer_labels)
        self.assertNotIn("Agent Joseph", employer_labels)