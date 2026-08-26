from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.common.models import DomainEvent
from apps.governance.models import AuditLog
from apps.ol_commitments.models import CommitmentSourceType, OLCommitment
from apps.ol_parameters.models import (
    OLGracePeriod,
    OLLoanInterestControl,
    OLLoanSystemSetup,
    OLMaturityClaimSetup,
    OLPlanType,
    OLProduct,
    OLReinstatementWindow,
    OLSurrenderSetup,
)
from apps.ol_policies.events import (
    POLICY_ISSUED,
    POLICY_LAPSED,
    POLICY_LOAN_DISBURSED,
    POLICY_LOAN_REPAID,
    POLICY_LOAN_REQUESTED,
    POLICY_MATURITY_CLAIM_CREATED,
    POLICY_MATURITY_PAID,
    POLICY_REINSTATED,
    POLICY_SURRENDER_REQUESTED,
)
from apps.ol_policies.models import (
    LoanStatus,
    MaturityClaim,
    Policy,
    PolicyAuditLog,
    PolicyStatus,
    SurrenderRequest,
    SurrenderStatus,
)
from apps.ol_policies.permissions import ACTIONS, has_ol_policy_permission
from apps.ol_policies.services.endorsement_service import create_policy_endorsement
from apps.ol_policies.services.issuance_service import issue_policy_from_proposal
from apps.ol_policies.services.lifecycle_service import reinstate_policy
from apps.ol_policies.services.maturity_service import create_maturity_claim, pay_maturity_claim
from apps.ol_policies.services.termination_service import request_policy_surrender
from apps.ol_proposals.models import OLProposal, OLProposalMember, OLProposalPlanConfig
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner


class PolicyLifecycleMatrixTestCase(APITestCase):
    """Cross-path regression coverage for the issued-policy bounded context.

    Each test starts from the same minimal, issuance-ready proposal. The
    matrix intentionally calls the real services and management commands so
    retries, audit rows, events, and immutable contract snapshots are tested
    at the same seams used by the API and batch workers.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="policy-matrix-admin",
            email="policy-matrix-admin@example.com",
            password="Strong-policy-matrix-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-MATRIX-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Asha Suleiman",
            email="asha.matrix@example.com",
            mobile_number="+255711900001",
            phone="+255711900001",
        )
        self.agent = Partner.objects.create(
            partner_number="ZIC-MATRIX-A-0001",
            partner_type="AGENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Hassan Agent",
            email="hassan.matrix@example.com",
            mobile_number="+255711900002",
            phone="+255711900002",
        )
        self.quotation = OLQuotation.objects.create(
            quote_number="QT-MATRIX-0001",
            quote_name="Policy lifecycle matrix quote",
            quote_date=date.today() - timedelta(days=400),
            partner=self.partner,
            currency="TZS",
        )
        self.proposal = OLProposal.objects.create(
            quotation=self.quotation,
            proposal_number="PROP-MATRIX-0001",
            status="AWAITING_FIRST_PREMIUM",
            partner=self.partner,
            agent_partner=self.agent,
            currency="TZS",
            prospect_snapshot={"name": "Asha Suleiman", "identity_number": "NIDA-MATRIX-1"},
            financial_summary_snapshot={"total_sum_assured": "50000000.00", "total_premium": "250000.00"},
        )
        self.plan_config = OLProposalPlanConfig.objects.create(
            proposal=self.proposal,
            plan_name_snapshot="ZIC Matrix Term Plan",
            sub_product_code="OL_TERM_MATRIX",
            section_number=1,
            base_sum_assured=Decimal("50000000.00"),
            term_years=10,
            payment_period_years=10,
            premium_frequency="ANNUALLY",
            quote_basis="SUM_ASSURED",
            estimated_maturity_value=Decimal("50000000.00"),
            premium_factor="NONE",
            premium_amount=Decimal("250000.00"),
            is_selected=True,
        )
        OLProposalMember.objects.create(
            proposal=self.proposal,
            member_type="POLICYHOLDER",
            first_name="Asha",
            last_name="Suleiman",
            date_of_birth=date(1990, 4, 12),
            gender="FEMALE",
            relationship="PRINCIPAL",
            member_sum_assured=Decimal("50000000.00"),
        )
        commitment = OLCommitment.objects.create(
            commitment_number="COM-MATRIX-FIRST-0001",
            source_type=CommitmentSourceType.PROPOSAL,
            source_content_type=ContentType.objects.get_for_model(OLProposal),
            source_object_id=str(self.proposal.pk),
            source_reference=self.proposal.proposal_number,
            partner=self.partner,
            partner_name_snapshot=self.partner.legal_name,
            currency="TZS",
            premium_frequency="ANNUALLY",
            due_date=date.today() - timedelta(days=400),
            premium_amount=Decimal("250000.00"),
            amount_paid=Decimal("250000.00"),
            balance=Decimal("0.00"),
            status="COMPLETED",
        )
        self.proposal.first_premium_commitment = commitment
        self.proposal.save(update_fields=["first_premium_commitment"])
        self.client.force_authenticate(self.user)

    def issue_policy(self):
        policy, created = issue_policy_from_proposal(self.proposal.pk, actor=self.user, source_channel="API")
        self.assertTrue(created)
        return policy

    def add_policy_commitment(self, policy, *, status="COMPLETED", balance=Decimal("0.00"), due_date=None):
        return OLCommitment.objects.create(
            commitment_number=f"COM-MATRIX-POL-{OLCommitment.objects.count() + 1:04d}",
            source_type=CommitmentSourceType.POLICY,
            source_content_type=ContentType.objects.get_for_model(Policy),
            source_object_id=str(policy.pk),
            source_reference=policy.policy_number,
            partner=policy.partner,
            partner_name_snapshot=policy.partner.legal_name,
            currency=policy.currency,
            premium_frequency=policy.premium_frequency,
            due_date=due_date or date.today(),
            premium_amount=Decimal(str(policy.premium_amount)),
            amount_paid=Decimal(str(policy.premium_amount)) - balance,
            balance=balance,
            status=status,
        )

    def test_happy_path_issuance_endorsement_and_maturity_has_audited_transitions(self):
        policy = self.issue_policy()
        before_contract = dict(policy.contract_snapshot)

        endorsement, adjustment = create_policy_endorsement(
            policy.pk,
            endorsement_type="PREMIUM_CHANGE",
            changes={"new_premium": "275000.00"},
            description="Annual premium indexed after approved servicing review.",
            actor=self.user,
            source_channel="API",
        )
        self.assertEqual(endorsement.status, "APPLIED")
        self.assertIsNotNone(adjustment)

        policy.refresh_from_db()
        snapshot_after_endorsement = dict(policy.contract_snapshot)
        snapshot_after_endorsement["maturity_value"] = "50000000.00"
        snapshot_after_endorsement["plans"] = [{"product_code": "OL_TERM_MATRIX"}]
        policy.contract_snapshot = snapshot_after_endorsement
        policy.maturity_date = date.today() - timedelta(days=1)
        policy.save(update_fields=["contract_snapshot", "maturity_date"])
        OLMaturityClaimSetup.objects.create(
            code="MATRIX-MATURITY-SETUP",
            name="Matrix maturity setup",
            effective_from=date.today() - timedelta(days=3650),
            auto_create_maturity_claim=True,
            days_before_maturity_to_initiate=0,
            default_payout_method="BANK_TRANSFER",
            require_documents=False,
            require_approval=False,
            maturity_claim_status_to_create="REPORTED",
            is_active=True,
        )
        claim, created = create_maturity_claim(policy, as_of=date.today(), actor=self.user, source_channel="BATCH")
        self.assertTrue(created)
        self.assertEqual(claim.status, "APPROVED")
        paid = pay_maturity_claim(claim.pk, payment_reference="MATRIX-MAT-0001", actor=self.user)
        self.assertEqual(paid.status, "PAID")
        policy.refresh_from_db()
        self.assertEqual(policy.status, PolicyStatus.MATURED)

        audited_events = set(PolicyAuditLog.objects.filter(policy=policy).values_list("event_type", flat=True))
        self.assertTrue({POLICY_ISSUED, "PolicyEndorsed", POLICY_MATURITY_CLAIM_CREATED, POLICY_MATURITY_PAID} <= audited_events)
        for row in PolicyAuditLog.objects.filter(policy=policy):
            self.assertTrue(row.reason)
            self.assertIsNotNone(row.before_snapshot)
            self.assertIsNotNone(row.after_snapshot)
            self.assertTrue(row.source_channel)
        self.assertNotEqual(before_contract.get("premium_amount"), str(policy.premium_amount))
        self.assertEqual(
            DomainEvent.objects.filter(aggregate_id=str(policy.pk)).count(),
            len(set(DomainEvent.objects.filter(aggregate_id=str(policy.pk)).values_list("event_type", flat=True))),
        )

    def test_lapse_reinstatement_path_and_batch_retry_are_idempotent(self):
        policy = self.issue_policy()
        overdue = self.add_policy_commitment(
            policy,
            status="PENDING",
            balance=Decimal("100000.00"),
            due_date=date.today() - timedelta(days=30),
        )
        OLGracePeriod.objects.create(
            code="MATRIX-GRACE-ANNUAL",
            name="Matrix annual grace",
            effective_from=date.today() - timedelta(days=365),
            premium_frequency="ANNUALLY",
            grace_days=5,
            warning_days=7,
            pre_lapse_days=8,
            lapse_days=10,
            is_active=True,
        )
        first_output = StringIO()
        call_command("process_policy_lapses", "--as-of", date.today().isoformat(), stdout=first_output)
        second_output = StringIO()
        call_command("process_policy_lapses", "--as-of", date.today().isoformat(), stdout=second_output)
        policy.refresh_from_db()
        self.assertEqual(policy.status, PolicyStatus.LAPSED)
        self.assertIn("changed=1", first_output.getvalue())
        self.assertIn("changed=0", second_output.getvalue())
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_LAPSED, aggregate_id=str(policy.pk)).count(), 1)

        OLReinstatementWindow.objects.create(
            code="MATRIX-REINSTATE-30",
            name="Matrix reinstatement window",
            effective_from=date.today() - timedelta(days=365),
            days_after_lapse=30,
            require_medical_underwriting=False,
            require_outstanding_premium_payment=True,
            interest_rate=Decimal("0"),
            penalty_rate=Decimal("0"),
            is_active=True,
        )
        reinstated = reinstate_policy(
            policy.pk,
            payment_amount=Decimal("100000.00"),
            actor=self.user,
            as_of=date.today(),
            source_channel="API",
        )
        self.assertEqual(reinstated.status, PolicyStatus.ACTIVE)
        overdue.refresh_from_db()
        self.assertEqual(overdue.status, "COMPLETED")
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_REINSTATED, aggregate_id=str(policy.pk)).count(), 1)
        self.assertTrue(PolicyAuditLog.objects.filter(policy=policy, event_type=POLICY_LAPSED).exists())
        self.assertTrue(PolicyAuditLog.objects.filter(policy=policy, event_type=POLICY_REINSTATED).exists())

    def test_surrender_path_creates_payout_handoff_and_is_idempotent(self):
        policy = self.issue_policy()
        policy.contract_snapshot = {**policy.contract_snapshot, "surrender_value_rate": "0.80"}
        policy.save(update_fields=["contract_snapshot"])
        self.add_policy_commitment(policy)
        OLSurrenderSetup.objects.create(
            code="MATRIX-SURRENDER-SETUP",
            name="Matrix surrender setup",
            effective_from=date.today() - timedelta(days=365),
            minimum_premiums_paid=1,
            minimum_policy_months=1,
            minimum_premium_paid_ratio=Decimal("100"),
            surrender_charge_type="PERCENTAGE",
            surrender_charge_value=Decimal("10"),
            partial_surrender_allowed=False,
            require_approval=False,
            is_active=True,
        )
        surrender, created = request_policy_surrender(policy.pk, actor=self.user, as_of=date.today(), source_channel="API")
        self.assertTrue(created)
        self.assertEqual(surrender.status, SurrenderStatus.PENDING_PAYMENT)
        self.assertTrue(surrender.payment_requisition_id)
        policy.refresh_from_db()
        self.assertEqual(policy.status, PolicyStatus.SURRENDER_PENDING)
        retry, retry_created = request_policy_surrender(policy.pk, actor=self.user, as_of=date.today(), source_channel="API")
        self.assertFalse(retry_created)
        self.assertEqual(retry.pk, surrender.pk)
        self.assertEqual(SurrenderRequest.objects.filter(policy=policy).count(), 1)
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_SURRENDER_REQUESTED, aggregate_id=str(policy.pk)).count(), 1)
        self.assertTrue(PolicyAuditLog.objects.filter(policy=policy, event_type=POLICY_SURRENDER_REQUESTED).exists())

    def test_loan_disbursement_repayment_path_records_finance_audit_and_events(self):
        policy = self.issue_policy()
        plan_type = OLPlanType.objects.create(code="MATRIX-PLAN-TYPE", name="Matrix plan type", is_active=True)
        product = OLProduct.objects.create(
            code="OL_MATRIX_FINANCE",
            name="Matrix finance product",
            plan_type=plan_type,
            effective_from=date.today() - timedelta(days=365),
            premium_frequencies=["ANNUALLY"],
            allow_loans=True,
            is_active=True,
        )
        policy.contract_snapshot = {
            **policy.contract_snapshot,
            "cash_value": "1000000.00",
            "allow_loans": True,
            "plans": [{"product_id": str(product.pk), "product_code": product.code}],
        }
        policy.save(update_fields=["contract_snapshot"])
        OLLoanSystemSetup.objects.create(
            code="MATRIX-LOAN-SETUP",
            name="Matrix loan setup",
            product=product,
            effective_from=date.today() - timedelta(days=365),
            allow_policy_loans=True,
            loan_basis="CASH_VALUE",
            max_loan_percentage_of_cash_value=Decimal("50"),
            min_loan_amount=Decimal("10000"),
            max_loan_amount=Decimal("400000"),
            loan_currency="TZS",
            repayment_options=["LUMP_SUM", "INSTALLMENTS"],
            require_approval=True,
            is_active=True,
        )
        OLLoanInterestControl.objects.create(
            code="MATRIX-LOAN-INTEREST",
            name="Matrix loan interest",
            product=product,
            effective_from=date.today() - timedelta(days=365),
            interest_rate=Decimal("0"),
            compounding_frequency="ANNUAL",
            interest_calculation_basis="ACTUAL_365",
            grace_period_days=0,
            penalty_interest_rate=Decimal("0"),
            capitalize_interest=True,
            is_active=True,
        )
        request_date = date.today() - timedelta(days=1)
        requested = self.client.post(
            f"/api/v1/ol/policies/{policy.pk}/loans/",
            {"amount": "100000.00", "as_of": request_date.isoformat(), "reason": "Matrix test loan."},
            format="json",
        )
        self.assertEqual(requested.status_code, 201, requested.data)
        loan_id = requested.data["data"]["id"]
        self.assertEqual(
            DomainEvent.objects.filter(event_type=POLICY_LOAN_REQUESTED, aggregate_id=str(policy.pk)).count(), 1
        )
        approved = self.client.post(f"/api/v1/ol/policies/loans/{loan_id}/approve/", {"as_of": request_date.isoformat()}, format="json")
        self.assertEqual(approved.status_code, 200, approved.data)
        disbursed = self.client.post(f"/api/v1/ol/policies/loans/{loan_id}/disburse/", {"as_of": request_date.isoformat()}, format="json")
        self.assertEqual(disbursed.status_code, 200, disbursed.data)
        repaid = self.client.post(
            f"/api/v1/ol/policies/loans/{loan_id}/repay/",
            {"amount": "100000.00", "payment_date": date.today().isoformat()},
            format="json",
        )
        self.assertEqual(repaid.status_code, 200, repaid.data)
        self.assertEqual(repaid.data["data"]["status"], LoanStatus.REPAID)
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_LOAN_DISBURSED, aggregate_id=str(policy.pk)).count(), 1)
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_LOAN_REPAID, aggregate_id=str(policy.pk)).count(), 1)
        self.assertTrue(PolicyAuditLog.objects.filter(policy=policy, event_type="PolicyLoanDisbursed").exists())
        self.assertTrue(PolicyAuditLog.objects.filter(policy=policy, event_type="PolicyLoanRepaid").exists())

    def test_maturity_command_retry_creates_one_claim_and_one_transition(self):
        policy = self.issue_policy()
        policy.contract_snapshot = {**policy.contract_snapshot, "maturity_value": "50000000.00"}
        policy.maturity_date = date.today() - timedelta(days=1)
        policy.save(update_fields=["contract_snapshot", "maturity_date"])
        OLMaturityClaimSetup.objects.create(
            code="MATRIX-MATURITY-BATCH",
            name="Matrix batch maturity",
            effective_from=date.today() - timedelta(days=3650),
            auto_create_maturity_claim=True,
            days_before_maturity_to_initiate=0,
            default_payout_method="BANK_TRANSFER",
            require_documents=True,
            require_approval=True,
            maturity_claim_status_to_create="REPORTED",
            is_active=True,
        )
        first = StringIO()
        second = StringIO()
        call_command("process_policy_maturity", "--as-of", date.today().isoformat(), stdout=first)
        call_command("process_policy_maturity", "--as-of", date.today().isoformat(), stdout=second)
        self.assertIn("created=1", first.getvalue())
        self.assertIn("created=0", second.getvalue())
        self.assertEqual(MaturityClaim.objects.filter(policy=policy).count(), 1)
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_MATURITY_CLAIM_CREATED, aggregate_id=str(policy.pk)).count(), 1)
        self.assertEqual(PolicyAuditLog.objects.filter(policy=policy, event_type="PolicyMaturityClaimCreated").count(), 1)

    def test_permission_matrix_blocks_unentitled_user_and_allows_superuser(self):
        limited = get_user_model().objects.create_user(
            username="policy-matrix-viewer",
            email="policy-matrix-viewer@example.com",
            password="Strong-policy-viewer-password-123!",
        )
        for action in ACTIONS:
            self.assertFalse(has_ol_policy_permission(limited, action), action)
            self.assertTrue(has_ol_policy_permission(self.user, action), action)

        policy = self.issue_policy()
        self.client.force_authenticate(limited)
        read_response = self.client.get(f"/api/v1/ol/policies/{policy.pk}/")
        self.assertEqual(read_response.status_code, 403, read_response.data)
        issue_response = self.client.post(
            "/api/v1/ol/policies/issue/",
            {"proposal_id": str(self.proposal.pk)},
            format="json",
        )
        self.assertEqual(issue_response.status_code, 403, issue_response.data)

    def test_issued_snapshot_remains_immutable_when_upstream_proposal_changes(self):
        policy = self.issue_policy()
        original_snapshot = policy.contract_snapshot
        self.plan_config.plan_name_snapshot = "Changed upstream plan name"
        self.plan_config.base_sum_assured = Decimal("99999999.00")
        self.plan_config.save(update_fields=["plan_name_snapshot", "base_sum_assured"])
        self.proposal.financial_summary_snapshot = {"total_sum_assured": "99999999.00"}
        self.proposal.save(update_fields=["financial_summary_snapshot"])
        policy.refresh_from_db()
        self.assertEqual(policy.contract_snapshot, original_snapshot)
        self.assertEqual(policy.sum_assured, Decimal("50000000.00"))
        self.assertTrue(PolicyAuditLog.objects.filter(policy=policy, event_type=POLICY_ISSUED).exists())

        audit_rows = AuditLog.objects.filter(entity_id=policy.pk)
        self.assertTrue(audit_rows.exists())
        self.assertTrue(any(row.before_state is not None or row.after_state is not None for row in audit_rows))
