import json
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.governance.models import AuditLog
from apps.ol_loans.models import LoanStatus, OLLoan, OLLoanDisbursement, OLLoanOffset


class OLLoanReleaseSeedTests(TestCase):
    def _run_seed(self):
        output = StringIO()
        call_command("seed_ol_loan_release", "--json", stdout=output)
        return json.loads(output.getvalue())

    def test_seed_creates_exactly_ten_scenarios_across_all_required_states(self):
        result = self._run_seed()

        self.assertEqual(result["loan_count"], 10)
        self.assertTrue(result["idempotent"])
        self.assertEqual(OLLoan.objects.filter(loan_number__startswith="OL-RELEASE-").count(), 10)
        self.assertEqual(
            {row["status"] for row in result["scenarios"]},
            {
                LoanStatus.ACTIVE,
                LoanStatus.PARTIALLY_REPAID,
                LoanStatus.SETTLED,
                LoanStatus.DEFAULTED,
                LoanStatus.OFFSET_ON_SURRENDER,
                LoanStatus.OFFSET_ON_CLAIM,
                LoanStatus.REJECTED,
                LoanStatus.REQUESTED,
            },
        )

        rows_by_scenario = {row["scenario"]: row for row in result["scenarios"]}
        self.assertEqual(rows_by_scenario["multi-currency repayment"]["status"], LoanStatus.PARTIALLY_REPAID)
        self.assertEqual(rows_by_scenario["multi-currency repayment"]["repayment_count"], 1)
        self.assertEqual(rows_by_scenario["offset on surrender"]["offset_count"], 1)
        self.assertEqual(rows_by_scenario["offset on death claim"]["offset_count"], 1)
        self.assertEqual(rows_by_scenario["pending approval"]["status"], LoanStatus.REQUESTED)
        self.assertEqual(rows_by_scenario["rejected request"]["status"], LoanStatus.REJECTED)
        self.assertEqual(OLLoanDisbursement.objects.filter(loan__loan_number__startswith="OL-RELEASE-").count(), 8)

    def test_failure_proofs_are_caught_with_teachable_codes_and_no_financial_mutation(self):
        result = self._run_seed()
        proofs = result["failure_proofs"]

        self.assertEqual(proofs["ineligible_policy"]["error_code"], "LOAN_INELIGIBLE")
        self.assertEqual(proofs["exceeds_cash_value_limit"]["error_code"], "LOAN_EXCEEDS_LIMIT")
        self.assertEqual(proofs["overpayment"]["error_code"], "LOAN_REPAYMENT_OVERPAYMENT")
        self.assertEqual(proofs["offset_on_already_settled"]["error_code"], "LOAN_OFFSET_INVALID")
        for proof in proofs.values():
            self.assertIn("resolution_steps", proof)
            self.assertTrue(proof["resolution_steps"])
        self.assertEqual(OLLoanOffset.objects.filter(loan__loan_number="OL-RELEASE-LOAN-SETTLED-001").count(), 0)
        self.assertEqual(
            OLLoan.objects.filter(loan_number__startswith="OL-RELEASE-").count(),
            result["loan_count"],
        )
        self.assertEqual(proofs["duplicate_disbursement"]["status"], "idempotent_replay")
        self.assertFalse(proofs["duplicate_disbursement"]["created"])

    def test_rerun_is_idempotent_and_audited_by_release_operator(self):
        first = self._run_seed()
        audit_count_before = AuditLog.objects.filter(action="LOAN_DISBURSED").count()
        repayment_count_before = sum(row["repayment_count"] for row in first["scenarios"])
        offset_count_before = sum(row["offset_count"] for row in first["scenarios"])

        second = self._run_seed()

        self.assertEqual(second["loan_count"], 10)
        self.assertEqual(OLLoan.objects.filter(loan_number__startswith="OL-RELEASE-").count(), 10)
        self.assertEqual(AuditLog.objects.filter(action="LOAN_DISBURSED").count(), audit_count_before)
        self.assertEqual(sum(row["repayment_count"] for row in second["scenarios"]), repayment_count_before)
        self.assertEqual(sum(row["offset_count"] for row in second["scenarios"]), offset_count_before)
        audited_loan = OLLoan.objects.get(loan_number="OL-RELEASE-LOAN-ACTIVE-001")
        self.assertTrue(
            AuditLog.objects.filter(
                action="LOAN_REQUESTED",
                object_id=str(audited_loan.pk),
                user__username="ol_loan_release_operator",
                source_channel="SYSTEM",
            ).exists()
        )
