import json
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.ol_claims.models import OLClaim, OLClaimLoanOffset


class OLClaimScenarioSeedTest(TestCase):
    def test_final_seed_creates_exactly_ten_scenarios_and_is_idempotent(self):
        first_output = StringIO()
        call_command("seed_ol_claim_scenarios", "--json", stdout=first_output)
        first = json.loads(first_output.getvalue().strip().splitlines()[-1])
        seeded = OLClaim.objects.filter(claim_number__startswith="OL-CLAIM-SEED-")
        self.assertEqual(first["claim_count"], 10)
        self.assertEqual(seeded.count(), 10)
        self.assertEqual(OLClaimLoanOffset.objects.filter(claim__in=seeded).count(), 1)
        self.assertEqual(set(first["states"].values()), {"SETTLED", "PENDING_MEDICAL", "REJECTED", "ASSESSED", "CANCELLED"})
        self.assertEqual(
            set(first["failure_proofs"]),
            {"inactive_policy", "duplicate_claim", "waiting_period_violation", "amount_exceeds_limit"},
        )
        self.assertTrue(all(proof["passed"] for proof in first["failure_proofs"].values()))

        second_output = StringIO()
        call_command("seed_ol_claim_scenarios", "--json", stdout=second_output)
        second = json.loads(second_output.getvalue().strip().splitlines()[-1])
        self.assertEqual(second["claim_count"], 10)
        self.assertEqual(OLClaim.objects.filter(claim_number__startswith="OL-CLAIM-SEED-").count(), 10)
        self.assertEqual(OLClaimLoanOffset.objects.filter(claim__in=seeded).count(), 1)
        self.assertEqual(second["loan_offset"]["offset_amount"], first["loan_offset"]["offset_amount"])
