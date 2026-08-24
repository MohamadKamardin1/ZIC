from datetime import date

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APITestCase as DRFTestCase

from apps.governance.models import AuditLog
from apps.ol_parameters.models import OLProposalDocumentRequirement
from apps.ol_proposals.errors import ProposalError
from apps.ol_proposals.models import OLProposal, OLProposalDocument, ProposalDocumentStatus
from apps.ol_proposals.services import document_service
from apps.ol_quotations.models import OLQuotation

User = get_user_model()


def make_proposal(number="OLP-2026-DOC1"):
    quotation = OLQuotation.objects.create(quote_number=f"Q-DOC-{number[-4:]}")
    proposal = OLProposal(quotation=quotation, proposal_number=number, status="ENRICHMENT")
    proposal.save()
    return proposal


class DocumentRequirementBehaviorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="doc_ops", password="Password@12345", email="doc_ops@zic.tz")
        call_command("seed_ol_proposal_document_requirements")
        self.proposal = make_proposal()

    def test_mandatory_vs_optional_documents(self):
        required = {row.document_type for row in document_service.applicable_requirements(self.proposal) if row.mandatory}
        self.assertEqual(required, {"IDENTITY_DOCUMENT", "SIGNATURE", "KYC_FORM"})

        # Optional requirement is never "missing".
        OLProposalDocumentRequirement.objects.create(
            code="PROPOSAL_DOC_OPTIONAL_BANK", name="Bank Statement", document_type="BANK_STATEMENT",
            mandatory=False, effective_from=date(2020, 1, 1), is_active=True,
        )
        missing = document_service.missing_mandatory_documents(self.proposal)
        self.assertNotIn("BANK_STATEMENT", missing)
        self.assertIn("IDENTITY_DOCUMENT", missing)

        document_service.upload_document(proposal=self.proposal, document_type="IDENTITY_DOCUMENT", file_reference="/media/id.pdf", actor=self.user)
        missing = document_service.missing_mandatory_documents(self.proposal)
        self.assertNotIn("IDENTITY_DOCUMENT", missing)
        self.assertIn("SIGNATURE", missing)

    def test_missing_documents_raise_structured_error(self):
        with self.assertRaises(ProposalError) as ctx:
            document_service.ensure_documents_ok(self.proposal)
        self.assertEqual(ctx.exception.error_code, "PROPOSAL_MANDATORY_DOCUMENTS_MISSING")
        self.assertTrue(ctx.exception.resolution_steps)

        for doc_type in ("IDENTITY_DOCUMENT", "SIGNATURE", "KYC_FORM"):
            document_service.upload_document(proposal=self.proposal, document_type=doc_type, file_reference=f"/media/{doc_type.lower()}.pdf", actor=self.user)
        self.assertTrue(document_service.ensure_documents_ok(self.proposal))


class DocumentEndpointTests(DRFTestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(username="doc_adm", password="Password@12345", email="doc_adm@zic.tz")
        call_command("seed_ol_proposal_document_requirements")
        self.proposal = make_proposal("OLP-2026-DOC2")
        self.url = f"/api/v1/ol-proposals/proposals/{self.proposal.pk}/documents/"
        self.client.force_authenticate(self.superuser)

    def test_upload_and_list_with_audit(self):
        upload = self.client.post(self.url, {"document_type": "IDENTITY_DOCUMENT", "file_reference": "/media/id.pdf"}, format="json")
        self.assertEqual(upload.status_code, 201, upload.data)
        self.assertEqual(upload.data["data"]["mandatory"], True)
        self.assertEqual(upload.data["data"]["status"], "UPLOADED")

        listing = self.client.get(self.url)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data["data"]["results"]), 1)
        self.assertEqual(listing.data["data"]["mandatory"], 1)

        requirements = listing.data["data"]["requirements"]
        by_type = {row["document_type"]: row for row in requirements}
        self.assertTrue(by_type["IDENTITY_DOCUMENT"]["mandatory"])
        self.assertTrue(by_type["SIGNATURE"]["mandatory"])
        self.assertIn("name", by_type["IDENTITY_DOCUMENT"])

        self.assertTrue(
            AuditLog.objects.filter(action="PROPOSAL_DOCUMENT_UPLOAD", object_id=str(self.proposal.pk)).exists()
        )
        document = OLProposalDocument.objects.get(proposal=self.proposal, document_type="IDENTITY_DOCUMENT")
        self.assertEqual(document.status, ProposalDocumentStatus.UPLOADED)
        self.assertEqual(document.uploaded_by, self.superuser)