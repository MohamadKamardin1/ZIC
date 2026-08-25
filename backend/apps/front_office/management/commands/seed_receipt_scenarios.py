"""Seed exactly ten realistic receipt scenarios (Prompt 12) idempotently.

Scenarios exercise different write approaches:
  - direct service writes (create / post / allocate / reverse / cancel)
  - the proposals first-premium seam (``link_first_premium_commitment``)
  - explicit multi-currency allocation through the exchange-rate table
  - the bulk CSV import pipeline (dry-run then commit)

Re-running the command is a no-op: every scenario is keyed by an idempotency
key (or a narration marker for the import path) and is skipped once present.
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.front_office.receipts.models import (
    Receipt,
    ReceiptAllocationTargetType,
    ReceiptSourceModule,
)
from apps.front_office.receipts.seed_data import (
    ensure_exchange_rate,
    ensure_mobile_money_rule,
    get_branch,
    get_commitment,
    get_partner,
    get_partner_bank_account,
    get_seed_user,
    link_first_premium,
    make_import_csv,
    make_proposal,
    scenario_receipt,
    seed_commitment_statuses,
)
from apps.front_office.receipts.services.allocation_service import allocate
from apps.front_office.receipts.services.import_service import commit_batch, dry_run
from apps.front_office.receipts.services.receipt_service import create_draft, post_receipt
from apps.front_office.receipts.services.reversal_service import cancel_draft, reverse_receipt

ZERO = "0.00"


class Command(BaseCommand):
    help = "Seed 10 realistic Front Office Receipts scenarios idempotently (Prompt 12)."

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("seed_receipt_parameters")
        call_command("seed_receipt_permissions")
        seed_commitment_statuses()
        actor = get_seed_user()
        branch = get_branch()
        ensure_mobile_money_rule()
        ensure_exchange_rate("USD", "TZS", "2500.00000000")

        manifest = []

        manifest.append(self._draft_manual(actor, branch))
        manifest.append(self._posted_unallocated_cash(actor, branch))
        manifest.append(self._posted_partially_allocated(actor, branch))
        manifest.append(self._first_premium_full(actor, branch))
        manifest.append(self._bank_transfer_reference(actor, branch))
        manifest.append(self._mobile_money(actor, branch))
        manifest.append(self._multi_currency(actor, branch))
        manifest.append(self._reversed(actor, branch))
        manifest.append(self._cancelled_draft(actor, branch))
        manifest.append(self._csv_import(actor, branch))

        self._render(manifest)

    # ------------------------------------------------------------------ #
    # Scenarios
    # ------------------------------------------------------------------ #

    def _draft_manual(self, actor, branch):
        key = "SEED-RCT-01-DRAFT"
        receipt = scenario_receipt(key)
        if receipt is not None:
            return self._entry("1", "Draft manual", receipt, "already present")
        partner = get_partner("SEEDP001", first_name="Asha", surname="Mollel")
        receipt, _created = create_draft(
            actor=actor,
            source_channel="MANUAL",
            idempotency_key=key,
            receipt_date=timezone.localdate(),
            branch_id=branch.pk,
            partner_id=partner.pk,
            payer_name=str(partner),
            source_module=ReceiptSourceModule.MANUAL,
            receipt_amount="250000.00",
            currency="TZS",
            payment_mode="CASH",
            narration="Scenario 1: draft manual receipt awaiting money confirmation.",
        )
        return self._entry("1", "Draft manual", receipt, "created")

    def _posted_unallocated_cash(self, actor, branch):
        key = "SEED-RCT-02-POSTED"
        receipt = scenario_receipt(key)
        if receipt is not None:
            return self._entry("2", "Posted unallocated cash", receipt, "already present")
        partner = get_partner("SEEDP002", first_name="Baraka", surname="Mwinjuma")
        receipt, _created = create_draft(
            actor=actor,
            source_channel="SYSTEM",
            idempotency_key=key,
            receipt_date=timezone.localdate(),
            branch_id=branch.pk,
            partner_id=partner.pk,
            payer_name=str(partner),
            source_module=ReceiptSourceModule.MANUAL,
            receipt_amount="150000.00",
            currency="TZS",
            payment_mode="CASH",
            narration="Scenario 2: cash received, posted, not yet allocated.",
        )
        post_receipt(receipt, actor=actor, reason="Scenario 2: cash confirmed.", source_channel="SYSTEM")
        return self._entry("2", "Posted unallocated cash", receipt, "created+posted")

    def _posted_partially_allocated(self, actor, branch):
        key = "SEED-RCT-03-PARTIAL"
        receipt = scenario_receipt(key)
        if receipt is not None:
            return self._entry("3", "Posted partially allocated", receipt, "already present")
        partner = get_partner("SEEDP003", first_name="Catherine", surname="Kileo")
        commitment = get_commitment(
            "SEED-OLC-003", partner, premium="100000.00", currency="TZS", status="PENDING"
        )
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
            narration="Scenario 3: partial first instalment received.",
        )
        post_receipt(receipt, actor=actor, reason="Scenario 3: money confirmed.", source_channel="SYSTEM")
        allocate(
            receipt,
            target_type=ReceiptAllocationTargetType.OL_COMMITMENT,
            target_id=commitment.commitment_number,
            amount="40000.00",
            narration="Scenario 3: partial allocation.",
            actor=actor,
            source_channel="SYSTEM",
        )
        return self._entry("3", "Posted partially allocated", receipt, "created+posted+allocated")

    def _first_premium_full(self, actor, branch):
        key = "SEED-RCT-04-FIRST-PREMIUM"
        receipt = scenario_receipt(key)
        if receipt is not None:
            return self._entry("4", "Fully allocated first premium", receipt, "already present")
        partner = get_partner("SEEDP004", first_name="Daudi", surname="Msigwa")
        proposal = make_proposal("SEED-OLP-004", "100000.00", partner, currency="TZS")
        commitment, _created = link_first_premium(proposal, actor=actor)
        receipt, _created = create_draft(
            actor=actor,
            source_channel="SYSTEM",
            idempotency_key=key,
            receipt_date=timezone.localdate(),
            branch_id=branch.pk,
            partner_id=partner.pk,
            payer_name=str(partner),
            source_module=ReceiptSourceModule.OL_PROPOSAL,
            source_reference_type="PROPOSAL_NUMBER",
            source_reference_id=proposal.proposal_number,
            receipt_amount="100000.00",
            currency="TZS",
            payment_mode="CASH",
            narration=f"Scenario 4: first premium for proposal {proposal.proposal_number}.",
        )
        post_receipt(receipt, actor=actor, reason="Scenario 4: first premium confirmed.", source_channel="SYSTEM")
        allocate(
            receipt,
            target_type=ReceiptAllocationTargetType.OL_COMMITMENT,
            target_id=commitment.commitment_number,
            amount="100000.00",
            narration=f"Scenario 4: full first-premium allocation {commitment.commitment_number}.",
            actor=actor,
            source_channel="SYSTEM",
        )
        from apps.ol_proposals.services.first_premium_service import first_premium_posted

        proposal.refresh_from_db()
        return self._entry(
            "4", "Fully allocated first premium", receipt, "created+posted+fully allocated",
            extra={
                "commitment": proposal.first_premium_commitment.commitment_number,
                "commitment_status": proposal.first_premium_commitment.status,
                "first_premium_posted": first_premium_posted(proposal),
            },
        )

    def _bank_transfer_reference(self, actor, branch):
        key = "SEED-RCT-05-BANK"
        receipt = scenario_receipt(key)
        if receipt is not None:
            return self._entry("5", "Bank transfer with reference", receipt, "already present")
        partner = get_partner("SEEDP005", first_name="Ester", surname="Nyoni")
        bank_account = get_partner_bank_account(partner, account_number="0150-3192-7777")
        commitment = get_commitment(
            "SEED-OLC-005", partner, premium="500000.00", currency="TZS", status="PENDING"
        )
        receipt, _created = create_draft(
            actor=actor,
            source_channel="SYSTEM",
            idempotency_key=key,
            receipt_date=timezone.localdate(),
            branch_id=branch.pk,
            partner_id=partner.pk,
            payer_name=str(partner),
            source_module=ReceiptSourceModule.MANUAL,
            receipt_amount="500000.00",
            currency="TZS",
            payment_mode="BANK_TRANSFER",
            payment_reference="CRDB-EI-20260825-0042",
            bank_account_id=bank_account.pk,
            narration="Scenario 5: bank transfer with payment reference.",
        )
        post_receipt(receipt, actor=actor, reason="Scenario 5: transfer credited.", source_channel="SYSTEM")
        allocate(
            receipt,
            target_type=ReceiptAllocationTargetType.OL_COMMITMENT,
            target_id=commitment.commitment_number,
            amount="500000.00",
            narration="Scenario 5: bank transfer allocated in full.",
            actor=actor,
            source_channel="SYSTEM",
        )
        return self._entry("5", "Bank transfer with reference", receipt, "created+posted+allocated")

    def _mobile_money(self, actor, branch):
        key = "SEED-RCT-06-MOBILE"
        receipt = scenario_receipt(key)
        if receipt is not None:
            return self._entry("6", "Mobile money", receipt, "already present")
        partner = get_partner("SEEDP006", first_name="Furaha", surname="Joseph")
        receipt, _created = create_draft(
            actor=actor,
            source_channel="SYSTEM",
            idempotency_key=key,
            receipt_date=timezone.localdate(),
            branch_id=branch.pk,
            partner_id=partner.pk,
            payer_name=str(partner),
            source_module=ReceiptSourceModule.MANUAL,
            receipt_amount="120000.00",
            currency="TZS",
            payment_mode="M-PESA",
            payment_reference="MPESA-SEED-20260825-88B1",
            narration="Scenario 6: M-PESA mobile money receipt.",
        )
        post_receipt(receipt, actor=actor, reason="Scenario 6: mobile money received.", source_channel="SYSTEM")
        return self._entry("6", "Mobile money", receipt, "created+posted")

    def _multi_currency(self, actor, branch):
        key = "SEED-RCT-07-USD"
        receipt = scenario_receipt(key)
        if receipt is not None:
            return self._entry("7", "Multi-currency allocation", receipt, "already present")
        partner = get_partner("SEEDP007", first_name="Grace", surname="Mwakasege")
        commitment = get_commitment(
            "SEED-OLC-007", partner, premium="2500000.00", currency="TZS", status="PENDING"
        )
        receipt, _created = create_draft(
            actor=actor,
            source_channel="SYSTEM",
            idempotency_key=key,
            receipt_date=timezone.localdate(),
            branch_id=branch.pk,
            partner_id=partner.pk,
            payer_name=str(partner),
            source_module=ReceiptSourceModule.MANUAL,
            receipt_amount="1000.00",
            currency="USD",
            exchange_rate="2500.000000",
            payment_mode="CASH",
            narration="Scenario 7: USD receipt allocated to a TZS commitment at 2,500.",
        )
        post_receipt(receipt, actor=actor, reason="Scenario 7: USD credited.", source_channel="SYSTEM")
        allocate(
            receipt,
            target_type=ReceiptAllocationTargetType.OL_COMMITMENT,
            target_id=commitment.commitment_number,
            amount="1000.00",
            exchange_rate="2500.000000",
            exchange_rate_source="EXCHANGE_RATE_TABLE:SEED",
            narration="Scenario 7: cross-currency allocation.",
            actor=actor,
            source_channel="SYSTEM",
        )
        return self._entry(
            "7", "Multi-currency allocation", receipt, "created+posted+allocated",
            extra={"converted_amount": "2,500,000.00 TZS at 1,000 USD"},
        )

    def _reversed(self, actor, branch):
        key = "SEED-RCT-08-REVERSED"
        receipt = scenario_receipt(key)
        if receipt is not None:
            return self._entry("8", "Reversed receipt", receipt, "already present")
        partner = get_partner("SEEDP008", first_name="Hassan", surname="Shabani")
        commitment = get_commitment(
            "SEED-OLC-008", partner, premium="100000.00", currency="TZS", status="PENDING"
        )
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
            narration="Scenario 8: receipt posted then reversed (duplicate payment).",
        )
        post_receipt(receipt, actor=actor, reason="Scenario 8: money confirmed.", source_channel="SYSTEM")
        allocate(
            receipt,
            target_type=ReceiptAllocationTargetType.OL_COMMITMENT,
            target_id=commitment.commitment_number,
            amount="100000.00",
            narration="Scenario 8: allocation before reversal.",
            actor=actor,
            source_channel="SYSTEM",
        )
        reverse_receipt(
            receipt,
            reason="Scenario 8: duplicate deposit — reversed in full.",
            actor=actor,
            source_channel="SYSTEM",
        )
        return self._entry("8", "Reversed receipt", receipt, "created+posted+allocated+reversed")

    def _cancelled_draft(self, actor, branch):
        key = "SEED-RCT-09-CANCELLED"
        receipt = scenario_receipt(key)
        if receipt is not None:
            return self._entry("9", "Cancelled draft", receipt, "already present")
        partner = get_partner("SEEDP009", first_name="Imani", surname="Temba")
        receipt, _created = create_draft(
            actor=actor,
            source_channel="MANUAL",
            idempotency_key=key,
            receipt_date=timezone.localdate(),
            branch_id=branch.pk,
            partner_id=partner.pk,
            payer_name=str(partner),
            source_module=ReceiptSourceModule.MANUAL,
            receipt_amount="75000.00",
            currency="TZS",
            payment_mode="CASH",
            narration="Scenario 9: draft cancelled before posting.",
        )
        cancel_draft(receipt, reason="Scenario 9: payer declined the deposit.", actor=actor, source_channel="MANUAL")
        return self._entry("9", "Cancelled draft", receipt, "created+cancelled")

    def _csv_import(self, actor, branch):
        marker = "SEED-10-CSV-IMPORT"
        existing = Receipt.objects.filter(narration__icontains=marker).order_by("-created_at").first()
        if existing is not None:
            return self._entry("10", "CSV-imported", existing, "already present")
        partner = get_partner("SEEDP010", first_name="Jackson", surname="Macha")
        csv_file = make_import_csv(
            [
                {
                    "receipt_date": timezone.localdate().isoformat(),
                    "branch_code": branch.code,
                    "payer_partner_number": partner.partner_number,
                    "currency_code": "TZS",
                    "payment_mode_code": "CASH",
                    "amount": "90000.00",
                    "payment_reference": "",
                    "source_module": "MANUAL",
                    "target_commitment_number": "",
                    "narration": marker,
                }
            ]
        )
        batch = dry_run(file=csv_file, import_mode="POST", actor=actor)
        committed = commit_batch(batch=batch, actor=actor)
        receipt = committed.rows.filter(receipt__isnull=False).first().receipt
        return self._entry(
            "10", "CSV-imported", receipt, f"dry-run+commit (batch {batch.batch_number})",
            extra={"batch_status": committed.status},
        )

    # ------------------------------------------------------------------ #
    # Output
    # ------------------------------------------------------------------ #

    def _entry(self, number, label, receipt, status, extra=None):
        return {
            "number": number,
            "label": label,
            "receipt_number": receipt.receipt_number or "—",
            "status": receipt.status,
            "amount": str(receipt.receipt_amount),
            "currency": receipt.currency,
            "result": status,
            **(extra or {}),
        }

    def _render(self, manifest):
        self.stdout.write(self.style.SUCCESS("Seeded 10 Front Office Receipts scenarios:"))
        self.stdout.write("")
        header = f"{'#':<3} {'Scenario':<38} {'Receipt #':<16} {'Status':<20} {'Amount':<12} {'Result'}"
        self.stdout.write(header)
        self.stdout.write("-" * len(header))
        for row in manifest:
            extra = " | " + " | ".join(f"{k}={v}" for k, v in row.items()
                                       if k not in ("number", "label", "receipt_number", "status", "amount", "currency", "result"))
            self.stdout.write(
                f"{row['number']:<3} {row['label']:<38} {row['receipt_number']:<16} "
                f"{row['status']:<20} {row['amount']:<12} {row['result']}{extra}"
            )
        self.stdout.write("")
        counts = {}
        for row in manifest:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        self.stdout.write(
            self.style.WARNING(
                "Status histogram: " + ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
            )
        )
