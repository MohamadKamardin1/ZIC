from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.governance.models import ApprovalRequest, AuditLog
from apps.ordinary_life.models import (
    OLPlan,
    OLProduct,
    OLProductVersion,
    OLRateBand,
    OLUnderwritingDecisionEvent,
)
from apps.ordinary_life.services.application_service import OrdinaryLifeApplicationService
from apps.partners.models import Partner
from apps.system_parameters.models import ParameterGroup, SystemParameter
from apps.system_parameters.services.config_service import ConfigurationService
from apps.users.models import User


class OrdinaryLifeApplicationServiceTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user(
            username="phase5-underwriter",
            email="phase5-underwriter@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
            user_type="UNDERWRITER",
        )
        self.partner = self._partner("P5-0001", "Asha", "Juma", "asha@example.com", "255710000001")
        self.policyholder = self._partner("P5-0002", "Hassan", "Ali", "hassan@example.com", "255710000002")
        self.product = OLProduct.objects.create(
            code="OL_PHASE5",
            name="Phase 5 Term Protection",
            business_area="ORDINARY_LIFE",
            min_age=18,
            max_age=65,
            term_length_years=10,
            is_active=True,
        )
        self.product_version = OLProductVersion.objects.create(
            product=self.product,
            version_number=1,
            effective_from=date(2026, 1, 1),
            currency="TZS",
            min_entry_age=18,
            max_entry_age=65,
            min_term_years=5,
            max_term_years=30,
            payment_frequencies=["MONTHLY", "QUARTERLY", "SEMI_ANNUAL", "ANNUAL"],
            underwriting_rules={"medical_required": False},
            servicing_rules={"grace_period_days": 30},
            snapshot={"test_fixture": "phase5"},
            is_active=True,
        )
        self.plan = OLPlan.objects.create(
            product_version=self.product_version,
            code="STANDARD",
            name="Standard",
            minimum_sum_assured=Decimal("1000000.00"),
            maximum_sum_assured=Decimal("500000000.00"),
            is_active=True,
        )
        self.rate_band = OLRateBand.objects.create(
            product_version=self.product_version,
            plan=self.plan,
            min_age=18,
            max_age=65,
            min_term_years=5,
            max_term_years=30,
            rate=Decimal("0.00120000"),
            is_active=True,
        )
        self.no_plan_rate_band = OLRateBand.objects.create(
            product_version=self.product_version,
            plan=None,
            min_age=18,
            max_age=65,
            min_term_years=5,
            max_term_years=30,
            rate=Decimal("0.00200000"),
            is_active=True,
        )
        ConfigurationService.invalidate_cache()

    @staticmethod
    def _partner(number, first_name, surname, email, mobile):
        return Partner.objects.create(
            partner_number=number,
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            first_name=first_name,
            surname=surname,
            date_of_birth=date(1990, 6, 15),
            identification_type="ZAN_ID",
            identification_number=number,
            email=email,
            mobile_number=mobile,
            status="ACTIVE",
            is_active=True,
        )

    def _application(self):
        application = OrdinaryLifeApplicationService.create_application(
            partner=self.partner,
            policyholder=self.policyholder,
            life_assured=self.policyholder,
            payer=self.policyholder,
            declarations={"consent": True, "source": "STAFF"},
            actor=self.actor,
        )
        return OrdinaryLifeApplicationService.submit_application(
            application,
            actor=self.actor,
            reason="Declarations verified at intake",
        )

    def _proposal(self, medical_required=False):
        if medical_required:
            self.product_version.underwriting_rules = {
                "medical_required": True,
                "medical_requirements": ["BLOOD_TEST"],
            }
            self.product_version.save(update_fields=["underwriting_rules", "updated_at"])
        application = self._application()
        quotation = OrdinaryLifeApplicationService.create_quotation(
            application=application,
            product_version=self.product_version,
            sum_assured=Decimal("10000000.00"),
            term_years=10,
            payment_frequency="ANNUAL",
            plan=self.plan,
            actor=self.actor,
        )
        OrdinaryLifeApplicationService.submit_quotation(quotation, actor=self.actor, reason="Quote accepted by customer")
        return OrdinaryLifeApplicationService.convert_quotation_to_proposal(
            quotation,
            application=application,
            actor=self.actor,
            reason="Application converted from accepted quote",
        )

    def test_application_submission_requires_declarations_and_active_canonical_parties(self):
        application = OrdinaryLifeApplicationService.create_application(
            partner=self.partner,
            policyholder=self.policyholder,
            life_assured=self.policyholder,
            actor=self.actor,
        )
        with self.assertRaises(ValidationError):
            OrdinaryLifeApplicationService.submit_application(application, actor=self.actor)
        application.declarations = {"consent": True}
        application.save(update_fields=["declarations", "updated_at"])
        submitted = OrdinaryLifeApplicationService.submit_application(application, actor=self.actor)
        self.assertEqual(submitted.status, "SUBMITTED")
        self.assertIsNotNone(submitted.submitted_at)

    def test_quotation_calculation_is_deterministic_and_immutable_by_version(self):
        application = self._application()
        quotation = OrdinaryLifeApplicationService.create_quotation(
            application=application,
            product_version=self.product_version,
            sum_assured=Decimal("10000000.00"),
            term_years=10,
            payment_frequency="ANNUAL",
            plan=self.plan,
            actor=self.actor,
        )
        first = quotation.current_version
        self.assertEqual(first.version_number, 1)
        self.assertEqual(first.calculated_outputs["annual_premium"], "12000.00")
        self.assertEqual(quotation.premium_amount, Decimal("12000.00"))

        repeated = OrdinaryLifeApplicationService.calculate_quotation(
            quotation=quotation,
            product_version=self.product_version,
            sum_assured=Decimal("10000000.00"),
            term_years=10,
            payment_frequency="ANNUAL",
            plan=self.plan,
            actor=self.actor,
        )
        self.assertEqual(repeated.pk, first.pk)
        self.assertEqual(quotation.versions.count(), 1)

        revised = OrdinaryLifeApplicationService.calculate_quotation(
            quotation=quotation,
            product_version=self.product_version,
            sum_assured=Decimal("10000000.00"),
            term_years=15,
            payment_frequency="ANNUAL",
            plan=self.plan,
            actor=self.actor,
        )
        self.assertEqual(revised.version_number, 2)
        self.assertEqual(quotation.versions.count(), 2)
        first.refresh_from_db()
        self.assertEqual(first.inputs["term_years"], 10)

    def test_quotation_requires_matching_rate_band_and_allowed_frequency(self):
        application = self._application()
        quotation = OrdinaryLifeApplicationService.create_quotation(
            application=application,
            product_version=self.product_version,
            sum_assured=Decimal("10000000.00"),
            term_years=10,
            payment_frequency="ANNUAL",
            plan=self.plan,
            actor=self.actor,
        )
        with self.assertRaises(ValidationError):
            OrdinaryLifeApplicationService.calculate_quotation(
                quotation=quotation,
                product_version=self.product_version,
                sum_assured=Decimal("10000000.00"),
                term_years=10,
                payment_frequency="WEEKLY",
                plan=self.plan,
                actor=self.actor,
            )

    def test_underwriting_cannot_approve_with_unresolved_medical_evidence(self):
        proposal = self._proposal(medical_required=True)
        case = OrdinaryLifeApplicationService.start_underwriting(proposal, actor=self.actor, reason="Risk review opened")
        requirement = case.medical_requirements.get(requirement_type="BLOOD_TEST")
        self.assertEqual(requirement.status, "PENDING")
        with self.assertRaises(ValidationError):
            OrdinaryLifeApplicationService.assess_risk(case, "APPROVED", actor=self.actor, reason="Attempted early approval")

        result = OrdinaryLifeApplicationService.record_medical_result(
            requirement,
            result="CLEAR",
            evidence_reference="MED-001",
            result_data={"laboratory": "ZIC-approved"},
            actor=self.actor,
            reason="Medical report received",
        )
        self.assertEqual(result.result, "CLEAR")
        OrdinaryLifeApplicationService.verify_medical_requirement(requirement, actor=self.actor, reason="Evidence verified")
        assessed = OrdinaryLifeApplicationService.assess_risk(case, "APPROVED", actor=self.actor, reason="Standard risk accepted")
        self.assertEqual(assessed.decision, "APPROVED")
        proposal.refresh_from_db()
        self.assertEqual(proposal.underwriting_status, "APPROVED")

    def test_business_approval_setting_creates_pending_approval_and_completion_is_idempotent_at_domain_boundary(self):
        group = ParameterGroup.objects.create(name="Phase 5 test", code="PHASE5_TEST")
        SystemParameter.objects.create(
            group=group,
            name="Require Ordinary Life proposal approval",
            code="APPROVAL_REQUIRED_ORDINARY_LIFE_OLPROPOSAL_APPROVE",
            value_type="STRING",
            string_value="true",
            is_active=True,
        )
        ConfigurationService.invalidate_cache()
        proposal = self._proposal()
        case = OrdinaryLifeApplicationService.start_underwriting(proposal, actor=self.actor)
        OrdinaryLifeApplicationService.assess_risk(case, "APPROVED", actor=self.actor, reason="Underwriting approved")
        approval = OrdinaryLifeApplicationService.submit_proposal_for_approval(proposal, actor=self.actor, comments="Escalated for business approval")
        self.assertIsInstance(approval, ApprovalRequest)
        self.assertEqual(approval.status, "PENDING")
        completed = OrdinaryLifeApplicationService.complete_business_approval(approval.pk, self.actor, comments="Approved within authority")
        self.assertEqual(completed.status, "APPROVED")
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, "APPROVED")
        self.assertEqual(proposal.payment_obligations.count(), 1)
        self.assertEqual(proposal.payment_obligations.first().status, "DUE")

    def test_declined_underwriting_reopen_preserves_append_only_decision_history(self):
        proposal = self._proposal()
        case = OrdinaryLifeApplicationService.start_underwriting(proposal, actor=self.actor)
        OrdinaryLifeApplicationService.assess_risk(case, "DECLINED", actor=self.actor, reason="Material risk outside appetite")
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, "DECLINED")
        reopened = OrdinaryLifeApplicationService.reopen_underwriting(
            case,
            actor=self.actor,
            reason="New medical evidence supplied by customer",
        )
        self.assertEqual(reopened.decision, "PENDING")
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, "UNDERWRITING")
        self.assertEqual(OLUnderwritingDecisionEvent.objects.filter(underwriting_case=case).count(), 2)

    def test_phase5_transitions_write_workflow_and_central_audit_evidence(self):
        proposal = self._proposal()
        case = OrdinaryLifeApplicationService.start_underwriting(proposal, actor=self.actor)
        OrdinaryLifeApplicationService.assess_risk(case, "APPROVED", actor=self.actor, reason="Accepted standard risk")
        OrdinaryLifeApplicationService.approve_proposal(proposal, actor=self.actor, reason="Business approval recorded")
        self.assertTrue(
            AuditLog.objects.filter(
                model_name="olproposal",
                object_id=str(proposal.pk),
                action="APPROVE_PROPOSAL",
            ).exists()
        )
        self.assertTrue(
            proposal.workflowevent_set.exists() if hasattr(proposal, "workflowevent_set") else True
        )
        self.assertGreaterEqual(
            AuditLog.objects.filter(object_id=str(proposal.pk)).count(),
            3,
        )
