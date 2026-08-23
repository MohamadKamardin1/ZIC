from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from apps.governance.models import AuditLog
from apps.ol_proposals.models import (
    OLProposal,
    OLProposalBeneficiary,
    OLProposalDocument,
    OLProposalHealthAnswer,
    OLProposalMember,
    OLProposalPlanConfig,
    ProposalDocumentStatus,
)
from apps.ol_quotations.models import OLQuotation

User = get_user_model()


class OLProposalModelTests(TestCase):
    def setUp(self):
        call_command("seed_ol_proposal_statuses")
        self.user = User.objects.create_user(username="proposal_ops", password="Password@12345", email="proposal_ops@zic.tz")
        self.quotation = OLQuotation.objects.create(quote_number="Q-PROP-0001")
        self.created = self._create()

    def _create(self, **overrides):
        proposal = OLProposal(
            quotation=self.quotation,
            proposal_number=overrides.pop("proposal_number", "OLP-2026-00001"),
            partner_name_snapshot=overrides.pop("partner_name_snapshot", "Zanzibar Trading Co."),
            currency=overrides.pop("currency", "TZS"),
            created_by=self.user,
            **overrides,
        )
        proposal.save()
        return proposal

    def test_default_status_resolves_from_catalog(self):
        self.assertEqual(self.created.status, "DRAFT")
        self.assertEqual(self.created.partner_name_snapshot, "Zanzibar Trading Co.")

    def test_status_validated_against_catalog(self):
        proposal = self._create(proposal_number="OLP-2026-00002", status="NOT_A_STATUS")
        with self.assertRaises(ValidationError):
            proposal.full_clean()

    def test_valid_catalog_status_passes_clean(self):
        proposal = self._create(proposal_number="OLP-2026-00003", status="ENRICHMENT")
        proposal.full_clean()
        self.assertEqual(proposal.status, "ENRICHMENT")

    def test_beneficiary_shares_must_total_100(self):
        OLProposalBeneficiary.objects.create(proposal=self.created, person_name="Alice", share_percent=Decimal("50.00"), is_primary=True)
        OLProposalBeneficiary.objects.create(proposal=self.created, person_name="Bob", share_percent=Decimal("50.00"))
        self.created.full_clean()  # ok

        OLProposalBeneficiary.objects.create(proposal=self.created, person_name="Cara", share_percent=Decimal("10.00"))
        with self.assertRaises(ValidationError):
            self.created.full_clean()

    def test_carried_children_and_documents(self):
        OLProposalPlanConfig.objects.create(
            proposal=self.created, base_sum_assured=Decimal("500000.00"), term_years=20,
            payment_period_years=20, premium_frequency="ANNUAL", premium_amount=Decimal("25000.00"),
        )
        OLProposalMember.objects.create(proposal=self.created, member_type="POLICYHOLDER", first_name="Amina", last_name="Hassan", date_of_birth=date(1990, 1, 1))
        OLProposalDocument.objects.create(proposal=self.created, document_type="ID", mandatory=True, status=ProposalDocumentStatus.UPLOADED, uploaded_by=self.user)
        self.assertEqual(self.created.plan_configs.count(), 1)
        self.assertEqual(self.created.members.count(), 1)
        self.assertEqual(self.created.documents.count(), 1)

    def test_audit_written_on_create(self):
        logs = AuditLog.objects.filter(app_label="ol_proposals", model_name="olproposal", object_id=str(self.created.pk))
        self.assertTrue(logs.exists())
        self.assertEqual(logs.first().user, self.user)

    def test_payment_ready_timestamp_set(self):
        proposal = self._create(proposal_number="OLP-2026-00004", status="PAYMENT_READY", payment_ready=True)
        self.assertTrue(proposal.payment_ready_at is not None)


class OLProposalHealthAnswerTests(TestCase):
    def setUp(self):
        call_command("seed_ol_proposal_statuses")
        self.quotation = OLQuotation.objects.create(quote_number="Q-PROP-0002")
        self.proposal = OLProposal.objects.create(quotation=self.quotation, proposal_number="OLP-2026-00100")

    def test_health_answer_creation_defaults(self):
        from apps.ol_parameters.models import OLHealthQuestion

        question = OLHealthQuestion.objects.create(
            code="SMOKING", name="Smoking habit", question_text="Do you smoke?", category="LIFESTYLE",
            answer_type="BOOLEAN", effective_from=date.today() - timedelta(days=30), is_active=True,
        )
        answer = OLProposalHealthAnswer.objects.create(
            proposal=self.proposal, health_question=question, answer={"value": True}, score=Decimal("2.0000"), triggers_medical=True
        )
        self.assertEqual(self.proposal.health_answers.count(), 1)
        self.assertTrue(answer.triggers_medical)