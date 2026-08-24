"""QA matrix: happy path, error matrix, permission matrix, idempotency, audit evidence, E2E.

Covers Prompt 11 scope: every state-change step, every proposal error code
(structured + teachable), all permission gates, idempotency seams, audit
coverage, and both staff and portal API flows.
"""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APITestCase as DRFTestCase

from apps.common.models import DomainEvent
from apps.governance.models import AuditLog
from apps.ol_commitments.models import OLCommitmentAllocation
from apps.ol_parameters.models import (
    OLCommitmentStatus,
    OLHealthQuestion,
    OLHealthQuestionnaire,
    OLHealthQuestionnaireItem,
)
from apps.ol_proposals.errors import ProposalError
from apps.ol_proposals.models import (
    OLProposal,
    OLProposalBeneficiary,
    OLProposalNotificationLog,
)
from apps.ol_proposals.permissions import ACTIONS, OLProposalPermission, has_ol_proposal_permission
from apps.ol_proposals.services import document_service, enrichment_service, health_service
from apps.ol_proposals.services.audit_consistency import audit_consistency, ensure_audit_consistency
from apps.ol_proposals.services.conversion_service import convert_quotation_to_proposal
from apps.ol_proposals.services.lifecycle_service import (
    cancel_proposal,
    mark_expired,
    transition_proposal,
)
from apps.ol_proposals.services.payment_readiness_service import mark_payment_ready
from apps.ol_proposals.services.policy_conversion_service import convert_proposal_to_policy
from apps.ol_quotations.models import (
    OLQuotation,
    OLQuotationPlanConfiguration,
    OLQuotationVersion,
    QuotationStatus,
)
from apps.ordinary_life.models import OLPlan, OLPolicy, OLProduct, OLProductVersion
from apps.partners.models import Partner, UserPartnerLink
from apps.users.models import UserGroup, UserPermission

User = get_user_model()


def seed_catalogs():
    call_command("seed_ol_proposal_statuses")
    for code, name, order in (("PENDING", "Pending", 10), ("PARTIALLY_PAID", "Partially paid", 20), ("COMPLETED", "Completed", 30)):
        OLCommitmentStatus.objects.update_or_create(
            code=code, defaults={"name": name, "applies_to": "COMMITMENT", "display_order": order, "is_active": True}
        )
    call_command("seed_ol_proposal_document_requirements")


def make_partner(number, name):
    slug = f"{name.replace(' ', '.').lower()}.{uuid4().hex[:8]}"
    return Partner.objects.create(
        partner_number=number,
        partner_type="INDIVIDUAL",
        party_type="INDIVIDUAL",
        first_name=name.split()[0],
        surname=" ".join(name.split()[1:]),
        email=f"{slug}@example.com",
        is_active=True,
        status="ACTIVE",
    )


def _product_plan():
    product, _ = OLProduct.objects.get_or_create(code="OL_ENDOW", defaults={"name": "Endowment"})
    product_version, _ = OLProductVersion.objects.get_or_create(
        product=product, version_number=1, defaults={"effective_from": date.today() - timedelta(days=30)}
    )
    plan, _ = OLPlan.objects.get_or_create(
        product_version=product_version, code="ENDOW-20",
        defaults={"name": "Twenty Year Endowment", "minimum_sum_assured": Decimal("10000"), "maximum_sum_assured": Decimal("1000000")},
    )
    return product_version, plan


def build_finalized_quotation(partner, *, quote_number="Q-QA-0001"):
    product_version, plan = _product_plan()
    quotation = OLQuotation.objects.create(quote_number=quote_number, currency="TZS")
    quotation.partner = partner
    quotation.partner_verified = True
    quotation.current_version_number = 1
    quotation.status = QuotationStatus.FINALIZED
    quotation.save()
    OLQuotationVersion.objects.create(
        quotation=quotation, version_number=1, status=QuotationStatus.FINALIZED, snapshot={}
    )
    OLQuotationPlanConfiguration.objects.create(
        quotation=quotation,
        product_version=product_version,
        plan=plan,
        base_sum_assured=Decimal("500000.00"),
        term_years=20,
        payment_period_years=20,
        premium_frequency="ANNUAL",
        premium_amount=Decimal("50000.00"),
        is_selected=True,
    )
    return quotation, product_version, plan


def seed_non_triggering_health():
    question = OLHealthQuestion.objects.create(
        code="SMOKING", name="Smoking habit", question_text="Do you smoke?", category="LIFESTYLE",
        answer_type="BOOLEAN", effective_from=date.today() - timedelta(days=30), is_active=True,
    )
    questionnaire = OLHealthQuestionnaire.objects.create(
        code="OL_GLOBAL_HEALTH", name="Global health", applies_to_scope="GLOBAL",
        version="1.0", effective_from=date.today() - timedelta(days=30), is_active=True,
    )
    item = OLHealthQuestionnaireItem.objects.create(
        code="ITEM_SMOKING", name="Smoking", questionnaire=questionnaire, health_question=question,
        sequence=1, mandatory=True, trigger_medical_requirement=False, score=Decimal("0.0000"),
    )
    return question, questionnaire, item


def complete_enrichment_and_docs(proposal, user):
    enrichment_service.apply_section(
        proposal=proposal, section="declarations",
        data={"declaration_pep_flag": False, "declaration_aml_flag": False},
        actor=user, suppress_errors=True,
    )
    enrichment_service.apply_section(
        proposal=proposal, section="bank_details",
        data={"bank_name": "NMB", "bank_account_name": "Ready Account", "bank_account_number": "1234567890"},
        actor=user, suppress_errors=True,
    )
    enrichment_service.replace_beneficiaries(
        proposal=proposal,
        items=[{
            "person_name": "Primary Beneficiary", "identity_type": "NIN", "identity_number": "QA-BEN-0001",
            "share_percent": Decimal("100.0000"), "is_primary": True,
        }],
        actor=user,
    )
    for document_type in ("IDENTITY_DOCUMENT", "SIGNATURE", "KYC_FORM"):
        document_service.upload_document(
            proposal=proposal, document_type=document_type, file_reference=f"/media/{document_type.lower()}.pdf", actor=user
        )


def allocate_full_payment(commitment, user, amount=None):
    amount = Decimal(str(amount or commitment.premium_amount))
    OLCommitmentAllocation.objects.create(
        commitment=commitment, receipt_reference=f"QA-RCT-{commitment.commitment_number}",
        amount=amount, payment_mode="CASH", currency=commitment.currency, allocated_by=user,
    )
    commitment.amount_paid = amount
    commitment.status = "COMPLETED"
    commitment.save()


def assert_audit_row(proposal, action, actor, channel):
    row = AuditLog.objects.filter(object_id=str(proposal.pk), action=action, source_channel=channel).latest("created_at")
    assert row.user == actor, f"{action} actor {row.user} != {actor}"
    assert (row.before_state is not None) or (row.after_state is not None), f"{action} lacks state"
    return row


class HappyPathIntegrationTests(TestCase):
    def setUp(self):
        seed_catalogs()
        self.user = User.objects.create_user(username="happy_ops", password="Password@12345", email="happy_ops@zic.tz")
        self.partner = make_partner("PT-QA-0001", "Happy Client")
        self.quotation, self.product_version, self.plan = build_finalized_quotation(self.partner)

    def test_complete_happy_path(self):
        # 1. quotation finalize + partner verify (already FINALIZED + verified)
        self.assertEqual(self.quotation.status, QuotationStatus.FINALIZED)
        self.assertTrue(self.quotation.partner_verified)

        # 2. convert
        result = convert_quotation_to_proposal(quotation=self.quotation, actor=self.user, request=None, source_channel="API")
        self.assertTrue(result.created)
        proposal = result.proposal
        self.assertEqual(proposal.status, "ENRICHMENT")

        # 3/4. enrich + beneficiaries
        complete_enrichment_and_docs(proposal, self.user)

        # 5. health answers (non-triggering)
        question, _, _ = seed_non_triggering_health()
        answer = health_service.record_answers(
            proposal=proposal, answers=[{"health_question": str(question.pk), "answer": {"value": False}}], actor=self.user
        )
        self.assertFalse(answer["triggered"])
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, "ENRICHMENT")

        # 6. payment ready
        readiness = mark_payment_ready(proposal=proposal, actor=self.user, source_channel="API")
        self.assertFalse(readiness["already_ready"])
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, "AWAITING_FIRST_PREMIUM")
        self.assertIsNotNone(proposal.first_premium_commitment)

        # 7. allocate full payment
        allocate_full_payment(proposal.first_premium_commitment, self.user)
        proposal.refresh_from_db()

        # 8. convert to policy
        policy, created = convert_proposal_to_policy(proposal=proposal, actor=self.user, source_channel="API")
        self.assertTrue(created)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, "CONVERTED")
        self.assertEqual(proposal.converted_policy, policy)
        self.assertTrue(policy.policy_number)
        self.assertEqual(policy.proposal.quotation.quotation_number, self.quotation.quote_number)
        self.assertEqual(OLPolicy.objects.count(), 1)

        # audit evidence for every step
        audit_consistency(proposal)
        report = audit_consistency(proposal)
        self.assertTrue(report["consistent"], report["problems"])
        for action, channel in (
            ("CONVERT_QUOTATION_TO_PROPOSAL", "API"),
            ("ENRICH_DECLARATIONS", "API"),
            ("ENRICH_BANK_DETAILS", "API"),
            ("ENRICH_BENEFICIARY_REPLACE", "API"),
            ("PROPOSAL_DOCUMENT_UPLOAD", "API"),
            ("MARK_PAYMENT_READY", "API"),
            ("LINK_FIRST_PREMIUM_COMMITMENT", "API"),
            ("PROPOSAL_TRANSITION", "API"),
            ("CONVERT_TO_POLICY", "API"),
        ):
            row = assert_audit_row(proposal, action, self.user, channel)
            self.assertTrue(row.reason or row.changed_fields)

    def test_policy_conversion_is_idempotent(self):
        proposal = convert_quotation_to_proposal(quotation=self.quotation, actor=self.user, source_channel="API").proposal
        complete_enrichment_and_docs(proposal, self.user)
        mark_payment_ready(proposal=proposal, actor=self.user, source_channel="API")
        proposal.refresh_from_db()
        allocate_full_payment(proposal.first_premium_commitment, self.user)

        policy, created = convert_proposal_to_policy(proposal=proposal, actor=self.user, source_channel="API")
        self.assertTrue(created)
        again, again_created = convert_proposal_to_policy(proposal=proposal, actor=self.user, source_channel="API")
        self.assertFalse(again_created)
        self.assertEqual(again.pk, policy.pk)
        self.assertEqual(
            OLPolicy.objects.filter(proposal__quotation__quotation_number=self.quotation.quote_number).count(), 1
        )
        self.assertEqual(
            OLProposalNotificationLog.objects.filter(proposal=proposal, event_type="ProposalConverted").count(), 1
        )
        self.assertEqual(
            DomainEvent.objects.filter(event_type="ProposalConverted", aggregate_id=str(proposal.pk)).count(), 1
        )


class ErrorMatrixTests(DRFTestCase):
    def setUp(self):
        seed_catalogs()
        self.user = User.objects.create_user(username="err_ops", password="Password@12345", email="err_ops@zic.tz")
        self.partner = make_partner("PT-QA-0002", "Error Partner")
        self.quotation, self.product_version, self.plan = build_finalized_quotation(self.partner)
        self.proposal = convert_quotation_to_proposal(quotation=self.quotation, actor=self.user, source_channel="API").proposal

    def _assert_structured(self, exc, code):
        self.assertEqual(exc.error_code, code)
        self.assertTrue(exc.message)
        self.assertTrue(exc.resolution_steps)

    def test_every_error_code_is_teachable(self):

        # PROPOSAL_PARTNER_NOT_VERIFIED
        blocked_quote, _, _ = build_finalized_quotation(make_partner("PT-QA-0003", "Unverified"), quote_number="Q-QA-0009")
        blocked_quote.partner_verified = False
        blocked_quote.save(update_fields=["partner_verified"])
        with self.assertRaises(ProposalError) as ctx:
            convert_quotation_to_proposal(quotation=blocked_quote, actor=self.user, source_channel="API")
        self._assert_structured(ctx.exception, "PROPOSAL_PARTNER_NOT_VERIFIED")

        # PROPOSAL_BENEFICIARY_SHARES_INVALID
        with self.assertRaises(ProposalError) as ctx:
            enrichment_service.replace_beneficiaries(
                proposal=self.proposal,
                items=[{"person_name": "A", "share_percent": Decimal("50.0000"), "is_primary": True}],
                actor=self.user,
            )
        self._assert_structured(ctx.exception, "PROPOSAL_BENEFICIARY_SHARES_INVALID")

        # PROPOSAL_DUPLICATE_BENEFICIARY
        OLProposalBeneficiary.objects.create(
            proposal=self.proposal, person_name="Dup", identity_type="NIN", identity_number="DUP-1",
            share_percent=Decimal("100.0000"), is_primary=True,
        )
        with self.assertRaises(ProposalError) as ctx:
            enrichment_service.add_beneficiary(
                proposal=self.proposal,
                data={"person_name": "Copy", "identity_type": "NIN", "identity_number": "DUP-1", "share_percent": Decimal("0.0001")},
                actor=self.user,
            )
        self._assert_structured(ctx.exception, "PROPOSAL_DUPLICATE_BENEFICIARY")

        # PROPOSAL_BENEFICIARY_GUARDIAN_REQUIRED
        OLProposalBeneficiary.objects.filter(proposal=self.proposal).delete()
        with self.assertRaises(ProposalError) as ctx:
            enrichment_service.replace_beneficiaries(
                proposal=self.proposal,
                items=[{"person_name": "Minor", "share_percent": Decimal("100.0000"), "is_primary": True, "is_minor": True}],
                actor=self.user,
            )
        self._assert_structured(ctx.exception, "PROPOSAL_BENEFICIARY_GUARDIAN_REQUIRED")

        # PROPOSAL_BENEFICIARY_NOT_FOUND
        with self.assertRaises(ProposalError) as ctx:
            enrichment_service.update_beneficiary(
                proposal=self.proposal, beneficiary_id=uuid4(),
                data={"person_name": "X"}, actor=self.user,
            )
        self._assert_structured(ctx.exception, "PROPOSAL_BENEFICIARY_NOT_FOUND")

        # PROPOSAL_MANDATORY_DOCUMENTS_MISSING
        with self.assertRaises(ProposalError) as ctx:
            document_service.ensure_documents_ok(self.proposal)
        self._assert_structured(ctx.exception, "PROPOSAL_MANDATORY_DOCUMENTS_MISSING")

        # PROPOSAL_UNDERWRITING_PENDING (readiness item)
        self.proposal.medical_required = True
        self.proposal.underwriting_status = "PENDING"
        self.proposal.save(update_fields=["medical_required", "underwriting_status"])
        from apps.ol_proposals.services.payment_readiness_service import evaluate_payment_ready

        item = next(row for row in evaluate_payment_ready(self.proposal)["items"] if row["key"] == "underwriting_cleared_or_not_required")
        self.assertEqual(item["error_code"], "PROPOSAL_UNDERWRITING_PENDING")
        self.assertTrue(item["resolution_steps"])
        self.assertTrue(item["deep_link"].startswith("/proposals/"))

        # PROPOSAL_NOT_PAYMENT_READY (with deep links)
        with self.assertRaises(ProposalError) as ctx:
            mark_payment_ready(proposal=self.proposal, actor=self.user, source_channel="API")
        self._assert_structured(ctx.exception, "PROPOSAL_NOT_PAYMENT_READY")
        self.assertEqual(ctx.exception.status_code, 409)
        failed = ctx.exception.details["checklist"]
        self.assertTrue(failed)
        for item in failed:
            self.assertTrue(item["error_code"])
            self.assertTrue(item["resolution_steps"])
            self.assertTrue(item["deep_link"].startswith("/proposals/"))

        # PROPOSAL_EXPIRED (underwriting decision on expired proposal)
        self.proposal.medical_required = False
        self.proposal.underwriting_status = "PENDING"
        self.proposal.expiry_date = date.today() - timedelta(days=1)
        self.proposal.save(update_fields=["medical_required", "underwriting_status", "expiry_date"])
        from apps.ol_proposals.services.underwriting_service import decide

        with self.assertRaises(ProposalError) as ctx:
            decide(proposal=self.proposal, decision="clear", actor=self.user, source_channel="API")
        self._assert_structured(ctx.exception, "PROPOSAL_EXPIRED")

        # PROPOSAL_INVALID_TRANSITION (lists allowed)
        self.proposal.expiry_date = date.today() + timedelta(days=30)
        self.proposal.status = "ENRICHMENT"
        self.proposal.save(update_fields=["expiry_date", "status"])
        with self.assertRaises(ProposalError) as ctx:
            transition_proposal(proposal=self.proposal, to_status="CONVERTED", actor=self.user, source_channel="API")
        self._assert_structured(ctx.exception, "PROPOSAL_INVALID_TRANSITION")
        self.assertTrue(any("Allowed next states" in step for step in ctx.exception.resolution_steps))

        # PROPOSAL_FIRST_PREMIUM_NOT_POSTED
        from apps.ol_proposals.services.first_premium_service import (
            ensure_first_premium_posted,
            link_first_premium_commitment,
        )

        self.proposal.financial_summary_snapshot = {"total_premium": "50000.00"}
        self.proposal.save(update_fields=["financial_summary_snapshot"])
        commitment, _ = link_first_premium_commitment(proposal=self.proposal, actor=self.user, source_channel="API")
        with self.assertRaises(ProposalError) as ctx:
            ensure_first_premium_posted(self.proposal)
        self._assert_structured(ctx.exception, "PROPOSAL_FIRST_PREMIUM_NOT_POSTED")

        # PROPOSAL_ALREADY_CONVERTED
        self.proposal.status = "CONVERTED"
        self.proposal.converted_policy = None
        self.proposal.save(update_fields=["status", "converted_policy"])
        with self.assertRaises(ProposalError) as ctx:
            convert_proposal_to_policy(proposal=self.proposal, actor=self.user, source_channel="API")
        self._assert_structured(ctx.exception, "PROPOSAL_ALREADY_CONVERTED")

        # PROPOSAL_EXPIRED via conversion guard quotation (already covered by decide) + PARAMETER_MISSING
        fresh = self._fresh()
        with self.assertRaises(ProposalError) as ctx:
            health_service.record_answers(
                proposal=fresh, answers=[{"health_question": "00000000-0000-0000-0000-000000000000", "answer": {"value": True}}],
                actor=self.user,
            )
        self._assert_structured(ctx.exception, "PARAMETER_MISSING")

        # PROPOSAL_ERROR via print on cancelled
        cancel_proposal(proposal=fresh, actor=self.user, reason="QA matrix cancellation", source_channel="API")
        with self.assertRaises(ProposalError) as ctx:
            import apps.ol_proposals.services.print_service as ps

            ps.ProposalPrintService.generate(proposal=fresh, actor=self.user)
        self._assert_structured(ctx.exception, "PROPOSAL_ERROR")

        # PROPOSAL_AUDIT_INCONSISTENT
        never = self._expired_without_audit()
        with self.assertRaises(ProposalError) as ctx:
            ensure_audit_consistency(never)
        self._assert_structured(ctx.exception, "PROPOSAL_AUDIT_INCONSISTENT")

        # VALIDATION_ERROR
        with self.assertRaises(ProposalError) as ctx:
            cancel_proposal(proposal=self._fresh(), actor=self.user, reason="", source_channel="API")
        self.assertEqual(ctx.exception.error_code, "VALIDATION_ERROR")

        # PROPOSAL_ERROR (non-finalized quotation; NOT_FOUND is endpoint-level, see below)
        with self.assertRaises(ProposalError) as ctx:
            convert_quotation_to_proposal(
                quotation=OLQuotation.objects.create(quote_number="Q-QA-0999"), actor=self.user, source_channel="API"
            )
        self._assert_structured(ctx.exception, "PROPOSAL_ERROR")

    def _fresh(self):
        self._fresh_seq = getattr(self, "_fresh_seq", 0) + 1
        seed_catalogs()
        quotation, _, _ = build_finalized_quotation(
            make_partner(f"PT-QA-0004-{self._fresh_seq}", "Fresh Client"), quote_number=f"Q-QA-0008-{self._fresh_seq}"
        )
        return convert_quotation_to_proposal(quotation=quotation, actor=self.user, source_channel="API").proposal

    def _expired_without_audit(self):
        proposal = self._fresh()
        proposal.status = "EXPIRED"
        proposal.save(update_fields=["status"])
        return proposal

    def test_error_not_found_via_endpoint(self):
        self.client.force_authenticate(User.objects.create_superuser(username="err_adm", password="Password@12345", email="err_adm@zic.tz"))
        response = self.client.get(f"/api/v1/ol-proposals/proposals/{uuid4()}/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error_code"], "PROPOSAL_NOT_FOUND")
        self.assertTrue(response.data["resolution_steps"])
        self.assertEqual(response.data["doc_ref"], "docs/OL_PROPOSALS_DESIGN.md")


class PermissionMatrixTests(DRFTestCase):
    def setUp(self):
        seed_catalogs()
        call_command("seed_ol_proposal_permissions")
        self.partner = make_partner("PT-QA-0005", "Permission Partner")
        self.viewer = User.objects.create_user(username="perm_view", password="Password@12345", email="perm_view@zic.tz")
        self.grant(self.viewer, "view")
        partner_quote, _, _ = build_finalized_quotation(self.partner, quote_number="Q-QA-0007")
        self.quotation = partner_quote
        self.proposal = convert_quotation_to_proposal(quotation=self.quotation, actor=None, source_channel="API").proposal

    def grant(self, user, action):
        permission, _ = UserPermission.objects.get_or_create(
            codename=f"ol_proposals.{action}",
            defaults={"name": f"OL Proposals {action}", "module": "ol_proposals", "action": action.upper()},
        )
        group, _ = UserGroup.objects.get_or_create(code=f"QA_{action.upper()}", defaults={"name": f"QA {action}"})
        group.permissions.add(permission)
        user.groups.add(group)

    def test_action_mapping_and_has_permission(self):
        privileged = User.objects.create_user(username="perm_all", password="Password@12345", email="perm_all@zic.tz")
        for action in ACTIONS:
            self.grant(privileged, action)
        for action in ACTIONS:
            self.assertTrue(has_ol_proposal_permission(privileged, action), action)
            expected_code = f"ol_proposals.{action}"
            self.assertEqual(OLProposalPermission.code_for(action), expected_code, action)
        self.assertEqual(OLProposalPermission.code_for("reactivate"), "ol_proposals.enrich")
        self.assertTrue(has_ol_proposal_permission(self.viewer, "view"))
        for action in ACTIONS:
            if action != "view":
                self.assertFalse(has_ol_proposal_permission(self.viewer, action), action)

    def test_view_only_user_blocked_from_every_action(self):
        self.client.force_authenticate(self.viewer)
        blocked_routes = [
            ("post", f"/api/v1/ol/proposals/from-quotation/{self.quotation.pk}/"),
            ("patch", f"/api/v1/ol-proposals/proposals/{self.proposal.pk}/enrich/"),
            ("post", f"/api/v1/ol-proposals/proposals/{self.proposal.pk}/documents/"),
            ("post", f"/api/v1/ol-proposals/proposals/{self.proposal.pk}/health-answers/"),
            ("post", f"/api/v1/ol-proposals/proposals/{self.proposal.pk}/underwriting-decision/"),
            ("post", f"/api/v1/ol-proposals/proposals/{self.proposal.pk}/mark-payment-ready/"),
            ("post", f"/api/v1/ol-proposals/proposals/{self.proposal.pk}/cancel/"),
            ("post", f"/api/v1/ol-proposals/proposals/{self.proposal.pk}/convert/"),
            ("post", f"/api/v1/ol-proposals/proposals/{self.proposal.pk}/print/"),
        ]
        for method, route in blocked_routes:
            with self.subTest(route=route):
                response = getattr(self.client, method)(route, {}, format="json")
                self.assertEqual(response.status_code, 403, response.data)

        view_ok = self.client.get("/api/v1/ol-proposals/proposals/")
        self.assertEqual(view_ok.status_code, 200)

    def test_granted_action_unblocks_endpoint(self):
        self.grant(self.viewer, "enrich")
        self.client.force_authenticate(self.viewer)
        response = self.client.patch(
            f"/api/v1/ol-proposals/proposals/{self.proposal.pk}/enrich/",
            {"declarations": {"declaration_pep_flag": False, "declaration_aml_flag": False}},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)


class IdempotencyTests(TestCase):
    def setUp(self):
        seed_catalogs()
        self.user = User.objects.create_user(username="idem_ops", password="Password@12345", email="idem_ops@zic.tz")
        self.partner = make_partner("PT-QA-0006", "Idempotent Partner")
        self.quotation, _, _ = build_finalized_quotation(self.partner, quote_number="Q-QA-0006")

    def test_conversion_idempotent(self):
        first = convert_quotation_to_proposal(quotation=self.quotation, actor=self.user, source_channel="API")
        second = convert_quotation_to_proposal(quotation=self.quotation, actor=self.user, source_channel="API")
        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertTrue(second.duplicate)
        self.assertEqual(first.proposal.pk, second.proposal.pk)
        self.assertEqual(OLProposal.objects.filter(quotation=self.quotation).count(), 1)

    def test_payment_ready_idempotent(self):
        proposal = convert_quotation_to_proposal(quotation=self.quotation, actor=self.user, source_channel="API").proposal
        complete_enrichment_and_docs(proposal, self.user)
        first = mark_payment_ready(proposal=proposal, actor=self.user, source_channel="API")
        second = mark_payment_ready(proposal=proposal, actor=self.user, source_channel="API")
        self.assertFalse(first["already_ready"])
        self.assertTrue(second["already_ready"])
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, "AWAITING_FIRST_PREMIUM")

    def test_expiry_batch_idempotent(self):
        proposal = convert_quotation_to_proposal(quotation=self.quotation, actor=self.user, source_channel="API").proposal
        proposal.expiry_date = date.today() - timedelta(days=1)
        proposal.save(update_fields=["expiry_date"])
        from apps.common.models import DomainEvent

        call_command("expire_proposals")
        call_command("expire_proposals")
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, "EXPIRED")
        self.assertEqual(
            DomainEvent.objects.filter(event_type="ProposalExpired", aggregate_id=str(proposal.pk)).count(), 1
        )


class AuditEvidenceTests(TestCase):
    def setUp(self):
        seed_catalogs()
        self.user = User.objects.create_user(username="aud_ops", password="Password@12345", email="aud_ops@zic.tz")
        self.partner = make_partner("PT-QA-0007", "Audit Partner")
        self.quotation, _, _ = build_finalized_quotation(self.partner, quote_number="Q-QA-0005")

    def test_every_state_change_has_audit(self):
        proposal = convert_quotation_to_proposal(quotation=self.quotation, actor=self.user, source_channel="API").proposal
        complete_enrichment_and_docs(proposal, self.user)
        mark_payment_ready(proposal=proposal, actor=self.user, source_channel="API")
        proposal.refresh_from_db()
        allocate_full_payment(proposal.first_premium_commitment, self.user)
        convert_proposal_to_policy(proposal=proposal, actor=self.user, source_channel="API")

        proposal.refresh_from_db()
        report = audit_consistency(proposal)
        self.assertTrue(report["consistent"], report["problems"])

        for action in (
            "CONVERT_QUOTATION_TO_PROPOSAL",
            "ENRICH_DECLARATIONS",
            "ENRICH_BANK_DETAILS",
            "ENRICH_BENEFICIARY_REPLACE",
            "MARK_PAYMENT_READY",
            "LINK_FIRST_PREMIUM_COMMITMENT",
            "CONVERT_TO_POLICY",
        ):
            rows = AuditLog.objects.filter(object_id=str(proposal.pk), action=action)
            self.assertTrue(rows.exists(), action)
            self.assertEqual(rows.first().user, self.user)
            self.assertEqual(rows.first().source_channel, "API")
            self.assertTrue(rows.first().reason or rows.first().before_state is not None)

        expiry = convert_quotation_to_proposal(
            quotation=build_finalized_quotation(make_partner("PT-QA-0008", "Expiry Audit"), quote_number="Q-QA-0004")[0],
            actor=self.user, source_channel="SYSTEM",
        ).proposal
        mark_expired(proposal=expiry, actor=None, reason="QA expiry", source_channel="BATCH")
        log = AuditLog.objects.filter(object_id=str(expiry.pk), action="PROPOSAL_EXPIRE", source_channel="BATCH").latest("created_at")
        self.assertEqual(log.source_channel, "BATCH")
        self.assertTrue(log.after_state.get("status") == "EXPIRED")


class E2EFlowTests(DRFTestCase):
    def setUp(self):
        seed_catalogs()
        self.staff = User.objects.create_superuser(username="e2e_staff", password="Password@12345", email="e2e_staff@zic.tz")
        self.partner = make_partner("PT-QA-0009", "E2E Partner")
        self.quotation, _, _ = build_finalized_quotation(self.partner, quote_number="Q-QA-0003")
        self.client.force_authenticate(self.staff)

    def test_staff_e2e_flow_through_api(self):
        # convert
        converted = self.client.post(f"/api/v1/ol/proposals/from-quotation/{self.quotation.pk}/", {}, format="json")
        self.assertEqual(converted.status_code, 201, converted.data)
        proposal_id = converted.data["data"]["id"]
        base = f"/api/v1/ol-proposals/proposals/{proposal_id}"

        # enrich
        enriched = self.client.patch(
            f"{base}/enrich/",
            {
                "declarations": {"declaration_pep_flag": False, "declaration_aml_flag": False},
                "bank_details": {"bank_name": "NMB", "bank_account_name": "E2E", "bank_account_number": "1111"},
            },
            format="json",
        )
        self.assertEqual(enriched.status_code, 200, enriched.data)

        # beneficiaries
        beneficiaries = self.client.post(
            f"{base}/beneficiaries/",
            {"person_name": "E2E Beneficiary", "identity_type": "NIN", "identity_number": "E2E-BEN",
             "share_percent": "100.0000", "is_primary": True},
            format="json",
        )
        self.assertEqual(beneficiaries.status_code, 201, beneficiaries.data)

        # documents
        for document_type in ("IDENTITY_DOCUMENT", "SIGNATURE", "KYC_FORM"):
            upload = self.client.post(
                f"{base}/documents/", {"document_type": document_type, "file_reference": f"/media/{document_type.lower()}.pdf"}, format="json"
            )
            self.assertEqual(upload.status_code, 201, upload.data)

        # health answers (non-triggering)
        question, _, _ = seed_non_triggering_health()
        answers = self.client.post(
            f"{base}/health-answers/",
            {"answers": [{"health_question": str(question.pk), "answer": {"value": False}}]},
            format="json",
        )
        self.assertEqual(answers.status_code, 200, answers.data)

        # payment ready
        ready = self.client.post(f"{base}/mark-payment-ready/", format="json")
        self.assertEqual(ready.status_code, 200, ready.data)
        self.assertEqual(ready.data["data"]["status"], "AWAITING_FIRST_PREMIUM")

        # allocate full payment against the linked commitment
        proposal_row = OLProposal.objects.get(pk=proposal_id)
        commitment = proposal_row.first_premium_commitment
        self.assertIsNotNone(commitment)
        OLCommitmentAllocation.objects.create(
            commitment=commitment, receipt_reference="E2E-RCT-1", amount=commitment.premium_amount,
            payment_mode="CASH", currency=commitment.currency, allocated_by=self.staff,
        )
        commitment.amount_paid = commitment.premium_amount
        commitment.status = "COMPLETED"
        commitment.save()

        # convert to policy via API (BR-03 enforced)
        converted_policy = self.client.post(f"{base}/convert/", format="json")
        self.assertEqual(converted_policy.status_code, 201, converted_policy.data)
        self.assertEqual(converted_policy.data["data"]["status"], "CONVERTED")
        self.assertTrue(converted_policy.data["data"]["policy_number"])

    def test_portal_read_only_and_cannot_convert(self):
        portal = User.objects.create_user(username="e2e_portal", password="Password@12345", email="e2e_portal@zic.tz", user_type="PORTAL_USER")
        UserPartnerLink.objects.create(user=portal, partner=self.partner, link_status="ACTIVE", is_primary=True, valid_from=date.today())

        staff_convert = self.client.post(f"/api/v1/ol/proposals/from-quotation/{self.quotation.pk}/", {}, format="json")
        proposal_id = staff_convert.data["data"]["id"]

        self.client.force_authenticate(portal)
        listing = self.client.get("/api/v1/ol-proposals/proposals/portal/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["data"]["count"], 1)
        detail = self.client.get(f"/api/v1/ol-proposals/proposals/portal/{proposal_id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn("allowed_actions", detail.data["data"])

        denied = self.client.post(f"/api/v1/ol-proposals/proposals/{proposal_id}/convert/", format="json")
        self.assertEqual(denied.status_code, 403, denied.data)