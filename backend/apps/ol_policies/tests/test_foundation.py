from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from apps.ol_policies.errors import POLICY_ERROR_REGISTRY
from apps.ol_policies.models import Policy, PolicyBenefit, PolicyEndorsement, PolicyMember, PolicyRider
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner
from apps.users.models import UserPermission


class PolicyFoundationTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="policy-admin",
            email="policy-admin@example.com",
            password="Strong-policy-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Asha Mwinyi",
            email="asha@example.com",
            mobile_number="+255711000001",
            phone="+255711000001",
        )
        self.agent = Partner.objects.create(
            partner_number="ZIC-A-0001",
            partner_type="AGENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Juma Agent",
            email="juma.agent@example.com",
            mobile_number="+255711000002",
            phone="+255711000002",
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-FOUNDATION-0001",
            quote_name="Foundation quote",
            quote_date=date(2026, 1, 1),
            partner=self.partner,
            currency="TZS",
        )
        self.proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-FOUNDATION-0001",
            status="AWAITING_FIRST_PREMIUM",
            partner=self.partner,
            agent_partner=self.agent,
            currency="TZS",
        )
        self.client.force_authenticate(self.user)

    def make_policy(self, *, policy_number="", status="ACTIVE"):
        return Policy.objects.create(
            policy_number=policy_number,
            proposal_ref=self.proposal,
            partner=self.partner,
            agent=self.agent,
            product_plan_ref="OL_TERM_STANDARD",
            currency="TZS",
            sum_assured=Decimal("25000000.00"),
            premium_amount=Decimal("125000.00"),
            premium_frequency="ANNUALLY",
            term_years=10,
            risk_commencement_date=date(2026, 1, 15),
            maturity_date=date(2036, 1, 14),
            status=status,
        )

    def test_policy_creation_and_snapshot_relationships(self):
        policy = self.make_policy()
        member = PolicyMember.objects.create(
            policy=policy,
            member_relation="PRINCIPAL",
            name="Asha Mwinyi",
            dob=date(1990, 6, 15),
            gender="FEMALE",
            benefit_amount=Decimal("25000000.00"),
        )
        rider = PolicyRider.objects.create(
            policy=policy,
            rider_code="OL_WAIVER",
            sum_assured=Decimal("25000000.00"),
            amount=Decimal("25000000.00"),
            premium=Decimal("15000.00"),
        )
        benefit = PolicyBenefit.objects.create(
            policy=policy,
            benefit_type="DEATH",
            calculation_basis="FIXED",
            amount=Decimal("25000000.00"),
        )
        endorsement = PolicyEndorsement.objects.create(
            policy=policy,
            endorsement_type="ADDRESS_CHANGE",
            effective_date=date(2026, 2, 1),
            description="Address updated by policyholder.",
        )

        self.assertTrue(policy.policy_number.startswith("POL-"))
        self.assertEqual(policy.proposal_ref, self.proposal)
        self.assertEqual(policy.partner, self.partner)
        self.assertEqual(policy.agent, self.agent)
        self.assertEqual(list(policy.members.all()), [member])
        self.assertEqual(list(policy.riders.all()), [rider])
        self.assertEqual(list(policy.benefits.all()), [benefit])
        self.assertEqual(list(policy.endorsements.all()), [endorsement])
        self.assertTrue(endorsement.endorsement_number.startswith("END-"))

    def test_policy_number_is_unique(self):
        self.make_policy(policy_number="POL-EXPLICIT-0001")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_policy(policy_number="POL-EXPLICIT-0001")

    def test_status_and_contract_validation(self):
        policy = self.make_policy(status="NOT_A_POLICY_STATUS")
        with self.assertRaises(ValidationError):
            policy.full_clean()

        policy.status = "ACTIVE"
        policy.maturity_date = policy.risk_commencement_date
        with self.assertRaises(ValidationError) as raised:
            policy.full_clean()
        self.assertIn("maturity_date", raised.exception.message_dict)

    def test_policy_error_registry_contains_required_codes_and_teachable_shape(self):
        required_codes = {
            "POLICY_NOT_FOUND",
            "POLICY_ALREADY_ISSUED",
            "POLICY_INVALID_STATUS",
            "POLICY_SURRENDER_BLOCKED",
            "POLICY_LOAN_BLOCKED",
            "POLICY_LAPSED",
            "POLICY_NOT_MATURED",
            "POLICY_ENDORSEMENT_INVALID",
        }
        self.assertTrue(required_codes.issubset(POLICY_ERROR_REGISTRY))
        for definition in POLICY_ERROR_REGISTRY.values():
            self.assertTrue(definition["message"])
            self.assertGreaterEqual(definition["status_code"], 400)
            self.assertTrue(definition["resolution_steps"])

    def test_list_and_detail_return_human_readable_relationships(self):
        policy = self.make_policy()
        list_response = self.client.get("/api/v1/ol/policies/")
        self.assertEqual(list_response.status_code, 200)
        row = list_response.data["data"]["results"][0]
        self.assertEqual(row["policy_number"], policy.policy_number)
        self.assertEqual(row["proposal_ref_display"], "PROP-FOUNDATION-0001")
        self.assertIn("Asha Mwinyi", row["policyholder_display"])
        self.assertIn("Juma Agent", row["agent_display"])
        self.assertEqual(row["product_plan_display"], "OL_TERM_STANDARD")
        self.assertNotIn("partner", row)
        self.assertNotIn("agent", row)

        detail_response = self.client.get(f"/api/v1/ol/policies/{policy.id}/")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.data["data"]["policy_number"], policy.policy_number)
        self.assertIn("members", detail_response.data["data"])
        self.assertIn("audit_logs", detail_response.data["data"])

    def test_permission_seed_registers_all_policy_actions(self):
        call_command("seed_ol_policy_permissions", verbosity=0)
        expected = {f"ol_policies.{action}" for action in ("view", "create", "service", "endorse", "cancel", "reinstate", "print", "configure")}
        actual = set(UserPermission.objects.filter(module="ol_policies").values_list("codename", flat=True))
        self.assertSetEqual(actual, expected)

    def test_unknown_policy_returns_structured_error_shape(self):
        response = self.client.get(f"/api/v1/ol/policies/{uuid4()}/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error_code"], "POLICY_NOT_FOUND")
        self.assertTrue(response.data["resolution_steps"])
        self.assertEqual(response.data["doc_ref"], "docs/OL_POLICIES_DESIGN.md")
