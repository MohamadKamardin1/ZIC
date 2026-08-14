from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.ordinary_life.models import (
    OLBeneficiary,
    OLBeneficiaryAllocation,
    OLClient,
    OLPaymentObligation,
    OLPlan,
    OLPolicy,
    OLProduct,
    OLProductVersion,
    OLProposal,
    OLQuotation,
    OLQuotationVersion,
    validate_policy_beneficiary_total,
)
from apps.partners.models import Partner


class OrdinaryLifePhase3ModelTests(TestCase):
    def make_partner(self, suffix="1"):
        return Partner.objects.create(
            partner_number=f"IA-PH3-{suffix}",
            partner_type="INDIVIDUAL",
            party_type="INDIVIDUAL",
            partner_category="INDIVIDUAL",
            first_name="Phase",
            surname=f"Three{suffix}",
            email=f"phase3-{suffix}@example.test",
            mobile_number=f"25570000{suffix.zfill(2)}",
        )

    def make_quotation(self):
        product = OLProduct.objects.create(code="PH3-PROD", name="Phase Three Product")
        client = OLClient.objects.create(
            first_name="Legacy",
            last_name="Client",
            date_of_birth=date(1990, 1, 1),
            id_number="PH3-CLIENT-1",
        )
        quotation = OLQuotation.objects.create(
            quotation_number="PH3-QUOTE-1",
            client=client,
            product=product,
            sum_assured=Decimal("1000000.00"),
            premium_amount=Decimal("10000.00"),
        )
        version = OLProductVersion.objects.create(
            product=product,
            version_number=1,
            effective_from=date(2026, 1, 1),
            min_entry_age=18,
            max_entry_age=65,
            min_term_years=1,
            max_term_years=30,
        )
        return quotation, version

    def make_policy(self):
        quotation, version = self.make_quotation()
        proposal = OLProposal.objects.create(
            proposal_number="PH3-PROPOSAL-1",
            quotation=quotation,
        )
        policy = OLPolicy.objects.create(
            policy_number="PH3-POLICY-1",
            proposal=proposal,
            product_version=version,
            start_date=date(2026, 2, 1),
            end_date=date(2056, 1, 31),
        )
        return policy

    def test_product_version_rejects_invalid_ranges(self):
        product = OLProduct.objects.create(code="PH3-RANGE", name="Range Product")
        invalid = OLProductVersion(
            product=product,
            version_number=1,
            effective_from=date(2026, 2, 1),
            effective_to=date(2026, 1, 1),
            min_entry_age=70,
            max_entry_age=18,
            min_term_years=20,
            max_term_years=10,
        )
        with self.assertRaises(ValidationError):
            invalid.full_clean()

    def test_product_version_number_is_unique_per_product(self):
        product = OLProduct.objects.create(code="PH3-UNIQUE", name="Unique Product")
        OLProductVersion.objects.create(
            product=product,
            version_number=1,
            effective_from=date(2026, 1, 1),
        )
        with self.assertRaises(IntegrityError):
            OLProductVersion.objects.create(
                product=product,
                version_number=1,
                effective_from=date(2027, 1, 1),
            )

    def test_quotation_version_requires_unique_number_and_calculation_hash(self):
        quotation, product_version = self.make_quotation()
        OLQuotationVersion.objects.create(
            quotation=quotation,
            version_number=1,
            product_version=product_version,
            calculation_hash="hash-one",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OLQuotationVersion.objects.create(
                    quotation=quotation,
                    version_number=1,
                    product_version=product_version,
                    calculation_hash="hash-two",
                )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OLQuotationVersion.objects.create(
                    quotation=quotation,
                    version_number=2,
                    product_version=product_version,
                    calculation_hash="hash-one",
                )

    def test_payment_obligation_rejects_zero_amount(self):
        quotation, _ = self.make_quotation()
        proposal = OLProposal.objects.create(proposal_number="PH3-PAY-PROPOSAL", quotation=quotation)
        obligation = OLPaymentObligation(
            proposal=proposal,
            obligation_type="FIRST_PREMIUM",
            amount=Decimal("0.00"),
            due_date=date(2026, 3, 1),
        )
        with self.assertRaises(ValidationError):
            obligation.full_clean()

    def test_policy_party_uses_canonical_partner_and_snapshot(self):
        policy = self.make_policy()
        partner = self.make_partner()
        party = policy.policy_parties.create(
            partner=partner,
            role="POLICYHOLDER",
            is_primary=True,
            effective_from=date(2026, 2, 1),
            identity_snapshot={"partner_number": partner.partner_number, "name": partner.display_name},
        )
        self.assertEqual(party.partner_id, partner.id)
        self.assertEqual(party.identity_snapshot["partner_number"], partner.partner_number)

    def test_beneficiary_allocations_must_total_exactly_one_hundred_before_issuance(self):
        policy = self.make_policy()
        beneficiary_one = OLBeneficiary.objects.create(
            policy=policy,
            name="Beneficiary One",
            relationship="Child",
            percentage=Decimal("60.00"),
        )
        beneficiary_two = OLBeneficiary.objects.create(
            policy=policy,
            name="Beneficiary Two",
            relationship="Child",
            percentage=Decimal("30.00"),
        )
        OLBeneficiaryAllocation.objects.create(
            policy=policy,
            beneficiary=beneficiary_one,
            percentage=Decimal("60.00"),
            effective_from=date(2026, 2, 1),
        )
        OLBeneficiaryAllocation.objects.create(
            policy=policy,
            beneficiary=beneficiary_two,
            percentage=Decimal("30.00"),
            effective_from=date(2026, 2, 1),
        )
        with self.assertRaises(ValidationError):
            validate_policy_beneficiary_total(policy)
        OLBeneficiaryAllocation.objects.create(
            policy=policy,
            beneficiary=beneficiary_two,
            percentage=Decimal("10.00"),
            effective_from=date(2026, 2, 1),
        )
        self.assertEqual(validate_policy_beneficiary_total(policy), Decimal("100.00"))


class OrdinaryLifePhase3PlanTests(TestCase):
    def test_plan_rejects_reversed_sum_assured_range(self):
        product = OLProduct.objects.create(code="PH3-PLAN", name="Plan Product")
        version = OLProductVersion.objects.create(
            product=product,
            version_number=1,
            effective_from=date(2026, 1, 1),
        )
        plan = OLPlan(
            product_version=version,
            code="BASIC",
            name="Basic",
            minimum_sum_assured=Decimal("1000000.00"),
            maximum_sum_assured=Decimal("500000.00"),
        )
        with self.assertRaises(ValidationError):
            plan.full_clean()
