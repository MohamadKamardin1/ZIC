"""Seed the final OL Loans release scenarios and structured proof payloads.

This command is intentionally additive and idempotent.  It first ensures the
Zanzibar OL parameter graph exists, then creates exactly ten loans under the
``OL-RELEASE`` natural-key namespace.  Requests, approvals, disbursements,
repayments, defaults, and offsets use the production services so the release
seed exercises the same accounting and audit seams as live operations.
"""

import json
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.front_office.receipts.config_models import CompanyBankAccount, ReceiptPaymentModeRule
from apps.governance.models import AuditLog
from apps.ol_loans.errors import LoanError
from apps.ol_loans.models import LoanStatus, OLLoan
from apps.ol_loans.services.approval_service import approve_loan, reject_loan
from apps.ol_loans.services.default_service import detect_loan_defaults, process_loan_offset
from apps.ol_loans.services.disbursement_service import disburse_loan
from apps.ol_loans.services.repayment_service import repay_loan
from apps.ol_loans.services.request_service import request_policy_loan
from apps.ol_parameters.models import OLLoanInterestControl, OLLoanSystemSetup, OLProduct
from apps.ol_policies.models import Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner

SEED_PREFIX = "OL-RELEASE"
RELEASE_DATE = date(2026, 1, 15)
AS_OF_DATE = date(2026, 8, 27)
CURRENCY = "TZS"


class Command(BaseCommand):
    help = "Seed exactly ten realistic OL Loan release scenarios and financial failure proofs."

    SCENARIOS = (
        ("ACTIVE-001", "standard active loan"),
        ("PARTIAL-001", "partially repaid"),
        ("SETTLED-001", "fully settled"),
        ("DEFAULTED-001", "defaulted overdue"),
        ("SURRENDER-001", "offset on surrender"),
        ("CLAIM-001", "offset on death claim"),
        ("FX-001", "multi-currency repayment"),
        ("REJECTED-001", "rejected request"),
        ("PENDING-001", "pending approval"),
        ("IMPORT-001", "CSV/imported loan"),
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            help="Print one machine-readable JSON result with scenario and proof payloads.",
        )
        parser.add_argument(
            "--skip-baseline",
            action="store_true",
            help="Do not run the complete Zanzibar OL seed; useful only when dependencies are already seeded.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not options["skip_baseline"]:
            call_command("seed_zanzibar_ol_complete", verbosity=0)
        actor = self._seed_actor()
        self._seed_payment_setup()
        product = self._seed_loan_parameters()

        loans = {}
        for suffix, _label in self.SCENARIOS:
            loans[suffix] = self._ensure_scenario(suffix, product, actor)

        failures = self._failure_proofs(loans, product, actor)
        seeded = list(
            OLLoan.objects.filter(loan_number__startswith=f"{SEED_PREFIX}-")
            .order_by("loan_number")
        )
        if len(seeded) != len(self.SCENARIOS):
            raise CommandError(
                f"Release seed expected exactly {len(self.SCENARIOS)} loans under {SEED_PREFIX}; found {len(seeded)}."
            )

        result = {
            "command": "seed_ol_loan_release",
            "as_of": AS_OF_DATE.isoformat(),
            "loan_count": len(seeded),
            "idempotent": True,
            "scenarios": [
                {
                    "scenario": label,
                    "loan_number": loan.loan_number,
                    "status": loan.status,
                    "currency": loan.currency,
                    "source_channel": loan.source_channel,
                    "principal_amount": str(loan.principal_amount),
                    "total_repaid": str(loan.total_repaid),
                    "outstanding_balance": str(loan.outstanding_balance),
                    "repayment_count": loan.repayments.count(),
                    "offset_count": loan.offsets.count(),
                    "audit_count": AuditLog.objects.filter(object_id=str(loan.pk)).count(),
                }
                for suffix, label in self.SCENARIOS
                for loan in [loans[suffix]]
            ],
            "failure_proofs": failures,
        }
        if options["json"]:
            self.stdout.write(json.dumps(result, sort_keys=True, default=str))
            return

        self.stdout.write(self.style.SUCCESS(f"Seeded/reused exactly {result['loan_count']} OL Loan release scenarios."))
        for row in result["scenarios"]:
            self.stdout.write(
                f"  {row['scenario']}: {row['loan_number']} -> {row['status']} "
                f"(outstanding {row['outstanding_balance']} {row['currency']})"
            )
        self.stdout.write("Failure proofs:")
        for key, proof in failures.items():
            self.stdout.write(f"  {key}: {proof['error_code']} — {proof['message']}")
        self.stdout.write(self.style.SUCCESS("The release seed is idempotent and did not flush or delete data."))

    def _seed_actor(self):
        user_model = get_user_model()
        actor, created = user_model.objects.get_or_create(
            username="ol_loan_release_operator",
            defaults={
                "email": "ol.loan.release@zic.tz",
                "first_name": "OL Loan",
                "last_name": "Release Operator",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        fields = []
        if not actor.is_staff:
            actor.is_staff = True
            fields.append("is_staff")
        if not actor.is_superuser:
            actor.is_superuser = True
            fields.append("is_superuser")
        if fields:
            fields.append("updated_at") if hasattr(actor, "updated_at") else None
            actor.save(update_fields=fields)
        return actor

    def _seed_payment_setup(self):
        rule, _ = ReceiptPaymentModeRule.objects.update_or_create(
            payment_mode="BANK_TRANSFER",
            defaults={
                "requires_reference": False,
                "requires_bank_account": True,
                "allows_bank_transfer": True,
                "is_active": True,
            },
        )
        rule.full_clean()
        rule.save(update_fields=["requires_reference", "requires_bank_account", "allows_bank_transfer", "is_active", "updated_at"])
        account, _ = CompanyBankAccount.objects.update_or_create(
            code="ZIC-OL-LOAN-RELEASE-TZS",
            defaults={
                "bank_name": "Zanzibar Commercial Bank",
                "account_name": "ZIC OL Loan Release Account",
                "account_number": "0199000001",
                "currency": CURRENCY,
                "is_default": True,
                "is_active": True,
            },
        )
        account.full_clean()
        account.save(update_fields=["bank_name", "account_name", "account_number", "currency", "is_default", "is_active", "updated_at"])

    def _seed_loan_parameters(self):
        product = OLProduct.objects.filter(code="OL_TERM_LIFE").first()
        if product is None:
            raise CommandError("The complete Zanzibar OL seed did not create OL_TERM_LIFE.")
        setup, _ = OLLoanSystemSetup.objects.update_or_create(
            code="ZIC_OL_TERM_LIFE_LOAN_SYSTEM",
            defaults={
                "name": "ZIC Term Life release loan setup",
                "description": "Release-tested policy loan configuration for Zanzibar Insurance Company.",
                "product": product,
                "plan": None,
                "effective_from": date(2026, 1, 1),
                "effective_to": None,
                "is_active": True,
                "allow_policy_loans": True,
                "loan_basis": "CASH_VALUE",
                "max_loan_percentage_of_cash_value": Decimal("80.00000000"),
                "min_loan_amount": Decimal("100000.00"),
                "max_loan_amount": Decimal("10000000.00"),
                "auto_approve_limit": None,
                "loan_currency": CURRENCY,
                "repayment_options": [
                    {
                        "code": "EQUAL_INSTALLMENT",
                        "label": "Equal monthly installment",
                        "schedule_method": "EQUAL_INSTALLMENT",
                        "term_months": [6, 12],
                        "enabled": True,
                    }
                ],
                "auto_deduct_from_benefits": True,
                "effect_on_claim": "DEDUCT_BALANCE",
                "effect_on_surrender": "DEDUCT_BALANCE",
                "effect_on_maturity": "DEDUCT_BALANCE",
                "require_approval": True,
            },
        )
        setup.full_clean()
        setup.save()
        interest, _ = OLLoanInterestControl.objects.update_or_create(
            code="ZIC_OL_TERM_LIFE_LOAN_INTEREST",
            defaults={
                "name": "ZIC Term Life release loan interest control",
                "description": "Release-tested monthly compound policy loan interest configuration.",
                "product": product,
                "plan": None,
                "effective_from": date(2026, 1, 1),
                "effective_to": None,
                "is_active": True,
                "interest_rate": Decimal("12.00000000"),
                "compounding_frequency": "MONTHLY",
                "interest_calculation_basis": "COMPOUND",
                "grace_period_days": 30,
                "penalty_period_days": 15,
                "penalty_interest_rate": Decimal("2.00000000"),
                "interest_suspension_rule": "",
                "capitalize_interest": True,
            },
        )
        interest.full_clean()
        interest.save()
        return product

    def _partner(self, suffix, name):
        partner, _ = Partner.objects.update_or_create(
            partner_number=f"{SEED_PREFIX}-P-{suffix}",
            defaults={
                "partner_type": "CLIENT",
                "partner_category": "INDIVIDUAL",
                "party_type": "INDIVIDUAL",
                "legal_name": name,
                "first_name": name.split()[0],
                "surname": " ".join(name.split()[1:]),
                "email": f"{suffix.lower()}@release.zic.tz",
                "mobile_number": "+255710000001",
                "phone": "+255710000001",
                "is_active": True,
                "status": "ACTIVE",
            },
        )
        return partner

    def _policy(self, suffix, product, *, cash_value="5000000.00", status="ACTIVE"):
        partner = self._partner(suffix, f"ZIC Release {suffix.title()}")
        quote, _ = OLQuotation.objects.update_or_create(
            quote_number=f"{SEED_PREFIX}-Q-{suffix}",
            defaults={
                "quote_name": f"ZIC OL release quote {suffix}",
                "quote_date": RELEASE_DATE,
                "partner": partner,
                "currency": CURRENCY,
            },
        )
        proposal, _ = OLProposal.objects.update_or_create(
            proposal_number=f"{SEED_PREFIX}-PROP-{suffix}",
            defaults={
                "quotation": quote,
                "status": "CONVERTED",
                "partner": partner,
                "partner_name_snapshot": partner.legal_name,
                "currency": CURRENCY,
                "prospect_snapshot": {"name": partner.legal_name, "identity_number": f"NIDA-{suffix}"},
                "plans_snapshot": [{"product_code": product.code, "product_name": product.name}],
                "financial_summary_snapshot": {"total_sum_assured": "50000000.00", "total_premium": "250000.00"},
                "source_channel": "SYSTEM",
            },
        )
        policy, _ = Policy.objects.update_or_create(
            policy_number=f"{SEED_PREFIX}-POL-{suffix}",
            defaults={
                "proposal_ref": proposal,
                "partner": partner,
                "product_plan_ref": product.code,
                "currency": CURRENCY,
                "sum_assured": Decimal("50000000.00"),
                "premium_amount": Decimal("250000.00"),
                "premium_frequency": "ANNUALLY",
                "term_years": 10,
                "risk_commencement_date": RELEASE_DATE,
                "maturity_date": date(2036, 1, 15),
                "status": status,
                "contract_snapshot": {
                    "cash_value": cash_value,
                    "product_id": str(product.pk),
                    "product_code": product.code,
                    "plans": [{"product_id": str(product.pk), "product_code": product.code}],
                },
            },
        )
        return policy

    def _ensure_requested(self, suffix, product, actor, *, amount="1000000.00", source_channel="SYSTEM"):
        policy = self._policy(suffix, product)
        result = request_policy_loan(
            policy.pk,
            requested_amount=Decimal(amount),
            term_months=12,
            repayment_mode="EQUAL_INSTALLMENT",
            reason=f"ZIC OL Loans release scenario: {suffix}.",
            idempotency_key=f"{SEED_PREFIX}-REQUEST-{suffix}",
            actor=actor,
            source_channel=source_channel,
            as_of=RELEASE_DATE,
        )
        loan = result.loan
        deterministic_number = f"{SEED_PREFIX}-LOAN-{suffix}"
        if loan.loan_number != deterministic_number:
            loan.loan_number = deterministic_number
            loan.updated_by = actor
            loan.save(update_fields=["loan_number", "updated_by", "updated_at"])
        return loan

    def _approved_disbursed(self, suffix, product, actor, *, amount="1000000.00", source_channel="SYSTEM", disbursement_date=RELEASE_DATE):
        loan = self._ensure_requested(suffix, product, actor, amount=amount, source_channel=source_channel)
        if loan.status == LoanStatus.REQUESTED and loan.approval_required:
            approve_loan(
                loan.pk,
                actor=actor,
                reason="Approved as part of the OL Loans release scenario matrix.",
                source_channel=source_channel,
            )
        loan.refresh_from_db()
        disburse_loan(
            loan.pk,
            payment_mode="BANK_TRANSFER",
            bank_account_code="ZIC-OL-LOAN-RELEASE-TZS",
            as_of=disbursement_date,
            reason=f"Disbursed OL Loans release scenario {suffix}.",
            idempotency_key=f"{SEED_PREFIX}-DISBURSE-{suffix}",
            actor=actor,
            source_channel=source_channel,
        )
        return OLLoan.objects.get(pk=loan.pk)

    def _ensure_scenario(self, suffix, product, actor):
        if suffix == "REJECTED-001":
            loan = self._ensure_requested(suffix, product, actor, amount="1000000.00")
            if loan.status == LoanStatus.REQUESTED:
                reject_loan(
                    loan.pk,
                    reason="Release scenario rejected after affordability review.",
                    actor=actor,
                    source_channel="SYSTEM",
                )
            return OLLoan.objects.get(pk=loan.pk)
        if suffix == "PENDING-001":
            return self._ensure_requested(suffix, product, actor, amount="2500000.00")

        source = "IMPORT" if suffix == "IMPORT-001" else "SYSTEM"
        loan = self._approved_disbursed(
            suffix,
            product,
            actor,
            source_channel=source,
            disbursement_date=date(2026, 8, 1) if suffix == "SETTLED-001" else RELEASE_DATE,
        )
        if suffix == "PARTIAL-001" and loan.status == LoanStatus.ACTIVE:
            repay_loan(
                loan.pk,
                amount=Decimal("250000.00"),
                currency=CURRENCY,
                exchange_rate=Decimal("1.00000000"),
                reason="Partial repayment for OL Loans release scenario.",
                payment_date=date(2026, 5, 15),
                idempotency_key=f"{SEED_PREFIX}-REPAY-{suffix}",
                actor=actor,
                source_channel="SYSTEM",
            )
        elif suffix == "SETTLED-001" and loan.status == LoanStatus.ACTIVE:
            repay_loan(
                loan.pk,
                amount=loan.outstanding_balance,
                currency=CURRENCY,
                exchange_rate=Decimal("1.00000000"),
                reason="Full settlement for OL Loans release scenario.",
                payment_date=date(2026, 8, 1),
                idempotency_key=f"{SEED_PREFIX}-REPAY-{suffix}",
                actor=actor,
                source_channel="SYSTEM",
            )
        elif suffix == "DEFAULTED-001" and loan.status in {LoanStatus.ACTIVE, LoanStatus.PARTIALLY_REPAID}:
            detect_loan_defaults(
                as_of=AS_OF_DATE,
                actor=actor,
                source_channel="BATCH",
                correlation_id=f"{SEED_PREFIX}-DEFAULT-DETECTION",
                loan_id=loan.pk,
            )
        elif suffix == "SURRENDER-001" and not loan.offsets.filter(source_type="SURRENDER", source_id=f"{SEED_PREFIX}-SURR-PAYOUT").exists():
            process_loan_offset(
                loan,
                "SURRENDER",
                f"{SEED_PREFIX}-SURR-PAYOUT",
                Decimal("400000.00"),
                actor=actor,
                source_channel="SYSTEM",
                reason="Surrender proceeds offset for OL Loans release scenario.",
            )
        elif suffix == "CLAIM-001" and not loan.offsets.filter(source_type="CLAIM", source_id=f"{SEED_PREFIX}-CLAIM-PAYOUT").exists():
            process_loan_offset(
                loan,
                "CLAIM",
                f"{SEED_PREFIX}-CLAIM-PAYOUT",
                Decimal("600000.00"),
                actor=actor,
                source_channel="SYSTEM",
                reason="Death claim proceeds offset for OL Loans release scenario.",
            )
        elif suffix == "FX-001" and not loan.repayments.filter(idempotency_key=f"{SEED_PREFIX}-REPAY-{suffix}").exists():
            repay_loan(
                loan.pk,
                amount=Decimal("250000.00"),
                currency="USD",
                exchange_rate=Decimal("2.00000000"),
                reason="Approved FX repayment for OL Loans release scenario.",
                payment_date=date(2026, 5, 15),
                idempotency_key=f"{SEED_PREFIX}-REPAY-{suffix}",
                actor=actor,
                source_channel="SYSTEM",
            )
        return OLLoan.objects.get(pk=loan.pk)

    def _capture_failure(self, operation, expected_code):
        try:
            with transaction.atomic():
                operation()
        except LoanError as exc:
            return {
                "status": "caught",
                "expected_error_code": expected_code,
                "error_code": exc.error_code,
                "message": str(exc),
                "field_errors": exc.field_errors or {},
                "details": exc.details or {},
                "resolution_steps": exc.resolution_steps or [],
            }
        raise CommandError(f"Failure proof expected {expected_code} but the operation succeeded.")

    def _failure_proofs(self, loans, product, actor):
        ineligible_policy = self._policy("FAIL-INELIGIBLE", product, status="CANCELLED")
        limit_policy = self._policy("FAIL-LIMIT", product, cash_value="500000.00")
        proofs = {
            "ineligible_policy": self._capture_failure(
                lambda: request_policy_loan(
                    ineligible_policy.pk,
                    requested_amount=Decimal("100000.00"),
                    term_months=12,
                    repayment_mode="EQUAL_INSTALLMENT",
                    reason="Expected ineligible policy proof.",
                    idempotency_key=f"{SEED_PREFIX}-FAIL-INELIGIBLE",
                    actor=actor,
                    source_channel="SYSTEM",
                    as_of=RELEASE_DATE,
                ),
                "LOAN_INELIGIBLE",
            ),
            "exceeds_cash_value_limit": self._capture_failure(
                lambda: request_policy_loan(
                    limit_policy.pk,
                    requested_amount=Decimal("1000000.00"),
                    term_months=12,
                    repayment_mode="EQUAL_INSTALLMENT",
                    reason="Expected cash value limit proof.",
                    idempotency_key=f"{SEED_PREFIX}-FAIL-LIMIT",
                    actor=actor,
                    source_channel="SYSTEM",
                    as_of=RELEASE_DATE,
                ),
                "LOAN_EXCEEDS_LIMIT",
            ),
            "overpayment": self._capture_failure(
                lambda: repay_loan(
                    loans["PARTIAL-001"].pk,
                    amount=loans["PARTIAL-001"].outstanding_balance + Decimal("1.00"),
                    currency=CURRENCY,
                    exchange_rate=Decimal("1.00000000"),
                    reason="Expected overpayment proof.",
                    payment_date=AS_OF_DATE,
                    idempotency_key=f"{SEED_PREFIX}-FAIL-OVERPAYMENT",
                    actor=actor,
                    source_channel="SYSTEM",
                ),
                "LOAN_REPAYMENT_OVERPAYMENT",
            ),
            "offset_on_already_settled": self._capture_failure(
                lambda: process_loan_offset(
                    loans["SETTLED-001"],
                    "CLAIM",
                    f"{SEED_PREFIX}-SETTLED-CLAIM",
                    Decimal("500000.00"),
                    actor=actor,
                    source_channel="SYSTEM",
                    reason="Expected settled-loan offset proof.",
                ),
                "LOAN_OFFSET_INVALID",
            ),
        }
        duplicate = disburse_loan(
            loans["ACTIVE-001"].pk,
            payment_mode="BANK_TRANSFER",
            bank_account_code="ZIC-OL-LOAN-RELEASE-TZS",
            as_of=RELEASE_DATE,
            reason="Expected idempotent duplicate disbursement proof.",
            idempotency_key=f"{SEED_PREFIX}-DISBURSE-ACTIVE-001-RETRY",
            actor=actor,
            source_channel="SYSTEM",
        )
        proofs["duplicate_disbursement"] = {
            "status": "idempotent_replay",
            "error_code": "IDEMPOTENT_REPLAY",
            "message": "Duplicate disbursement returned the existing immutable disbursement without creating a second release.",
            "created": duplicate.changed,
            "disbursement_id": str(duplicate.disbursement.pk),
            "schedule_count": len(duplicate.schedules),
            "resolution_steps": [
                "Reuse the original disbursement result when a network retry is detected.",
                "Do not create a second financial release for the same loan.",
            ],
        }
        return proofs
