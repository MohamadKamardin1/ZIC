"""Prompt 12 release gate: pins the BR-03 seam, the seed manifest and the failure proofs.

These tests replay the same flows the ``seed_receipt_scenarios``,
``receipt_failure_proofs`` and ``verify_br03_release`` management commands
execute, so CI exercises the exact release surface rather than a parallel
implementation. Each test runs inside a rolled-back transaction, so the
commands stay idempotent against a clean database on every run.
"""

from django.core.management import call_command
from django.test import TestCase

from apps.front_office.management.commands.receipt_failure_proofs import run_proofs
from apps.front_office.management.commands.verify_br03_release import run_verification
from apps.front_office.receipts.models import Receipt
from apps.governance.models import AuditLog


class Br03ReleaseGateTests(TestCase):
    def test_br03_guard_blocks_before_allocation(self):
        result = run_verification()
        step = result["steps"]["guard_blocks_before_allocation"]
        self.assertTrue(step["passed"])
        self.assertFalse(step["first_premium_posted"])
        self.assertEqual(step["caught_error"]["code"], "PROPOSAL_FIRST_PREMIUM_NOT_POSTED")

    def test_br03_full_lifecycle_converts_reversal_reconverts(self):
        result = run_verification()
        self.assertTrue(result["all_passed"])
        self.assertTrue(result["steps"]["converts_after_full_allocation"]["passed"])
        self.assertTrue(result["steps"]["guard_false_after_reversal"]["passed"])
        self.assertTrue(result["steps"]["reconversion_returns_existing_policy"]["passed"])

    def test_br03_verification_is_rerunnable(self):
        first = run_verification()
        second = run_verification()
        self.assertTrue(first["all_passed"])
        self.assertTrue(second["all_passed"])
        self.assertEqual(
            first["steps"]["converts_after_full_allocation"]["policy_number"],
            second["steps"]["converts_after_full_allocation"]["policy_number"],
        )


class SeedManifestTests(TestCase):
    def setUp(self):
        call_command("seed_receipt_scenarios")

    def test_exactly_ten_scenarios_seeded_with_expected_statuses(self):
        expected = {
            "SEED-RCT-01-DRAFT": "DRAFT",
            "SEED-RCT-02-POSTED": "POSTED",
            "SEED-RCT-03-PARTIAL": "PARTIALLY_ALLOCATED",
            "SEED-RCT-04-FIRST-PREMIUM": "FULLY_ALLOCATED",
            "SEED-RCT-05-BANK": "FULLY_ALLOCATED",
            "SEED-RCT-06-MOBILE": "POSTED",
            "SEED-RCT-07-USD": "FULLY_ALLOCATED",
            "SEED-RCT-08-REVERSED": "REVERSED",
            "SEED-RCT-09-CANCELLED": "CANCELLED",
        }
        for idempotency_key, expected_status in expected.items():
            receipt = Receipt.objects.filter(idempotency_key=idempotency_key).first()
            self.assertIsNotNone(receipt, f"missing scenario {idempotency_key}")
            self.assertEqual(receipt.status, expected_status, f"status mismatch for {idempotency_key}")

        imported = Receipt.objects.filter(narration__icontains="SEED-10-CSV-IMPORT").order_by("-created_at").first()
        self.assertIsNotNone(imported, "missing CSV-imported scenario")
        self.assertEqual(imported.status, "POSTED")

        all_seed = Receipt.objects.filter(
            idempotency_key__startswith="SEED-RCT-"
        ) | Receipt.objects.filter(narration__icontains="SEED-10-CSV-IMPORT")
        self.assertEqual(all_seed.count(), 10)

    def test_first_premium_scenario_satisfies_br03(self):
        from apps.ol_proposals.models import OLProposal
        from apps.ol_proposals.services.first_premium_service import first_premium_posted

        proposal = OLProposal.objects.get(proposal_number="SEED-OLP-004")
        self.assertEqual(proposal.first_premium_commitment.status, "COMPLETED")
        self.assertTrue(first_premium_posted(proposal))

    def test_seed_produced_audit_trail(self):
        self.assertGreater(AuditLog.objects.filter(entity_type="receipt").count(), 0)


class FailureProofTests(TestCase):
    def test_all_five_failure_proofs_caught_with_expected_codes(self):
        proofs = run_proofs()
        self.assertEqual(len(proofs), 5)
        by_proof = {p["proof"]: p for p in proofs}
        expected_codes = {
            "missing_payment_reference": "RECEIPT_PAYMENT_REFERENCE_REQUIRED",
            "over_allocation": "RECEIPT_OVERALLOCATION",
            "cross_currency_without_exchange_rate": "RECEIPT_CURRENCY_MISMATCH",
            "allocation_to_completed_commitment": "RECEIPT_OVERALLOCATION",
            "reversal_after_lock_period": "RECEIPT_REVERSAL_LOCKED",
        }
        for proof_name, expected_code in expected_codes.items():
            proof = by_proof[proof_name]
            self.assertEqual(proof["outcome"], "caught", f"{proof_name} escaped the guard")
            self.assertEqual(proof["error"]["code"], expected_code, f"{proof_name} raised the wrong code")
