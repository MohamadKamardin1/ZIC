from django.core.management.base import BaseCommand
from django.db import transaction

from apps.front_office.receipts.config_models import (
    CompanyBankAccount,
    ReceiptNumberingRule,
    ReceiptPaymentModeRule,
    ResetFrequency,
)


class Command(BaseCommand):
    help = "Seed Front Office Receipts baseline parameters (numbering, bank accounts, payment mode rules) idempotently."

    @transaction.atomic
    def handle(self, *args, **options):
        numbering, numbering_created = ReceiptNumberingRule.objects.update_or_create(
            code="RCT_DEFAULT",
            defaults={
                "name": "Default Receipt Numbering",
                "prefix": "RCT",
                "sequence_padding": 6,
                "next_sequence": 1,
                "reset_frequency": ResetFrequency.YEARLY,
                "is_active": True,
            },
        )

        reversal_numbering, reversal_numbering_created = ReceiptNumberingRule.objects.update_or_create(
            code="RVR_DEFAULT",
            defaults={
                "name": "Default Receipt Reversal Numbering",
                "prefix": "RVR",
                "sequence_padding": 6,
                "next_sequence": 1,
                "reset_frequency": ResetFrequency.YEARLY,
                "is_active": True,
            },
        )

        bank, bank_created = CompanyBankAccount.objects.update_or_create(
            code="TZS_MAIN",
            defaults={
                "bank_name": "CRDB Bank PLC",
                "account_name": "ZIC Main Account",
                "account_number": "0150-3192-9999",
                "currency": "TZS",
                "is_default": True,
                "is_active": True,
            },
        )

        rule_seeds = [
            {
                "payment_mode": "CASH",
                "requires_reference": False,
                "requires_bank_account": False,
                "allows_cash": True,
                "min_amount": "1000.00",
            },
            {
                "payment_mode": "BANK_TRANSFER",
                "requires_reference": True,
                "requires_bank_account": True,
                "allows_bank_transfer": True,
                "min_amount": "5000.00",
            },
            {
                "payment_mode": "MOBILE_MONEY",
                "requires_reference": True,
                "requires_bank_account": False,
                "allows_mobile_money": True,
                "min_amount": "1000.00",
                "max_amount": "3000000.00",
            },
            {
                "payment_mode": "CARD",
                "requires_reference": True,
                "requires_bank_account": False,
                "allows_card": True,
                "min_amount": "1000.00",
            },
            {
                "payment_mode": "CHEQUE",
                "requires_reference": True,
                "requires_bank_account": False,
                "allows_cheque": True,
            },
        ]
        created_rules = 0
        updated_rules = 0
        for seed in rule_seeds:
            payment_mode = seed.pop("payment_mode")
            rule, was_created = ReceiptPaymentModeRule.objects.update_or_create(
                payment_mode=payment_mode,
                defaults={**seed, "is_active": True},
            )
            if was_created:
                created_rules += 1
            else:
                updated_rules += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Front Office Receipts parameters seeded: "
                f"numbering rule {('created' if numbering_created else 'updated')}, "
                f"reversal numbering rule {('created' if reversal_numbering_created else 'updated')}, "
                f"bank account {('created' if bank_created else 'updated')}, "
                f"{created_rules} payment mode rules created, {updated_rules} updated."
            )
        )
