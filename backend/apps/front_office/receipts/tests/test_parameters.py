import re
import threading
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APITestCase

from apps.front_office.receipts.config_models import (
    CompanyBankAccount,
    ReceiptNumberingRule,
    ReceiptPaymentModeRule,
    ResetFrequency,
    mask_account_number,
)
from apps.front_office.receipts.errors import ReceiptError
from apps.front_office.receipts.services.receipt_numbering import ReceiptNumberingService
from apps.partner_onboarding.models import Branch

User = get_user_model()

BASE = "/api/v1/front-office/receipts"


def make_branch(code="DAR", name="Dar es Salaam"):
    return Branch.objects.create(code=code, name=name)


class ReceiptNumberingServiceTests(TestCase):
    def setUp(self):
        call_command("seed_receipt_parameters")

    def test_generation_format_and_sequence(self):
        first = ReceiptNumberingService.next_number()
        second = ReceiptNumberingService.next_number()
        self.assertRegex(first, r"^RCT-\d{4}-\d{6}$")
        self.assertEqual(first, "RCT-2026-000001")
        self.assertEqual(second, "RCT-2026-000002")

    def test_branch_aware_rule_selection(self):
        branch = make_branch(code="DAR", name="Dar es Salaam")
        ReceiptNumberingRule.objects.create(
            code="RCT_DAR",
            name="Dar es Salaam Receipts",
            branch=branch,
            prefix="DAR",
            sequence_padding=5,
            next_sequence=1,
            reset_frequency=ResetFrequency.YEARLY,
        )
        number = ReceiptNumberingService.next_number(branch_id=branch.pk)
        self.assertRegex(number, r"^DAR-\d{4}-\d{5}$")
        self.assertEqual(number, "DAR-2026-00001")

    def test_missing_numbering_rule_raises_structured_error(self):
        ReceiptNumberingRule.objects.filter(is_active=True).update(is_active=False)
        with self.assertRaises(ReceiptError) as ctx:
            ReceiptNumberingService.next_number()
        self.assertEqual(ctx.exception.error_code, "RECEIPT_PARAMETER_MISSING")
        self.assertEqual(
            ctx.exception.details["navigation_path"],
            "Front Office Parameters > Receipt Numbering",
        )

    def test_inactive_rule_is_not_selected(self):
        ReceiptNumberingRule.objects.update(is_active=False)
        with self.assertRaises(ReceiptError):
            ReceiptNumberingService.next_number()


class ReceiptNumberingConcurrencyTests(TransactionTestCase):
    def test_concurrent_generation_is_unique(self):
        call_command("seed_receipt_parameters")
        results = []
        errors = []

        def worker(count):
            for _ in range(count):
                try:
                    results.append(ReceiptNumberingService.next_number())
                except Exception as exc:  # pragma: no cover - surfaces a real failure
                    errors.append(exc)

        threads = [threading.Thread(target=worker, args=(5,)) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])
        self.assertEqual(len(results), 40)
        self.assertEqual(len(set(results)), 40)


class CompanyBankAccountTests(TestCase):
    def test_masked_account_number_property(self):
        account = CompanyBankAccount(
            code="TZS_MAIN",
            bank_name="CRDB Bank PLC",
            account_name="ZIC Main Account",
            account_number="015031929999",
            currency="TZS",
        )
        self.assertEqual(account.masked_account_number, "********9999")

    def test_mask_account_number_helper(self):
        self.assertEqual(mask_account_number("1234567890"), "******7890")
        self.assertEqual(mask_account_number("1234"), "****")
        self.assertEqual(mask_account_number(""), "****")

    def test_clean_rejects_bad_currency(self):
        account = CompanyBankAccount(
            code="BAD",
            bank_name="B",
            account_name="A",
            account_number="12345",
            currency="TANX",
        )
        with self.assertRaises(ValidationError) as ctx:
            account.full_clean()
        self.assertIn("currency", ctx.exception.message_dict)


class ReceiptPaymentModeRuleTests(TestCase):
    def test_rule_rejects_max_below_min(self):
        rule = ReceiptPaymentModeRule(
            payment_mode="TEST",
            allows_cash=True,
            min_amount=Decimal("500.00"),
            max_amount=Decimal("100.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            rule.full_clean()
        self.assertIn("max_amount", ctx.exception.message_dict)

    def test_rule_requires_at_least_one_instrument(self):
        rule = ReceiptPaymentModeRule(payment_mode="TEST")
        with self.assertRaises(ValidationError) as ctx:
            rule.full_clean()
        self.assertIn("__all__", ctx.exception.message_dict)

    def test_valid_rule_passes_clean(self):
        rule = ReceiptPaymentModeRule(
            payment_mode="CASH",
            allows_cash=True,
            requires_reference=False,
            min_amount=Decimal("1000.00"),
        )
        rule.full_clean()
        self.assertEqual(rule.payment_mode, "CASH")


class ReceiptOptionsEndpointTests(APITestCase):
    def setUp(self):
        call_command("seed_receipt_parameters")
        self.admin = User.objects.create_superuser(
            username="options_admin", password="Password@12345", email="options_admin@zic.tz"
        )
        self.client.force_authenticate(self.admin)
        self.branch = make_branch()

    def test_option_groups_use_value_label_meta_shape(self):
        response = self.client.get(f"{BASE}/options/")
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        for group in ("branches", "currencies", "payment_modes", "company_bank_accounts", "receipt_statuses"):
            self.assertIn(group, data)
            for entry in data[group]:
                self.assertIn("value", entry)
                self.assertIn("label", entry)
                self.assertIn("meta", entry)
                self.assertIsInstance(entry["meta"], dict)

    def test_branch_and_bank_account_options(self):
        data = self.client.get(f"{BASE}/options/").data["data"]
        branch_values = {entry["value"] for entry in data["branches"]}
        self.assertIn(str(self.branch.pk), branch_values)
        branch = next(entry for entry in data["branches"] if entry["value"] == str(self.branch.pk))
        self.assertEqual(branch["label"], "Dar es Salaam")
        self.assertEqual(branch["meta"]["code"], "DAR")

        accounts = data["company_bank_accounts"]
        self.assertTrue(accounts)
        account = accounts[0]
        self.assertEqual(account["meta"]["currency"], "TZS")
        self.assertNotEqual(account["meta"]["account_number"], account["label"])
        self.assertIn("****", account["meta"]["account_number"])

    def test_payment_mode_options_come_from_rules(self):
        data = self.client.get(f"{BASE}/options/").data["data"]
        modes = {entry["value"]: entry for entry in data["payment_modes"]}
        self.assertIn("CASH", modes)
        self.assertIn("BANK_TRANSFER", modes)
        self.assertIn("MOBILE_MONEY", modes)
        bank_transfer = modes["BANK_TRANSFER"]
        self.assertTrue(bank_transfer["meta"]["requires_reference"])
        self.assertTrue(bank_transfer["meta"]["requires_bank_account"])

    def test_receipt_statuses_and_currencies(self):
        data = self.client.get(f"{BASE}/options/").data["data"]
        status_values = {entry["value"] for entry in data["receipt_statuses"]}
        self.assertIn("DRAFT", status_values)
        self.assertIn("POSTED", status_values)
        currency_values = {entry["value"] for entry in data["currencies"]}
        self.assertIn("TZS", currency_values)
