from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APITestCase as DRFTestCase

from apps.common.models import DomainEvent
from apps.governance.models import AuditLog
from apps.ol_proposals.errors import ProposalError
from apps.ol_proposals.models import OLProposal, OLProposalBeneficiary
from apps.ol_proposals.services import document_service
from apps.ol_proposals.services.payment_readiness_service import (
    CHECKLIST_ITEMS,
    evaluate_payment_ready,
    mark_payment_ready,
)
from apps.ol_quotations.models import OLQuotation, OLQuotationVersion
from apps.partners.models import Partner

User = get_user_model()


def make_ready_proposal(number="OLP-2026-PR1"):
    partner = Partner.objects.create(
        partner_number=f"PT-PR-{number[-4:]}",
        partner_type="INDIVIDUAL",
        party_type="INDIVIDUAL",
        first_name="Farida",
        surname="Mwangi",
        email="farida.pr@example.com",
        is_active=True,
        status="ACTIVE",
    )
    quotation = OLQuotation.objects.create(quote_number=f"Q-PR-{number[-4:]}", currency="TZS")
    quotation.partner = partner
    quotation.partner_verified = True
    quotation.current_version_number = 1
    quotation.save()
    version = OLQuotationVersion.objects.create(quotation=quotation, version_number=1, status="FINALIZED")

    proposal = OLProposal(
        quotation=quotation,
        quotation_version=version,
        proposal_number=number,
        status="ENRICHMENT",
        partner=partner,
        partner_name_snapshot=partner.legal_name or str(partner),
        currency="TZS",
        expiry_date=date.today() + timedelta(days=30),
        declaration_pep_flag=False,
        declaration_aml_flag=False,
        bank_name="NMB",
        bank_account_name="Farida Mwangi",
        bank_account_number="1234567890",
    )
    proposal.save()
    OLProposalBeneficiary.objects.create(
        proposal=proposal,
        person_name="Farida Mwangi",
        identity_type="NIN",
        identity_number="PR-BEN-0001",
        share_percent=Decimal("100.0000"),
        is_primary=True,
    )
    return {"proposal": proposal, "quotation": quotation, "version": version, "partner": partner}


def upload_mandatory_documents(proposal, user):
    call_command("seed_ol_proposal_document_requirements")
    for document_type in ("IDENTITY_DOCUMENT", "SIGNATURE", "KYC_FORM"):
        document_service.upload_document(
            proposal=proposal, document_type=document_type, file_reference=f"/media/{document_type.lower()}.pdf", actor=user
        )


class PaymentReadinessServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="pr_ops", password="Password@12345", email="pr_ops@zic.tz")
        fixture = make_ready_proposal("OLP-2026-PR1")
        self.proposal = fixture["proposal"]
        self.quotation = fixture["quotation"]
        upload_mandatory_documents(self.proposal, self.user)

    def test_ready_proposal_passes_every_checklist_item(self):
        result = evaluate_payment_ready(self.proposal)
        self.assertTrue(result["passed"])
        self.assertEqual(len(result["items"]), len(CHECKLIST_ITEMS))
        for item in result["items"]:
            self.assertTrue(item["passed"], item["key"])
            self.assertEqual(item["error_code"], "")

    def test_each_failing_item_is_teachable_with_deep_link(self):
        cases = {
            "partner_verified": "PROPOSAL_PARTNER_NOT_VERIFIED",
            "enrichment_complete": "PROPOSAL_ENRICHMENT_INCOMPLETE",
            "beneficiaries_valid": "PROPOSAL_BENEFICIARY_SHARES_INVALID",
            "mandatory_documents_complete": "PROPOSAL_MANDATORY_DOCUMENTS_MISSING",
            "underwriting_cleared_or_not_required": "PROPOSAL_UNDERWRITING_PENDING",
            "not_expired": "PROPOSAL_EXPIRED",
            "quotation_version_current": "PROPOSAL_QUOTATION_VERSION_STALE",
        }
        breakers = {
            "partner_verified": lambda: setattr(self.quotation, "partner_verified", False) or self.quotation.save(),
            "enrichment_complete": lambda: setattr(self.proposal, "bank_account_number", "") or self.proposal.save(update_fields=["bank_account_number"]),
            "beneficiaries_valid": lambda: self.proposal.beneficiaries.all().delete(),
            "mandatory_documents_complete": lambda: self.proposal.documents.filter(document_type="SIGNATURE").delete(),
            "underwriting_cleared_or_not_required": lambda: (
                setattr(self.proposal, "medical_required", True)
                or setattr(self.proposal, "underwriting_status", "PENDING")
            ) or self.proposal.save(update_fields=["medical_required", "underwriting_status"]),
            "not_expired": lambda: setattr(self.proposal, "expiry_date", date.today() - timedelta(days=1)) or self.proposal.save(update_fields=["expiry_date"]),
            "quotation_version_current": lambda: setattr(self.quotation, "current_version_number", 2) or self.quotation.save(update_fields=["current_version_number"]),
        }
        for key, expected_code in cases.items():
            with self.subTest(key=key):
                breakers[key]()
                self.proposal.refresh_from_db()
                result = evaluate_payment_ready(self.proposal)
                item = next(row for row in result["items"] if row["key"] == key)
                self.assertFalse(item["passed"])
                self.assertEqual(item["error_code"], expected_code)
                self.assertTrue(item["message"])
                self.assertTrue(item["resolution_steps"])
                self.assertTrue(item["deep_link"].startswith("/proposals/"))
                with self.assertRaises(ProposalError) as ctx:
                    mark_payment_ready(proposal=self.proposal, actor=self.user, source_channel="API")
                self.assertEqual(ctx.exception.error_code, "PROPOSAL_NOT_PAYMENT_READY")
                self.assertEqual(ctx.exception.status_code, 409)
                failed = [row["key"] for row in ctx.exception.details["checklist"]]
                self.assertIn(key, failed)
                self.proposal.refresh_from_db()
                self.assertEqual(self.proposal.status, "ENRICHMENT")

    def test_success_emits_event_exactly_once_per_transition(self):
        result = mark_payment_ready(proposal=self.proposal, actor=self.user, source_channel="API")
        self.assertFalse(result["already_ready"])
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, "AWAITING_FIRST_PREMIUM")
        self.assertTrue(self.proposal.payment_ready)
        self.assertIsNotNone(self.proposal.payment_ready_at)
        events = DomainEvent.objects.filter(event_type="ProposalPaymentReady", aggregate_id=str(self.proposal.pk))
        self.assertEqual(events.count(), 1)

        replay = mark_payment_ready(proposal=self.proposal, actor=self.user, source_channel="API")
        self.assertTrue(replay["already_ready"])
        self.assertEqual(events.count(), 1)

    def test_audit_snapshot_stored_with_checklist(self):
        mark_payment_ready(proposal=self.proposal, actor=self.user, source_channel="API")
        audit = AuditLog.objects.filter(action="MARK_PAYMENT_READY", object_id=str(self.proposal.pk)).latest("created_at")
        self.assertIn("checklist", audit.after_state)
        self.assertTrue(audit.after_state["checklist"]["passed"])
        self.assertEqual(audit.after_state["status"], "AWAITING_FIRST_PREMIUM")


class PaymentReadinessEndpointTests(DRFTestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(username="pr_adm", password="Password@12345", email="pr_adm@zic.tz")
        fixture = make_ready_proposal("OLP-2026-PR2")
        self.proposal = fixture["proposal"]
        upload_mandatory_documents(self.proposal, self.superuser)
        self.client.force_authenticate(self.superuser)
        self.base = f"/api/v1/ol-proposals/proposals/{self.proposal.pk}"

    def test_checklist_endpoint_matches_service_result(self):
        self.proposal.refresh_from_db()
        response = self.client.get(f"{self.base}/payment-readiness/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"], evaluate_payment_ready(self.proposal))

    def test_mark_payment_ready_success_endpoint(self):
        response = self.client.post(f"{self.base}/mark-payment-ready/", format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["data"]["status"], "AWAITING_FIRST_PREMIUM")
        self.assertTrue(response.data["data"]["payment_readiness"]["passed"])

    def test_mark_payment_ready_conflict_returns_teachable_409(self):
        self.proposal.documents.filter(document_type="KYC_FORM").delete()
        self.proposal.refresh_from_db()
        response = self.client.post(f"{self.base}/mark-payment-ready/", format="json")
        self.assertEqual(response.status_code, 409, response.data)
        self.assertEqual(response.data["error_code"], "PROPOSAL_NOT_PAYMENT_READY")
        failed = response.data["error"]["details"]["checklist"]
        codes = {item["error_code"] for item in failed}
        self.assertIn("PROPOSAL_MANDATORY_DOCUMENTS_MISSING", codes)
        failing = next(item for item in failed if item["error_code"] == "PROPOSAL_MANDATORY_DOCUMENTS_MISSING")
        self.assertTrue(failing["message"])
        self.assertTrue(failing["resolution_steps"])
        self.assertTrue(failing["deep_link"].startswith("/proposals/"))