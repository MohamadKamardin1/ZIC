from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase as DRFTestCase

from apps.common.models import DomainEvent
from apps.governance.models import AuditLog
from apps.ol_parameters.models import OLDefaultParameterValueType, OLDefaultSystemParameter
from apps.ol_proposals.errors import ProposalError
from apps.ol_proposals.services.conversion_service import convert_quotation_to_proposal
from apps.ol_quotations.models import (
    OLQuotation,
    OLQuotationBenefit,
    OLQuotationFinancialSummary,
    OLQuotationInstallmentConfiguration,
    OLQuotationInstallmentRateRow,
    OLQuotationMember,
    OLQuotationPlanConfiguration,
    OLQuotationVersion,
    QuotationStatus,
)
from apps.ordinary_life.models import OLPlan, OLProduct, OLProductVersion
from apps.partners.models import Partner

User = get_user_model()


class ConversionServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="convert_ops", password="Password@12345", email="convert_ops@zic.tz")
        self.today = date.today()
        OLDefaultSystemParameter.objects.create(code="PROPOSAL_VALIDITY_DAYS", parameter_key="PROPOSAL_VALIDITY_DAYS", parameter_category="PROPOSAL", name="Proposal validity days", value_type=OLDefaultParameterValueType.INTEGER, integer_value=45, is_active=True, effective_from=date(2020,1,1))
        self.partner = Partner.objects.create(
            partner_number="PT-OLP-0001",
            partner_type="INDIVIDUAL",
            party_type="INDIVIDUAL",
            first_name="Amina",
            surname="Salim",
            email="amina.olp@example.com",
            mobile_number="255700000001",
            identification_type="NIN",
            identification_number="ID-OLP-0001",
            date_of_birth=date(1990, 1, 1),
            is_active=True,
            status="ACTIVE",
        )
        self.product = OLProduct.objects.create(code="OL_TERM", name="Term Life")
        self.product_version = OLProductVersion.objects.create(
            product=self.product, version_number=1, effective_from=self.today - timedelta(days=30)
        )
        self.plan = OLPlan.objects.create(
            product_version=self.product_version, code="TERM-20", name="Twenty Year Term",
            minimum_sum_assured=Decimal("10000"), maximum_sum_assured=Decimal("1000000"),
        )
        self.quotation = OLQuotation.objects.create(quote_number="Q-CONV-0001", currency="TZS")
        self.quotation.status = QuotationStatus.FINALIZED
        self.quotation.partner = self.partner
        self.quotation.partner_verified = True
        self.quotation.save(update_fields=["status", "partner", "partner_verified", "updated_at"])

        self.plan_config = OLQuotationPlanConfiguration.objects.create(
            quotation=self.quotation,
            product_version=self.product_version,
            plan=self.plan,
            base_sum_assured=Decimal("500000.00"),
            term_years=20,
            payment_period_years=20,
            premium_frequency="ANNUAL",
            quote_basis="SUM_ASSURED",
            premium_factor="NONE",
            premium_amount=Decimal("25000.00"),
            is_selected=True,
        )
        OLQuotationMember.objects.create(
            quotation=self.quotation, member_type="LIFE_ASSURED", first_name="Amina", last_name="Salim",
            date_of_birth=date(1990, 1, 1), identity_number="ID-OLP-0001",
        )
        self.installment = OLQuotationInstallmentConfiguration.objects.create(
            quotation=self.quotation,
            plan_configuration=self.plan_config,
            frequency="ANNUAL",
            annuity_period_years=20,
            number_of_installments=20,
            installment_amount=Decimal("25000.00"),
            first_due_date=self.today,
            currency="TZS",
            is_selected=True,
        )
        OLQuotationInstallmentRateRow.objects.create(
            installment_configuration=self.installment,
            period_from=1,
            period_to=20,
            description="Level premium",
            rate=Decimal("0.00500000"),
            charge=Decimal("0"),
        )
        OLQuotationBenefit.objects.create(
            quotation=self.quotation, code="ACCIDENT", name="Accident benefit", basis="FIXED",
            value=Decimal("100000.00"), premium_amount=Decimal("5000.00"), is_selected=True,
        )
        OLQuotationFinancialSummary.objects.create(
            quotation=self.quotation,
            total_sum_assured=Decimal("500000.00"),
            total_premium=Decimal("25000.00"),
            base_premium=Decimal("25000.00"),
            currency="TZS",
        )
        self.version = OLQuotationVersion.objects.create(
            quotation=self.quotation,
            version_number=1,
            status=QuotationStatus.FINALIZED,
            snapshot={"children": {}},
        )

    def test_successful_conversion_carries_every_dataset(self):
        result = convert_quotation_to_proposal(quotation=self.quotation, actor=self.user, source_channel="API")
        self.assertTrue(result.created)
        proposal = result.proposal
        self.assertEqual(proposal.status, "ENRICHMENT")
        self.assertEqual(proposal.partner_id, self.partner.pk)
        self.assertEqual(proposal.currency, "TZS")
        self.assertEqual(proposal.expiry_date, self.today + timedelta(days=45))
        self.assertEqual(proposal.plan_configs.count(), 1)
        self.assertEqual(proposal.members.count(), 1)
        self.assertEqual(proposal.installment_configs.count(), 1)
        self.assertEqual(proposal.installment_configs.first().rate_rows.count(), 1)
        self.assertEqual(proposal.benefits.count(), 1)
        self.assertEqual(proposal.plan_configs.first().premium_amount, Decimal("25000.00"))
        self.assertEqual(Decimal(proposal.financial_summary_snapshot["total_premium"]), Decimal("25000.00"))
        self.assertEqual(proposal.prospect_snapshot["quote_number"], "Q-CONV-0001")
        self.assertTrue(
            DomainEvent.objects.filter(event_type="ProposalCreated", aggregate_id=str(proposal.pk)).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(action="CONVERT_QUOTATION_TO_PROPOSAL", object_id=str(proposal.pk)).exists()
        )

    def test_repeated_conversion_returns_same_proposal(self):
        first = convert_quotation_to_proposal(quotation=self.quotation, actor=self.user)
        second = convert_quotation_to_proposal(quotation=self.quotation, actor=self.user)
        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertTrue(second.duplicate)
        self.assertEqual(second.proposal.pk, first.proposal.pk)
        from apps.ol_proposals.models import OLProposal

        self.assertEqual(OLProposal.objects.filter(quotation=self.quotation).count(), 1)

    def test_unverified_partner_blocked_with_teachable_error(self):
        self.quotation.partner_verified = False
        self.quotation.save(update_fields=["partner_verified", "updated_at"])
        with self.assertRaises(ProposalError) as ctx:
            convert_quotation_to_proposal(quotation=self.quotation, actor=self.user)
        error = ctx.exception
        self.assertEqual(error.error_code, "PROPOSAL_PARTNER_NOT_VERIFIED")
        self.assertTrue(any("verify" in step.lower() for step in error.resolution_steps))

    def test_expiry_computed_from_parameter(self):
        OLDefaultSystemParameter.objects.filter(parameter_key="PROPOSAL_VALIDITY_DAYS").update(integer_value=30)
        proposal = convert_quotation_to_proposal(quotation=self.quotation, actor=self.user).proposal
        self.assertEqual(proposal.expiry_date, self.today + timedelta(days=30))


class ConversionEndpointTests(DRFTestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(username="conv_admin", password="Password@12345", email="conv_admin@zic.tz")
        self.user = User.objects.create_user(username="conv_plain", password="Password@12345", email="conv_plain@zic.tz")
        self.today = date.today()
        self.partner = Partner.objects.create(
            partner_number="PT-OLP-0002", partner_type="INDIVIDUAL", party_type="INDIVIDUAL",
            first_name="Hassan", surname="Mfaume", email="hassan.olp@example.com", mobile_number="255700000002",
            identification_type="NIN", identification_number="ID-OLP-0002", date_of_birth=date(1985, 1, 1),
            is_active=True, status="ACTIVE",
        )
        self.quotation = OLQuotation.objects.create(quote_number="Q-CONV-EP-1")
        self.quotation.status = QuotationStatus.FINALIZED
        self.quotation.partner = self.partner
        self.quotation.partner_verified = True
        self.quotation.save(update_fields=["status", "partner", "partner_verified", "updated_at"])
        self.version = OLQuotationVersion.objects.create(
            quotation=self.quotation, version_number=1, status=QuotationStatus.FINALIZED, snapshot={"children": {}}
        )
        self.url = f"/api/v1/ol/proposals/from-quotation/{self.quotation.pk}/"

    def test_endpoint_creates_and_is_idempotent(self):
        self.client.force_authenticate(self.superuser)
        first = self.client.post(self.url, {}, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data["data"]["status"], "ENRICHMENT")
        self.assertTrue(first.data["data"]["created"])
        second = self.client.post(self.url, {}, format="json")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["data"]["id"], first.data["data"]["id"])
        self.assertTrue(second.data["data"]["duplicate"])

    def test_endpoint_requires_create_permission(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url, {}, format="json")
        self.assertIn(response.status_code, (401, 403), response.data)