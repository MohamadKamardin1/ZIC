"""Shared fixtures for the Prompt 12 release commands.

Used by ``seed_receipt_scenarios``, ``receipt_failure_proofs`` and
``verify_br03_release`` so the three commands build on one consistent, idempotent
set of reference records (partners, branches, commitment statuses, proposals,
exchange rates, payment-mode aliases).
"""

import csv
import io
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.front_office.receipts.config_models import ReceiptPaymentModeRule
from apps.front_office.receipts.models import ExchangeRate, Receipt
from apps.ol_commitments.models import OLCommitment
from apps.ol_parameters.models import OLCommitmentStatus
from apps.ol_proposals.models import OLProposal, OLProposalPlanConfig
from apps.ol_proposals.services.first_premium_service import link_first_premium_commitment
from apps.ol_quotations.models import OLQuotation, OLQuotationVersion
from apps.ordinary_life.models import OLPlan, OLProduct, OLProductVersion
from apps.partner_onboarding.models import Branch
from apps.partners.models import Partner, PartnerBankAccount

User = get_user_model()

COMMITMENT_STATUS_SEEDS = (
    ("PENDING", "Pending", 10, False),
    ("PARTIALLY_PAID", "Partially paid", 20, False),
    ("COMPLETED", "Completed", 30, True),
)


def seed_commitment_statuses():
    """Idempotently seed the commitment status catalog the allocation engine reads."""
    for code, name, order, terminal in COMMITMENT_STATUS_SEEDS:
        OLCommitmentStatus.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "applies_to": "COMMITMENT",
                "display_order": order,
                "is_terminal": terminal,
                "is_active": True,
            },
        )


def get_seed_user(username="seed_release_ops"):
    return User.objects.get_or_create(
        username=username,
        defaults={"email": f"{username}@zic.tz", "is_staff": True},
    )[0]


def get_branch(code="DAR", name="Dar es Salaam"):
    return Branch.objects.get_or_create(code=code, defaults={"name": name})[0]


def get_partner(partner_number, **overrides):
    defaults = {
        "partner_type": "INDIVIDUAL",
        "party_type": "INDIVIDUAL",
        "first_name": "Neema",
        "surname": "Mushi",
        "email": f"{partner_number.lower()}@zic.tz",
        "mobile_number": "255700000111",
        "is_active": True,
        "status": "ACTIVE",
    }
    defaults.update(overrides)
    return Partner.objects.get_or_create(partner_number=partner_number, defaults=defaults)[0]


def get_commitment(commitment_number, partner, *, premium, currency="TZS", status="PENDING", **overrides):
    """Idempotent OLCommitment fixture; updates the premium when already present."""
    commitment, created = OLCommitment.objects.get_or_create(
        commitment_number=commitment_number,
        defaults={
            "source_type": "MANUAL",
            "currency": currency,
            "due_date": timezone.localdate() + timedelta(days=10),
            "premium_amount": premium,
            "status": status,
            "partner": partner,
            "partner_name_snapshot": str(partner),
            "source_channel": "SYSTEM",
        },
    )
    if not created:
        fields = {
            "currency": currency,
            "due_date": timezone.localdate() + timedelta(days=10),
            "premium_amount": premium,
            "status": status,
            "partner": partner,
            "partner_name_snapshot": str(partner),
        }
        fields.update(overrides)
        for key, value in fields.items():
            setattr(commitment, key, value)
        commitment.save()
    return commitment


def make_proposal(proposal_number, premium_amount, partner, currency="TZS"):
    """Idempotent payment-ready proposal with a resolvable first-premium amount."""
    existing = OLProposal.objects.filter(proposal_number=proposal_number).first()
    if existing is not None:
        return existing

    quotation, _ = OLQuotation.objects.get_or_create(
        quote_number=f"Q-SEED-{proposal_number}", defaults={"currency": currency}
    )
    quotation.partner = partner
    quotation.partner_verified = True
    quotation.current_version_number = 1
    quotation.save()
    version, _ = OLQuotationVersion.objects.get_or_create(
        quotation=quotation, version_number=1, defaults={"status": "FINALIZED"}
    )
    proposal = OLProposal.objects.create(
        quotation=quotation,
        quotation_version=version,
        proposal_number=proposal_number,
        status="AWAITING_FIRST_PREMIUM",
        partner=partner,
        partner_name_snapshot=str(partner),
        currency=currency,
        expiry_date=date.today() + timedelta(days=30),
        payment_ready=True,
        financial_summary_snapshot={"total_premium": str(premium_amount)},
    )
    _attach_plan_config(proposal, premium_amount)
    return proposal


def _attach_plan_config(proposal, premium_amount):
    """Carry a selected plan configuration so BR-03 conversion can mirror the legacy policy.

    ``convert_proposal_to_policy`` reads the selected plan config for the product
    version and legacy quotation mirror, so the fixture must carry one.
    """
    product, _ = OLProduct.objects.get_or_create(code="OL_TERM", defaults={"name": "Term Life"})
    product_version, _ = OLProductVersion.objects.get_or_create(
        product=product,
        version_number=1,
        defaults={"effective_from": date.today() - timedelta(days=30)},
    )
    plan, _ = OLPlan.objects.get_or_create(
        product_version=product_version,
        code="TERM-SEED",
        defaults={
            "name": "Seeded Term Plan",
            "minimum_sum_assured": "10000.00",
            "maximum_sum_assured": "100000000.00",
        },
    )
    OLProposalPlanConfig.objects.create(
        proposal=proposal,
        product_version=product_version,
        plan=plan,
        plan_name_snapshot=plan.name,
        base_sum_assured=Decimal(str(premium_amount)) * 10,
        term_years=20,
        payment_period_years=20,
        premium_frequency="ANNUAL",
        quote_basis="SUM_ASSURED",
        premium_factor="NONE",
        premium_amount=Decimal(str(premium_amount)),
        is_selected=True,
    )


def link_first_premium(proposal, actor=None):
    """Idempotent first-premium commitment linkage returning ``(commitment, created)``."""
    if proposal.first_premium_commitment_id:
        return proposal.first_premium_commitment, False
    return link_first_premium_commitment(proposal=proposal, actor=actor, source_channel="SYSTEM")


def get_partner_bank_account(partner, account_number="0150-3192-9999"):
    return PartnerBankAccount.objects.get_or_create(
        partner=partner,
        account_number=account_number,
        defaults={
            "bank_name": "CRDB Bank PLC",
            "branch_name": "Head Office",
            "account_name": f"{partner} — Receipts",
            "currency": "TZS",
            "is_primary": True,
            "is_verified": True,
        },
    )[0]


def ensure_mobile_money_rule():
    """Add the ``M-PESA`` payment-mode rule alias so mobile-money receipts post.

    The receipt stores mobile-money mode as ``M-PESA`` (the choice value) while
    the baseline parameter command keys the rule ``MOBILE_MONEY``; the alias
    bridges that gap without changing the baseline seed.
    """
    ReceiptPaymentModeRule.objects.update_or_create(
        payment_mode="M-PESA",
        defaults={
            "requires_reference": True,
            "requires_bank_account": False,
            "allows_mobile_money": True,
            "min_amount": "1000.00",
            "max_amount": "3000000.00",
            "is_active": True,
        },
    )


def ensure_exchange_rate(from_currency, to_currency, rate, effective_date=None):
    ExchangeRate.objects.update_or_create(
        from_currency=from_currency,
        to_currency=to_currency,
        effective_date=effective_date or timezone.localdate(),
        defaults={"rate": rate, "source": "SEED", "is_active": True},
    )


def scenario_receipt(idempotency_key):
    return Receipt.objects.filter(idempotency_key=idempotency_key).first()


def make_import_csv(rows, columns=None):
    from apps.front_office.receipts.services.import_service import IMPORT_COLUMNS

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns or IMPORT_COLUMNS)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return SimpleUploadedFile(
        "seed_receipts.csv", buf.getvalue().encode("utf-8"), content_type="text/csv"
    )
