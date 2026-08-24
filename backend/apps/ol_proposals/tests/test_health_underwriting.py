from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase as DRFTestCase

from apps.common.models import DomainEvent
from apps.ol_parameters.models import OLHealthQuestion, OLHealthQuestionnaire, OLHealthQuestionnaireItem
from apps.ol_proposals.errors import ProposalError
from apps.ol_proposals.models import OLProposal
from apps.ol_proposals.services import health_service, underwriting_service
from apps.ol_quotations.models import OLQuotation

User = get_user_model()


def make_proposal(number="OLP-2026-UW1"):
    quotation = OLQuotation.objects.create(quote_number=f"Q-UW-{number[-4:]}")
    proposal = OLProposal(quotation=quotation, proposal_number=number, status="ENRICHMENT")
    proposal.save()
    return proposal


def seed_questionnaire(trigger=True):
    question = OLHealthQuestion.objects.create(
        code="SMOKING", name="Smoking habit", question_text="Do you smoke?",
        category="LIFESTYLE", answer_type="BOOLEAN", effective_from=date.today() - timedelta(days=30), is_active=True,
    )
    questionnaire = OLHealthQuestionnaire.objects.create(
        code="OL_GLOBAL_HEALTH", name="Global health questionnaire", applies_to_scope="GLOBAL",
        version="1.0", effective_from=date.today() - timedelta(days=30), is_active=True,
    )
    item = OLHealthQuestionnaireItem.objects.create(
        code="ITEM_SMOKING", name="Smoking item",
        questionnaire=questionnaire, health_question=question, sequence=1, mandatory=True,
        trigger_medical_requirement=trigger, score="2.0000",
    )
    return question, questionnaire, item


class HealthAnswerTriggerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="health_ops", password="Password@12345", email="health_ops@zic.tz")
        self.proposal = make_proposal()
        self.question, _, _ = seed_questionnaire(trigger=True)

    def test_trigger_moves_status_and_emits_event(self):
        result = health_service.record_answers(
            proposal=self.proposal,
            answers=[{"health_question": str(self.question.pk), "answer": {"value": True}}],
            actor=self.user,
        )
        self.assertTrue(result["triggered"])
        self.proposal.refresh_from_db()
        self.assertTrue(self.proposal.medical_required)
        self.assertEqual(self.proposal.status, "PENDING_UNDERWRITING")
        self.assertTrue(
            DomainEvent.objects.filter(event_type="MedicalRequirementRaised", aggregate_id=str(self.proposal.pk)).exists()
        )


class UnderwritingDecisionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="uw_ops", password="Password@12345", email="uw_ops@zic.tz")
        self.proposal = make_proposal()

    def test_clear_returns_to_enrichment(self):
        proposal = underwriting_service.decide(proposal=self.proposal, decision="clear", actor=self.user, source_channel="API")
        proposal.refresh_from_db()
        self.assertEqual(proposal.underwriting_status, "CLEARED")
        self.assertEqual(proposal.status, "ENRICHMENT")
        self.assertFalse(proposal.medical_required)

    def test_decline_blocks_progression(self):
        proposal = underwriting_service.decide(proposal=self.proposal, decision="decline", actor=self.user, reason="High-risk occupation")
        proposal.refresh_from_db()
        self.assertEqual(proposal.underwriting_status, "DECLINED")
        self.assertEqual(proposal.status, "CANCELLED")
        with self.assertRaises(ProposalError) as ctx:
            underwriting_service.decide(proposal=proposal, decision="clear", actor=self.user)
        self.assertEqual(ctx.exception.error_code, "PROPOSAL_INVALID_TRANSITION")

    def test_decline_requires_reason(self):
        with self.assertRaises(ProposalError) as ctx:
            underwriting_service.decide(proposal=self.proposal, decision="decline", actor=self.user)
        self.assertEqual(ctx.exception.error_code, "VALIDATION_ERROR")


class HealthUnderwritingEndpointTests(DRFTestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(username="uw_adm", password="Password@12345", email="uw_adm@zic.tz")
        self.proposal = make_proposal("OLP-2026-UW2")
        self.question, _, _ = seed_questionnaire(trigger=True)
        self.client.force_authenticate(self.superuser)
        self.urls = {
            "questions": f"/api/v1/ol-proposals/proposals/{self.proposal.pk}/health-questions/",
            "answers": f"/api/v1/ol-proposals/proposals/{self.proposal.pk}/health-answers/",
            "decision": f"/api/v1/ol-proposals/proposals/{self.proposal.pk}/underwriting-decision/",
        }

    def test_questions_served(self):
        response = self.client.get(self.urls["questions"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["questionnaire"], "OL_GLOBAL_HEALTH")
        self.assertEqual(len(response.data["data"]["results"]), 1)
        self.assertEqual(response.data["data"]["results"][0]["question_code"], "SMOKING")

    def test_answers_then_clear_endpoint(self):
        answers = self.client.post(self.urls["answers"], {"answers": [{"health_question": str(self.question.pk), "answer": {"value": True}}]}, format="json")
        self.assertEqual(answers.status_code, 200, answers.data)
        self.assertTrue(answers.data["data"]["health_result"]["triggered"])
        self.assertEqual(answers.data["data"]["status"], "PENDING_UNDERWRITING")

        clear = self.client.post(self.urls["decision"], {"decision": "clear"}, format="json")
        self.assertEqual(clear.status_code, 200, clear.data)
        self.assertEqual(clear.data["data"]["status"], "ENRICHMENT")
        self.assertEqual(clear.data["data"]["underwriting_status"], "CLEARED")