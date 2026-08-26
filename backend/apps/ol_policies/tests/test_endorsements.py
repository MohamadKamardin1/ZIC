from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.common.models import DomainEvent
from apps.ol_commitments.models import CommitmentSourceType, OLCommitment
from apps.ol_policies.events import POLICY_ENDORSED
from apps.ol_policies.models import Policy, PolicyEndorsement, PolicyMember, PolicyStatus
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner


class PolicyEndorsementTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="endorsement-admin",
            email="endorsement-admin@example.com",
            password="Strong-endorsement-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-END-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Asha Omar",
            email="asha.end@example.com",
            mobile_number="+255711300001",
            phone="+255711300001",
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-END-0001",
            quote_name="Endorsement test quote",
            quote_date=date(2026, 1, 1),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-END-0001",
            status="CONVERTED",
            partner=self.partner,
            currency="TZS",
            prospect_snapshot={},
            financial_summary_snapshot={},
        )
        self.policy = Policy.objects.create(
            proposal_ref=proposal,
            partner=self.partner,
            product_plan_ref="OL_TERM_STANDARD",
            currency="TZS",
            sum_assured=Decimal("50000000.00"),
            premium_amount=Decimal("100000.00"),
            premium_frequency="ANNUALLY",
            term_years=10,
            risk_commencement_date=date(2026, 1, 1),
            maturity_date=date(2036, 1, 1),
            status=PolicyStatus.ACTIVE,
            contract_snapshot={
                "min_members": 1,
                "max_members": 2,
                "premium_change_max_percent": "20",
                "plans": [{"product_code": "ZIC_TERM_STANDARD", "plan_name": "Standard"}],
            },
        )
        self.member = PolicyMember.objects.create(
            policy=self.policy,
            member_relation="PRINCIPAL",
            name="Asha Omar",
            dob=date(1990, 1, 1),
            gender="FEMALE",
            benefit_amount=Decimal("50000000.00"),
        )
        self.client.force_authenticate(self.user)

    def test_premium_change_creates_immutable_endorsement_and_commitment_adjustment(self):
        response = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/endorsements/",
            {
                "endorsement_type": "PREMIUM_CHANGE",
                "effective_date": "2026-06-01",
                "description": "Annual premium updated after approved servicing request.",
                "changes": {"new_premium": "110000.00"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.premium_amount, Decimal("110000.00"))
        endorsement = PolicyEndorsement.objects.get(policy=self.policy)
        self.assertEqual(endorsement.status, "APPLIED")
        self.assertEqual(endorsement.before_snapshot["premium_amount"], "100000.00")
        self.assertEqual(endorsement.after_snapshot["premium_amount"], "110000.00")
        adjustment = OLCommitment.objects.get(source_reference=self.policy.policy_number)
        self.assertEqual(adjustment.source_type, CommitmentSourceType.POLICY)
        self.assertEqual(adjustment.premium_amount, Decimal("10000.00"))
        self.assertEqual(response.data["data"]["commitment"]["commitment_number"], adjustment.commitment_number)
        self.assertEqual(DomainEvent.objects.filter(event_type=POLICY_ENDORSED, aggregate_id=str(self.policy.pk)).count(), 1)

    def test_premium_change_outside_configured_band_is_blocked(self):
        response = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/endorsements/",
            {"endorsement_type": "PREMIUM_CHANGE", "changes": {"new_premium": "130000.00"}},
            format="json",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "POLICY_ENDORSEMENT_INVALID")
        self.assertIn("new_premium", response.data["field_errors"])
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.premium_amount, Decimal("100000.00"))
        self.assertFalse(PolicyEndorsement.objects.filter(policy=self.policy).exists())

    def test_member_add_and_remove_preserve_history_and_validate_limits(self):
        add = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/endorsements/",
            {
                "endorsement_type": "MEMBER_ADD",
                "changes": {
                    "member_relation": "SPOUSE",
                    "name": "Omar Asha",
                    "dob": "1991-02-02",
                    "gender": "MALE",
                    "benefit_amount": "25000000.00",
                },
            },
            format="json",
        )
        self.assertEqual(add.status_code, 201)
        new_member = PolicyMember.objects.get(policy=self.policy, name="Omar Asha")
        self.assertTrue(new_member.is_active)

        blocked_add = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/endorsements/",
            {
                "endorsement_type": "MEMBER_ADD",
                "changes": {
                    "member_relation": "CHILD",
                    "name": "Child Asha",
                    "dob": "2015-03-03",
                    "gender": "FEMALE",
                    "benefit_amount": "10000000.00",
                },
            },
            format="json",
        )
        self.assertEqual(blocked_add.status_code, 422)
        self.assertIn("maximum number", blocked_add.data["message"])

        remove = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/endorsements/",
            {"endorsement_type": "MEMBER_REMOVE", "changes": {"member_id": str(new_member.pk)}},
            format="json",
        )
        self.assertEqual(remove.status_code, 201)
        new_member.refresh_from_db()
        self.assertFalse(new_member.is_active)
        self.assertEqual(new_member.ended_at, date.today())

    def test_member_remove_cannot_violate_minimum_members(self):
        response = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/endorsements/",
            {"endorsement_type": "MEMBER_REMOVE", "changes": {"member_id": str(self.member.pk)}},
            format="json",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "POLICY_ENDORSEMENT_INVALID")
        self.member.refresh_from_db()
        self.assertTrue(self.member.is_active)

    def test_lapsed_policy_cannot_be_endorsed_before_reinstatement(self):
        self.policy.status = PolicyStatus.LAPSED
        self.policy.save(update_fields=["status"])
        response = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/endorsements/",
            {"endorsement_type": "ADDRESS_CHANGE", "changes": {"address": "Stone Town"}},
            format="json",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "POLICY_INVALID_STATUS")

    def test_endorsement_history_list_and_detail_show_before_after(self):
        response = self.client.post(
            f"/api/v1/ol/policies/{self.policy.pk}/endorsements/",
            {"endorsement_type": "ADDRESS_CHANGE", "changes": {"address": "Mkunazini"}},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        endorsement_id = response.data["data"]["endorsement"]["id"]

        listing = self.client.get(f"/api/v1/ol/policies/{self.policy.pk}/endorsements/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data["data"]), 1)
        self.assertEqual(listing.data["data"][0]["after_snapshot"]["contract_snapshot"]["address"], "Mkunazini")

        detail = self.client.get(f"/api/v1/ol/policies/{self.policy.pk}/endorsements/{endorsement_id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["data"]["before_snapshot"]["premium_amount"], "100000.00")
