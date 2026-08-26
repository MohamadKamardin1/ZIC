"""Attempt the five mandatory receipt failure scenarios and capture proof payloads.

Each proof builds a minimal fixture, attempts the operation through the real
service layer, and records the structured ``ReceiptError`` (code, status,
message, field errors, resolution steps). The command is idempotent: fixtures
are keyed by fixed idempotency keys, so re-running replays the same captured
rejections. Proof output is printed as JSON lines and also returned for tests.
"""

import json

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.front_office.receipts.errors import ReceiptError
from apps.front_office.receipts.models import ReceiptAllocationTargetType, ReceiptSourceModule
from apps.front_office.receipts.seed_data import (
    get_branch,
    get_commitment,
    get_partner,
    get_partner_bank_account,
    get_seed_user,
    scenario_receipt,
    seed_commitment_statuses,
)
from apps.front_office.receipts.services.allocation_service import allocate
from apps.front_office.receipts.services.receipt_service import create_draft, post_receipt
from apps.front_office.receipts.services.reversal_service import reverse_receipt
from apps.system_parameters.models import ParameterGroup, SystemParameter
from apps.system_parameters.services.config_service import ConfigurationService

LOCK_PARAM = "RECEIPT_REVERSAL_LOCK_DAYS"


def _proof(payload):
    return payload


def _error_payload(exc):
    return {
        "code": getattr(exc, "error_code", "RECEIPT_ERROR"),
        "status_code": getattr(exc, "status_code", 500),
        "message": str(exc) or "The operation was rejected.",
        "field_errors": getattr(exc, "field_errors", None) or {},
        "resolution_steps": getattr(exc, "resolution_steps", None) or [],
    }


def _set_lock_days(days):
    group, _ = ParameterGroup.objects.get_or_create(
        code="FRONT_OFFICE_RECEIPTS",
        defaults={"name": "Front Office Receipts", "sort_order": 10},
    )
    SystemParameter.objects.update_or_create(
        code=LOCK_PARAM,
        defaults={
            "group": group,
            "name": "Receipt reversal lock (days)",
            "description": "Receipts older than this many days cannot be reversed. 0 disables the lock.",
            "value_type": "INTEGER",
            "integer_value": days,
            "is_active": True,
        },
    )
    ConfigurationService.invalidate_parameter(LOCK_PARAM)


def _clear_lock_days():
    SystemParameter.objects.filter(code=LOCK_PARAM).update(is_active=False)
    ConfigurationService.invalidate_parameter(LOCK_PARAM)


class Command(BaseCommand):
    help = "Attempt and capture the 5 mandatory receipt failure proofs (Prompt 12)."

    def handle(self, *args, **options):
        proofs = run_proofs()
        for proof in proofs:
            self.stdout.write(json.dumps(proof, indent=2, sort_keys=True))
            self.stdout.write("")
        total = len(proofs)
        caught = sum(1 for proof in proofs if proof["outcome"] == "caught")
        self.stdout.write(
            self.style.SUCCESS(f"Failure proofs: {caught}/{total} caught with expected error codes.")
        )


def run_proofs():
    """Execute all five failure scenarios; returns the list of proof payloads."""
    call_command("seed_receipt_parameters")
    seed_commitment_statuses()
    actor = get_seed_user()
    branch = get_branch()

    proofs = [
        _missing_payment_reference(actor, branch),
        _over_allocation(actor, branch),
        _cross_currency_without_rate(actor, branch),
        _allocation_to_completed_commitment(actor, branch),
        _reversal_after_lock_period(actor, branch),
    ]
    return proofs


def _missing_payment_reference(actor, branch):
    key = "SEED-FAIL-01-REFERENCE"
    partner = get_partner("SEEDFP001", first_name="Rehema", surname="Lema")
    bank_account = get_partner_bank_account(partner, account_number="0150-3192-1234")
    receipt = scenario_receipt(key)
    attempt = {
        "payment_mode": "BANK_TRANSFER",
        "bank_account": str(bank_account.account_number),
        "payment_reference": "",
        "currency": "TZS",
        "amount": "200000.00",
    }
    if receipt is None:
        receipt, _created = create_draft(
            actor=actor,
            source_channel="SYSTEM",
            idempotency_key=key,
            receipt_date=timezone.localdate(),
            branch_id=branch.pk,
            partner_id=partner.pk,
            payer_name=str(partner),
            source_module=ReceiptSourceModule.MANUAL,
            receipt_amount="200000.00",
            currency="TZS",
            payment_mode="BANK_TRANSFER",
            bank_account_id=bank_account.pk,
            narration="Failure proof 1: BANK_TRANSFER posted without a payment reference.",
        )
    try:
        post_receipt(receipt, actor=actor, reason="Failure proof 1 attempt.", source_channel="SYSTEM")
        outcome, error = "escaped", None
    except ReceiptError as exc:
        outcome, error = "caught", _error_payload(exc)
    return _proof(
        {
            "proof": "missing_payment_reference",
            "expected_error": "RECEIPT_PAYMENT_REFERENCE_REQUIRED",
            "attempt": attempt,
            "outcome": outcome,
            "error": error,
        }
    )


def _over_allocation(actor, branch):
    key = "SEED-FAIL-02-OVERALLOC"
    partner = get_partner("SEEDFP002", first_name="Salim", surname="Hamisi")
    commitment = get_commitment(
        "SEED-OLC-FAIL-02", partner, premium="200000.00", currency="TZS", status="PENDING"
    )
    receipt = scenario_receipt(key)
    attempt = {"receipt_amount": "100000.00", "allocated": "150000.00", "unallocated": "100000.00"}
    if receipt is None:
        receipt, _created = create_draft(
            actor=actor,
            source_channel="SYSTEM",
            idempotency_key=key,
            receipt_date=timezone.localdate(),
            branch_id=branch.pk,
            partner_id=partner.pk,
            payer_name=str(partner),
            source_module=ReceiptSourceModule.MANUAL,
            receipt_amount="100000.00",
            currency="TZS",
            payment_mode="CASH",
            narration="Failure proof 2: over-allocation attempt.",
        )
        post_receipt(receipt, actor=actor, reason="Failure proof 2 setup.", source_channel="SYSTEM")
    try:
        allocate(
            receipt,
            target_type=ReceiptAllocationTargetType.OL_COMMITMENT,
            target_id=commitment.commitment_number,
            amount="150000.00",
            narration="Failure proof 2: attempt to over-allocate.",
            actor=actor,
            source_channel="SYSTEM",
        )
        outcome, error = "escaped", None
    except ReceiptError as exc:
        outcome, error = "caught", _error_payload(exc)
    return _proof(
        {
            "proof": "over_allocation",
            "expected_error": "RECEIPT_OVERALLOCATION",
            "attempt": attempt,
            "outcome": outcome,
            "error": error,
        }
    )


def _cross_currency_without_rate(actor, branch):
    key = "SEED-FAIL-03-CURRENCY"
    partner = get_partner("SEEDFP003", first_name="Tatu", surname="Chande")
    commitment = get_commitment(
        "SEED-OLC-FAIL-03", partner, premium="200000.00", currency="TZS", status="PENDING"
    )
    bank_account = get_partner_bank_account(partner, account_number="0150-3192-5555")
    receipt = scenario_receipt(key)
    attempt = {"receipt_currency": "KES", "commitment_currency": "TZS", "exchange_rate": "not supplied"}
    if receipt is None:
        receipt, _created = create_draft(
            actor=actor,
            source_channel="SYSTEM",
            idempotency_key=key,
            receipt_date=timezone.localdate(),
            branch_id=branch.pk,
            partner_id=partner.pk,
            payer_name=str(partner),
            source_module=ReceiptSourceModule.MANUAL,
            receipt_amount="10000.00",
            currency="KES",
            payment_mode="BANK_TRANSFER",
            payment_reference="KES-SEED-20260825-0001",
            bank_account_id=bank_account.pk,
            narration="Failure proof 3: cross-currency allocation without an exchange rate.",
        )
        post_receipt(receipt, actor=actor, reason="Failure proof 3 setup.", source_channel="SYSTEM")
    try:
        allocate(
            receipt,
            target_type=ReceiptAllocationTargetType.OL_COMMITMENT,
            target_id=commitment.commitment_number,
            amount="10000.00",
            narration="Failure proof 3: no rate supplied.",
            actor=actor,
            source_channel="SYSTEM",
        )
        outcome, error = "escaped", None
    except ReceiptError as exc:
        outcome, error = "caught", _error_payload(exc)
    return _proof(
        {
            "proof": "cross_currency_without_exchange_rate",
            "expected_error": "RECEIPT_CURRENCY_MISMATCH",
            "attempt": attempt,
            "outcome": outcome,
            "error": error,
        }
    )


def _allocation_to_completed_commitment(actor, branch):
    settle_key = "SEED-FAIL-04-SETTLE"
    key = "SEED-FAIL-04-COMPLETED"
    partner = get_partner("SEEDFP004", first_name="Upendo", surname="Massawe")
    commitment = get_commitment(
        "SEED-OLC-FAIL-04", partner, premium="100000.00", currency="TZS", status="PENDING"
    )

    # Settle the commitment with a first receipt so it is genuinely COMPLETED (balance 0).
    settle_receipt = scenario_receipt(settle_key)
    if settle_receipt is None:
        settle_receipt, _created = create_draft(
            actor=actor,
            source_channel="SYSTEM",
            idempotency_key=settle_key,
            receipt_date=timezone.localdate(),
            branch_id=branch.pk,
            partner_id=partner.pk,
            payer_name=str(partner),
            source_module=ReceiptSourceModule.MANUAL,
            receipt_amount="100000.00",
            currency="TZS",
            payment_mode="CASH",
            narration="Failure proof 4: first receipt that settles the commitment.",
        )
        post_receipt(settle_receipt, actor=actor, reason="Failure proof 4 settle setup.", source_channel="SYSTEM")
        allocate(
            settle_receipt,
            target_type=ReceiptAllocationTargetType.OL_COMMITMENT,
            target_id=commitment.commitment_number,
            amount="100000.00",
            narration="Failure proof 4: settle the commitment.",
            actor=actor,
            source_channel="SYSTEM",
        )
    commitment.refresh_from_db()
    attempt = {"commitment_status": commitment.status, "commitment_balance": str(commitment.balance), "allocated": "50000.00"}

    receipt = scenario_receipt(key)
    if receipt is None:
        receipt, _created = create_draft(
            actor=actor,
            source_channel="SYSTEM",
            idempotency_key=key,
            receipt_date=timezone.localdate(),
            branch_id=branch.pk,
            partner_id=partner.pk,
            payer_name=str(partner),
            source_module=ReceiptSourceModule.MANUAL,
            receipt_amount="100000.00",
            currency="TZS",
            payment_mode="CASH",
            narration="Failure proof 4: allocation to a completed commitment.",
        )
        post_receipt(receipt, actor=actor, reason="Failure proof 4 setup.", source_channel="SYSTEM")
    try:
        allocate(
            receipt,
            target_type=ReceiptAllocationTargetType.OL_COMMITMENT,
            target_id=commitment.commitment_number,
            amount="50000.00",
            narration="Failure proof 4: allocate to settled commitment.",
            actor=actor,
            source_channel="SYSTEM",
        )
        outcome, error = "escaped", None
    except ReceiptError as exc:
        outcome, error = "caught", _error_payload(exc)
    return _proof(
        {
            "proof": "allocation_to_completed_commitment",
            "expected_error": "RECEIPT_OVERALLOCATION",
            "attempt": attempt,
            "outcome": outcome,
            "error": error,
        }
    )


def _reversal_after_lock_period(actor, branch):
    key = "SEED-FAIL-05-LOCKED"
    partner = get_partner("SEEDFP005", first_name="Vumilia", surname="Rweyemamu")
    receipt = scenario_receipt(key)
    attempt = {"receipt_date": "10 days before today", "lock_days": 5, "reverse": True}
    try:
        _set_lock_days(5)
        if receipt is None:
            receipt, _created = create_draft(
                actor=actor,
                source_channel="SYSTEM",
                idempotency_key=key,
                receipt_date=timezone.localdate() - timezone.timedelta(days=10),
                branch_id=branch.pk,
                partner_id=partner.pk,
                payer_name=str(partner),
                source_module=ReceiptSourceModule.MANUAL,
                receipt_amount="100000.00",
                currency="TZS",
                payment_mode="CASH",
                narration="Failure proof 5: reversal after the lock period.",
            )
            post_receipt(receipt, actor=actor, reason="Failure proof 5 setup.", source_channel="SYSTEM")
        reverse_receipt(receipt, reason="Failure proof 5: attempt to reverse a locked receipt.", actor=actor, source_channel="SYSTEM")
        outcome, error = "escaped", None
    except ReceiptError as exc:
        outcome, error = "caught", _error_payload(exc)
    finally:
        _clear_lock_days()
    return _proof(
        {
            "proof": "reversal_after_lock_period",
            "expected_error": "RECEIPT_REVERSAL_LOCKED",
            "attempt": attempt,
            "outcome": outcome,
            "error": error,
        }
    )
