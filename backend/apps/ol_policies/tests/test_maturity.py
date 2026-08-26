from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.common.models import DomainEvent
from apps.ol_parameters.models import OLMaturityClaimSetup
from apps.ol_policies.events import POLICY_MATURITY_CLAIM_APPROVED, POLICY_MATURITY_CLAIM_CREATED, POLICY_MATURITY_PAID
from apps.ol_policies.models import LoanStatus, MaturityClaim, MaturityClaimStatus, Policy, PolicyLoan, PolicyStatus
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner


class PolicyMaturityTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="maturity-admin",
            email="maturity-admin@example.com",
            password="Strong-maturity-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-MAT-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Zawadi Juma",
            email="zawadi.maturity@example.com",
            mobile_number="+255711700001",
            phone="+255711700001",
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-MAT-0001",
            quote_name="Maturity quote",
            quote_date=date.today() - timedelta(days=4000),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-MAT-0001",
            status="CONVERTED",
            partner=self.partner,
            currency="TZS",
            prospect_snapshot={},
            financial_summary_snapshot={},
        )
        self.policy = Policy.objects.create(
            proposal_ref=proposal,
            partner=self.partner,
            product_plan_ref="OL_MATURITY_PRODUCT",
            currency="TZS",
            sum_assured=Decimal("500000.00"),
            premium_amount=Decimal("100000.00"),
            premium_frequency="ANNUALLY",
            term_years=10,
            risk_commencement_date=date.today() - timedelta(days=4000),
            maturity_date=date.today() - timedelta(days=1),
            status=PolicyStatus.ACTIVE,
            contract_snapshot={"maturity_value": "500000.00", "plans": [{"product_code": "OL_MATURITY_PRODUCT"}]},
        )
        PolicyLoan.objects.create(
            policy=self.policy,
            principal_amount=Decimal("50000.00"),
            outstanding_principal=Decimal("50000.00"),
            outstanding_interest=Decimal("0.00"),
            currency="TZS",
            status=LoanStatus.DISBURSED,
            disbursed_at=date.today() - timedelta(days=10),
        )
        OLMaturityClaimSetup.objects.create(
            code="MATURITY-SETUP-1",
            name="Maturity setup",
            effective_from=date.today() - timedelta(days=3650),
            auto_create_maturity_claim=True,
            days_before_maturity_to_initiate=0,
            default_payout_method="BANK_TRANSFER",
            require_documents=True,
            require_approval=True,
            maturity_claim_status_to_create="REPORTED",
            is_active=True,
        )
        self.client.force_authenticate(self.user)

    def test_maturity_command_creates_claim_with_loan_deduction_and_is_idempotent(self):
        output = StringIO()
        call_command("process_policy_maturity", "--as-of", date.today().isoformat(), stdout=output)
        self.assertIn("created=1", output.getvalue())
        self.policy.refresh_from_db()
        claim = MaturityClaim.objects.get(policy=self.policy)
        self.assertEqual(self.policy.status, PolicyStatus.MATURED_PENDING_PAYMENT)
        self.assertEqual(claim.status, MaturityClaimStatus.PENDING_DOCUMENTS)
        self.assertEqual(claim.maturity_value, Decimal("500000.00"))
        self.assertEqual(claim.loan_deduction, Decimal("50000.00"))
        self.assertEqual(claim.net_payout, Decimal("450000.00"))
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_MATURITY_CLAIM_CREATED, aggregate_id=str(self.policy.pk)).count(), 1)

        output = StringIO()
        call_command("process_policy_maturity", "--as-of", date.today().isoformat(), stdout=output)
        self.assertIn("created=0", output.getvalue())
        self.assertEqual(MaturityClaim.objects.filter(policy=self.policy).count(), 1)
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_MATURITY_CLAIM_CREATED, aggregate_id=str(self.policy.pk)).count(), 1)

    def test_maturity_api_requires_documents_then_approves_and_pays(self):
        response = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/maturity/",
            {"as_of": date.today().isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        claim_id = response.data["data"]["claim"]["id"]

        blocked = self.client.post(f"/api/v1/ol/policies/maturity/{claim_id}/approve/", {}, format="json")
        self.assertEqual(blocked.status_code, 422)
        self.assertIn("documents_verified", blocked.data["field_errors"])

        approved = self.client.post(
            f"/api/v1/ol/policies/maturity/{claim_id}/approve/",
            {"documents_verified": True},
            format="json",
        )
        self.assertEqual(approved.status_code, 200)
        claim = MaturityClaim.objects.get(pk=claim_id)
        self.assertEqual(claim.status, MaturityClaimStatus.APPROVED)
        self.assertTrue(claim.payment_requisition_id)
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_MATURITY_CLAIM_APPROVED, aggregate_id=str(self.policy.pk)).count(), 1)

        missing_reference = self.client.post(f"/api/v1/ol/policies/maturity/{claim_id}/pay/", {}, format="json")
        self.assertEqual(missing_reference.status_code, 422)
        paid = self.client.post(
            f"/api/v1/ol/policies/maturity/{claim_id}/pay/",
            {"payment_reference": "BANK-MAT-0001"},
            format="json",
        )
        self.assertEqual(paid.status_code, 200)
        claim.refresh_from_db()
        self.policy.refresh_from_db()
        self.assertEqual(claim.status, MaturityClaimStatus.PAID)
        self.assertEqual(self.policy.status, PolicyStatus.MATURED)
        self.assertEqual(claim.payment_reference, "BANK-MAT-0001")
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_MATURITY_PAID, aggregate_id=str(self.policy.pk)).count(), 1)

    def test_maturity_list_and_invalid_date_are_teachable(self):
        invalid = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/maturity/",
            {"as_of": "not-a-date"},
            format="json",
        )
        self.assertEqual(invalid.status_code, 422)
        self.assertIn("as_of", invalid.data["field_errors"])
        listing = self.client.get(f"/api/v1/ol/policies/{self.policy.pk}/maturity/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["data"], [])
