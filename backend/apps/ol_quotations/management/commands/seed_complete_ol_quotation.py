from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.ol_parameters.models import (
    OLBeneficialType,
    OLInvestmentFund,
    OLProduct,
    OLRiderSetup,
)
from apps.ol_quotations.models import (
    OLQuotation,
    OLQuotationBeneficiary,
    OLQuotationBenefit,
    OLQuotationFundAllocation,
    OLQuotationInstallmentConfiguration,
    OLQuotationInstallmentRateRow,
    OLQuotationMember,
    OLQuotationPaymentDetail,
    OLQuotationPlanConfiguration,
    OLQuotationProduct,
    OLQuotationRiderSelection,
    OLQuotationUnderwriting,
    QuotationStatus,
)
from apps.ol_quotations.services.document_service import QuotationDocumentService
from apps.ol_quotations.services.quotation_service import QuotationService
from apps.ordinary_life.models import OLPlan, OLProductVersion
from apps.partner_onboarding.models import Location
from apps.partners.models import Partner, PartnerTypeAssignment
from apps.users.models import User

SEED_MARKER_KEY = "seed_marker"
SEED_MARKER_VALUE = "complete_ol_quotation"

BALANCED_FUND_CODE = "ZIC_BAL_TZS"
EQUITY_FUND_CODE = "ZIC_EQ_TZS"
ACCIDENTAL_DEATH_RIDER_CODE = "ZIC_ACCIDENTAL_DEATH_RIDER_OL_EDUCATION_SAVINGS"
PREMIUM_WAIVER_RIDER_CODE = "ZIC_PREMIUM_WAIVER_RIDER_OL_EDUCATION_SAVINGS"
PRODUCT_VERSION_CODE = "OL_EDUCATION_SAVINGS"
PLAN_CODE = "OL_EDU_GROWTH"
PRODUCT_CODE = "OL_EDUCATION_SAVINGS"
AGENT_PARTNER_NUMBER = "ZIC-AGENT-0001"
PROSPECT_PARTNER_NUMBER = "PN-2026-000002"
LINKED_PARTNER_NUMBER = "PN-2026-000001"
LOCATION_CODE = "ZIC-JAMBIANI"


class Command(BaseCommand):
    help = (
        "Seed one complete Ordinary Life quotation with every module and field populated, "
        "then finalize it and generate its print document. Re-running replaces the prior seed."
    )

    def add_arguments(self, parser):
        parser.add_argument("--quote-name", default="ZIC Complete OL Quotation Seed")
        parser.add_argument(
            "--no-replace",
            action="store_true",
            help="Error instead of replacing an existing seeded complete quotation.",
        )
        parser.add_argument(
            "--no-document",
            action="store_true",
            help="Finalize but skip generating the print document.",
        )
        parser.add_argument(
            "--no-finalize",
            action="store_true",
            help="Build a complete DRAFT only (no calculation, finalize, or document).",
        )

    @staticmethod
    def _get_or_error(queryset, label):
        value = queryset.first()
        if value is None:
            raise CommandError(f"Required reference data not found: {label}.")
        return value

    @staticmethod
    def _age_at(date_of_birth, on_date):
        return on_date.year - date_of_birth.year - ((on_date.month, on_date.day) < (date_of_birth.month, date_of_birth.day))

    def handle(self, *args, **options):
        actor = (
            User.objects.filter(username="sultan").first()
            or User.objects.filter(is_superuser=True).order_by("username").first()
            or User.objects.filter(is_active=True).order_by("username").first()
        )
        if actor is None:
            raise CommandError("No active user is available to act as the quotation creator.")

        product_version = self._get_or_error(
            OLProductVersion.objects.filter(product__code=PRODUCT_VERSION_CODE, is_active=True).order_by("-version_number"),
            f"product version {PRODUCT_VERSION_CODE}",
        )
        plan = self._get_or_error(OLPlan.objects.filter(code=PLAN_CODE), f"plan {PLAN_CODE}")
        parameter_product = self._get_or_error(OLProduct.objects.filter(code=PRODUCT_CODE), f"product {PRODUCT_CODE}")
        location = self._get_or_error(Location.objects.filter(code=LOCATION_CODE), f"location {LOCATION_CODE}")
        agent_partner = self._get_or_error(
            Partner.objects.filter(partner_number=AGENT_PARTNER_NUMBER),
            f"agent partner {AGENT_PARTNER_NUMBER}",
        )
        prospect = self._get_or_error(
            Partner.objects.filter(partner_number=PROSPECT_PARTNER_NUMBER),
            f"prospect partner {PROSPECT_PARTNER_NUMBER}",
        )
        linked_partner = self._get_or_error(
            Partner.objects.filter(partner_number=LINKED_PARTNER_NUMBER),
            f"linked partner {LINKED_PARTNER_NUMBER}",
        )
        spouse_partner = self._get_or_error(
            PartnerTypeAssignment.objects.filter(partner_type__code="CLIENT", status="ACTIVE")
            .exclude(partner__partner_number=LINKED_PARTNER_NUMBER)
            .select_related("partner"),
            "a second CLIENT partner for the spouse member",
        ).partner
        child_partner = self._get_or_error(
            Partner.objects.filter(is_active=True, partner_type="INDIVIDUAL")
            .exclude(pk__in=[prospect.pk, linked_partner.pk, spouse_partner.pk, agent_partner.pk])
            .order_by("pk"),
            "an individual partner for the child beneficiary",
        )
        balanced_fund = self._get_or_error(
            OLInvestmentFund.objects.filter(code=BALANCED_FUND_CODE, is_active=True),
            f"fund {BALANCED_FUND_CODE}",
        )
        equity_fund = self._get_or_error(
            OLInvestmentFund.objects.filter(code=EQUITY_FUND_CODE, is_active=True),
            f"fund {EQUITY_FUND_CODE}",
        )
        accidental_death_rider = self._get_or_error(
            OLRiderSetup.objects.filter(code=ACCIDENTAL_DEATH_RIDER_CODE, is_active=True),
            f"rider {ACCIDENTAL_DEATH_RIDER_CODE}",
        )
        premium_waiver_rider = self._get_or_error(
            OLRiderSetup.objects.filter(code=PREMIUM_WAIVER_RIDER_CODE, is_active=True),
            f"rider {PREMIUM_WAIVER_RIDER_CODE}",
        )
        death_benefit_type = self._get_or_error(
            OLBeneficialType.objects.filter(code="DEATH_BENEFIT", is_active=True),
            "beneficial type DEATH_BENEFIT",
        )
        maturity_benefit_type = self._get_or_error(
            OLBeneficialType.objects.filter(code="MATURITY_BENEFIT", is_active=True),
            "beneficial type MATURITY_BENEFIT",
        )

        existing = OLQuotation.objects.filter(metadata__has_key=SEED_MARKER_KEY, metadata__seed_marker=SEED_MARKER_VALUE).first()
        if existing is not None:
            if options["no_replace"]:
                raise CommandError(
                    f"A seeded complete quotation already exists ({existing.quote_number}); use without --no-replace to rebuild it."
                )
            self.stdout.write(f"Removing prior seeded quotation {existing.quote_number}...")
            existing.delete()

        quote_date = date.today()
        quote = self._build_quotation(
            actor=actor,
            quote_name=options["quote_name"],
            quote_date=quote_date,
            product_version=product_version,
            plan=plan,
            parameter_product=parameter_product,
            location=location,
            agent_partner=agent_partner,
            prospect=prospect,
            linked_partner=linked_partner,
            spouse_partner=spouse_partner,
            child_partner=child_partner,
            balanced_fund=balanced_fund,
            equity_fund=equity_fund,
            accidental_death_rider=accidental_death_rider,
            premium_waiver_rider=premium_waiver_rider,
            death_benefit_type=death_benefit_type,
            maturity_benefit_type=maturity_benefit_type,
        )

        if options["no_finalize"]:
            self._report(quote, finalized=False, document=None)
            return

        summary = QuotationService.calculate_premium(quotation=quote, actor=actor)
        payment = quote.payment_detail
        payment.amount = summary.total_premium
        payment.updated_by = actor
        payment.save(update_fields=["amount", "updated_by", "updated_at"])

        quote = QuotationService.transition(
            quotation=quote,
            target_status=QuotationStatus.FINALIZED,
            actor=actor,
            notes="Complete seeded Ordinary Life quotation finalized.",
        )
        quote = OLQuotation.objects.get(pk=quote.pk)

        document = None
        if not options["no_document"]:
            document = QuotationDocumentService.generate(quotation=quote, actor=actor)
        self._report(quote, finalized=True, document=document)

    @transaction.atomic
    def _build_quotation(self, **ctx):
        actor = ctx["actor"]
        quote_date = ctx["quote_date"]
        quote_name = ctx["quote_name"]
        product_version = ctx["product_version"]
        plan = ctx["plan"]
        parameter_product = ctx["parameter_product"]
        location = ctx["location"]
        agent_partner = ctx["agent_partner"]
        prospect = ctx["prospect"]
        linked_partner = ctx["linked_partner"]
        spouse_partner = ctx["spouse_partner"]
        child_partner = ctx["child_partner"]
        balanced_fund = ctx["balanced_fund"]
        equity_fund = ctx["equity_fund"]
        accidental_death_rider = ctx["accidental_death_rider"]
        premium_waiver_rider = ctx["premium_waiver_rider"]
        death_benefit_type = ctx["death_benefit_type"]
        maturity_benefit_type = ctx["maturity_benefit_type"]

        prospect_first = prospect.first_name or "Prospect"
        prospect_last = prospect.surname or prospect.legal_name or "Partner"
        prospect_identity_type = prospect.identification_type or "NIN"
        prospect_identity_number = prospect.identification_number or "NIN-1985-0615-001"
        prospect_dob = prospect.date_of_birth or date(1995, 6, 15)
        prospect_gender = prospect.gender or "MALE"

        quote = QuotationService.create_draft(
            actor=actor,
            validated_data={
                "partner": prospect,
                "linked_partner": linked_partner,
                "product": parameter_product,
                "product_version": product_version,
                "currency": "TZS",
                "quote_name": quote_name,
                "quote_date": quote_date,
                "identity_type": prospect_identity_type,
                "identity_number": prospect_identity_number,
                "date_of_birth": prospect_dob,
                "gender": prospect_gender,
                "smoker_status": "SMOKER",
                "location": "Jambiani, Unguja South, Zanzibar",
                "location_master": location,
                "agent_partner": agent_partner,
                "address": "Mizingani Road, Stone Town, Zanzibar",
                "partner_verified": False,
                "approval_required": False,
                "expiry_date": quote_date + timedelta(days=30),
                "metadata": {SEED_MARKER_KEY: SEED_MARKER_VALUE},
            },
        )

        OLQuotationProduct.objects.create(
            quotation=quote,
            product=parameter_product,
            product_version=product_version,
            product_name_snapshot=parameter_product.name,
            currency="TZS",
            is_selected=True,
            is_primary=True,
            metadata={},
            created_by=actor,
            updated_by=actor,
        )

        plan_config = OLQuotationPlanConfiguration.objects.create(
            quotation=quote,
            product_version=product_version,
            plan=plan,
            sub_product_code="BASE",
            section_number=1,
            is_selected=True,
            base_sum_assured=Decimal("5000000.00"),
            term_years=5,
            payment_period_years=5,
            premium_frequency="MONTHLY",
            quote_basis="SUM_ASSURED",
            estimated_maturity_value=Decimal("5000000.00"),
            premium_factor="NONE",
            joint_life=False,
            mortgage=False,
            personal_accident=True,
            premium_waiver=True,
            estimated_bonus_rate=Decimal("0.0000"),
            premium_amount=None,
            coverage_rules={"riders_required": False, "investment_linked": False},
            created_by=actor,
            updated_by=actor,
        )

        principal_member = OLQuotationMember.objects.create(
            quotation=quote,
            member_type="LIFE_ASSURED",
            partner=prospect,
            first_name=prospect_first,
            last_name=prospect_last,
            identity_number=prospect_identity_number,
            date_of_birth=prospect_dob,
            age_at_quote=self._age_at(prospect_dob, quote_date),
            gender=prospect_gender,
            smoker_status="SMOKER",
            relationship="SELF",
            contact_phone=prospect.mobile_number or "+255 700 123 456",
            contact_email=prospect.email or f"{prospect_first.lower()}@example.com",
            member_sum_assured=Decimal("5000000.00"),
            coverage_basis="PRINCIPAL",
            waiting_period_days=0,
            metadata={"is_principal": True, "source": SEED_MARKER_VALUE},
            created_by=actor,
            updated_by=actor,
        )
        OLQuotationMember.objects.create(
            quotation=quote,
            member_type="DEPENDENT",
            partner=spouse_partner,
            first_name=spouse_partner.first_name or "Fatma",
            last_name=spouse_partner.surname or "Sultan",
            identity_number="NIN-1997-0220-002",
            date_of_birth=date(1997, 2, 20),
            age_at_quote=29,
            gender="FEMALE",
            smoker_status="NON_SMOKER",
            relationship="SPOUSE",
            contact_phone=spouse_partner.mobile_number or "+255 700 222 333",
            contact_email=spouse_partner.email or "spouse@example.com",
            member_sum_assured=Decimal("2500000.00"),
            coverage_basis="DEPENDENT",
            waiting_period_days=30,
            metadata={"is_principal": False, "source": SEED_MARKER_VALUE},
            created_by=actor,
            updated_by=actor,
        )
        OLQuotationMember.objects.create(
            quotation=quote,
            member_type="DEPENDENT",
            partner=child_partner,
            first_name=child_partner.first_name or "Zuri",
            last_name=child_partner.surname or "Sultan",
            identity_number="NIN-2018-0510-003",
            date_of_birth=date(2018, 5, 10),
            age_at_quote=8,
            gender="FEMALE",
            smoker_status="NON_SMOKER",
            relationship="CHILD",
            contact_phone=child_partner.mobile_number or "",
            contact_email=child_partner.email or "",
            member_sum_assured=Decimal("1000000.00"),
            coverage_basis="DEPENDENT",
            waiting_period_days=60,
            metadata={"is_principal": False, "source": SEED_MARKER_VALUE},
            created_by=actor,
            updated_by=actor,
        )

        installment = OLQuotationInstallmentConfiguration.objects.create(
            quotation=quote,
            plan_configuration=plan_config,
            frequency="BANK_TRANSFER",
            annuity_period_years=1,
            number_of_installments=3,
            after_maturity_benefits=True,
            before_maturity_benefits=False,
            installment_amount=Decimal("5000000.00"),
            first_due_date=quote_date,
            currency="TZS",
            is_selected=True,
            created_by=actor,
            updated_by=actor,
        )
        rate_rows = [
            (1, "40.0000", 1, 1, "First installment (40%)"),
            (2, "35.0000", 2, 2, "Second installment (35%)"),
            (3, "25.0000", 3, 3, "Final installment (25%)"),
        ]
        for sequence, rate_percent, period_from, period_to, notes in rate_rows:
            OLQuotationInstallmentRateRow.objects.create(
                installment_configuration=installment,
                sequence=sequence,
                description=notes,
                rate_percent=Decimal(rate_percent),
                paid_up_rate=Decimal("0.0000"),
                period_from=period_from,
                period_to=period_to,
                rate=Decimal(rate_percent),
                charge=Decimal("0.00"),
                notes=notes,
                created_by=actor,
                updated_by=actor,
            )

        OLQuotationFundAllocation.objects.create(
            quotation=quote,
            plan_configuration=plan_config,
            fund=balanced_fund,
            allocation_percentage=Decimal("60.0000"),
            allocation_amount=Decimal("3000000.00"),
            is_selected=True,
            metadata={},
            created_by=actor,
            updated_by=actor,
        )
        OLQuotationFundAllocation.objects.create(
            quotation=quote,
            plan_configuration=plan_config,
            fund=equity_fund,
            allocation_percentage=Decimal("40.0000"),
            allocation_amount=Decimal("2000000.00"),
            is_selected=True,
            metadata={},
            created_by=actor,
            updated_by=actor,
        )

        OLQuotationRiderSelection.objects.create(
            quotation=quote,
            rider=accidental_death_rider,
            plan_configuration=plan_config,
            rider_sum_assured=Decimal("2000000.00"),
            rider_term_years=5,
            beneficial_type=death_benefit_type,
            benefit_basis="FIXED",
            benefit_value=Decimal("2000000.00"),
            loading=Decimal("0.0000"),
            discount=Decimal("0.0000"),
            maximum_cap=None,
            premium_amount=None,
            is_selected=True,
            metadata={},
            created_by=actor,
            updated_by=actor,
        )
        OLQuotationRiderSelection.objects.create(
            quotation=quote,
            rider=premium_waiver_rider,
            plan_configuration=plan_config,
            rider_sum_assured=Decimal("5000000.00"),
            rider_term_years=5,
            beneficial_type=death_benefit_type,
            benefit_basis="FIXED",
            benefit_value=Decimal("5000000.00"),
            loading=Decimal("0.0000"),
            discount=Decimal("0.0000"),
            maximum_cap=None,
            premium_amount=None,
            is_selected=True,
            metadata={},
            created_by=actor,
            updated_by=actor,
        )

        OLQuotationBenefit.objects.create(
            quotation=quote,
            plan_configuration=plan_config,
            rider_selection=None,
            beneficial_type=maturity_benefit_type,
            code="MATURITY-1",
            name="Maturity Benefit",
            benefit_type="MATURITY",
            basis="FIXED",
            value=Decimal("5000000.00"),
            loading=Decimal("0.0000"),
            discount=Decimal("0.0000"),
            maximum_cap=None,
            sum_assured=Decimal("5000000.00"),
            premium_amount=Decimal("0.00"),
            is_selected=True,
            metadata={},
            created_by=actor,
            updated_by=actor,
        )
        OLQuotationBenefit.objects.create(
            quotation=quote,
            plan_configuration=plan_config,
            rider_selection=None,
            beneficial_type=death_benefit_type,
            code="DEATH-1",
            name="Death Benefit",
            benefit_type="DEATH",
            basis="FIXED",
            value=Decimal("5000000.00"),
            loading=Decimal("0.0000"),
            discount=Decimal("0.0000"),
            maximum_cap=None,
            sum_assured=Decimal("5000000.00"),
            premium_amount=Decimal("0.00"),
            is_selected=True,
            metadata={},
            created_by=actor,
            updated_by=actor,
        )

        OLQuotationPaymentDetail.objects.create(
            quotation=quote,
            payer=prospect,
            payment_method="BANK_TRANSFER",
            account_reference="0150298835400",
            payment_reference="OLQ-SEED-PAY-001",
            amount=None,
            currency="TZS",
            metadata={"channel": SEED_MARKER_VALUE},
            created_by=actor,
            updated_by=actor,
        )

        OLQuotationUnderwriting.objects.create(
            quotation=quote,
            medical_required=True,
            financial_underwriting_required=True,
            risk_class="STANDARD",
            health_answers={
                "chronic_conditions": "None",
                "recent_surgery": "None",
                "family_history": "None",
                "smoking_habit": "Current smoker",
            },
            medical_requirements=["MEDICAL_REPORT", "BLOOD_PRESSURE_CHECK"],
            declarations={
                "confirmed": True,
                "signed": True,
                "consent": "Yes",
                "agreed_at": quote_date.isoformat(),
            },
            notes="Standard underwriting completed for the seeded complete quotation.",
            created_by=actor,
            updated_by=actor,
        )

        OLQuotationBeneficiary.objects.create(
            quotation=quote,
            partner=linked_partner,
            name=f"{spouse_partner.first_name or 'Fatma'} {spouse_partner.surname or 'Sultan'}",
            relationship="SPOUSE",
            percentage=Decimal("60.0000"),
            identity_number="NIN-1997-0220-002",
            metadata={},
            created_by=actor,
            updated_by=actor,
        )
        OLQuotationBeneficiary.objects.create(
            quotation=quote,
            partner=child_partner,
            name=f"{child_partner.first_name or 'Zuri'} {child_partner.surname or 'Sultan'}",
            relationship="CHILD",
            percentage=Decimal("40.0000"),
            identity_number="NIN-2018-0510-003",
            metadata={},
            created_by=actor,
            updated_by=actor,
        )

        quote.wizard_step_completion = QuotationService.wizard_completion(quote)
        quote.updated_by = actor
        quote.save(update_fields=["wizard_step_completion", "updated_by", "updated_at"])
        return quote

    def _report(self, quote, *, finalized, document):
        self.stdout.write(self.style.SUCCESS(f"Seeded complete OL quotation: {quote.quote_number}"))
        self.stdout.write(f"  name: {quote.quote_name}")
        self.stdout.write(f"  status: {quote.status} (finalized={finalized})")
        self.stdout.write(f"  product: {quote.product_version.product.code if quote.product_version else None} v{quote.product_version.version_number if quote.product_version else None} -> plan {quote.plan_configurations.first().plan.code if quote.plan_configurations.first() and quote.plan_configurations.first().plan_id else None}")
        self.stdout.write(f"  partner: {quote.partner.partner_number if quote.partner_id else None}, agent: {quote.agent_partner.partner_number if quote.agent_partner_id else None}")
        self.stdout.write(
            f"  children -> products: {quote.products.count()}, plan_configs: {quote.plan_configurations.count()}, "
            f"members: {quote.members.count()}, installments: {quote.installment_configurations.count()}, "
            f"funds: {quote.fund_allocations.count()}, riders: {quote.rider_selections.count()}, "
            f"benefits: {quote.benefits.count()}, beneficiaries: {quote.beneficiaries.count()}, "
            f"documents: {quote.documents.count()}, versions: {quote.versions.count()}, events: {quote.events.count()}"
        )
        if finalized:
            try:
                summary = quote.financial_summary
                self.stdout.write(
                    f"  financial -> sum_assured: {summary.total_sum_assured}, total_premium: {summary.total_premium}, "
                    f"base_premium: {summary.base_premium}, rider_premium: {summary.total_rider_premium}, "
                    f"loading: {summary.total_loading}, tax: {summary.total_tax}, "
                    f"maturity: {summary.estimated_maturity_value}, recalc_required: {summary.recalculation_required}"
                )
            except Exception:
                pass
        if document is not None:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  document generated: id={document.pk} type={document.document_type} "
                    f"file={document.file_reference} html={document.html_reference}"
                )
            )
        if not finalized:
            self.stdout.write(
                self.style.WARNING("Quotation left as DRAFT (--no-finalize). Run again without that flag to calculate, finalize, and generate the document.")
            )
