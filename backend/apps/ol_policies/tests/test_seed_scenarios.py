import json
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.ol_policies.models import Policy, PolicyStatus


class PolicyScenarioSeedTestCase(TestCase):
    def test_seed_creates_eight_states_and_failure_proofs(self):
        output = StringIO()
        call_command("seed_ol_policy_scenarios", "--json", stdout=output)
        result = json.loads(output.getvalue())

        self.assertEqual(result["policy_count"], 8)
        self.assertEqual(
            set(result["states"].values()),
            {
                PolicyStatus.ACTIVE,
                PolicyStatus.LAPSED,
                PolicyStatus.MATURED,
                PolicyStatus.PAID_UP,
                PolicyStatus.SURRENDERED,
                PolicyStatus.CANCELLED,
            },
        )
        self.assertEqual(
            result["failure_proofs"]["issue_without_first_premium"]["error_code"],
            "POLICY_FIRST_PREMIUM_NOT_POSTED",
        )
        self.assertEqual(
            result["failure_proofs"]["reinstate_outside_window"]["error_code"],
            "POLICY_LAPSED",
        )
        self.assertEqual(
            result["failure_proofs"]["surrender_within_first_year"]["error_code"],
            "POLICY_SURRENDER_BLOCKED",
        )
        self.assertEqual(Policy.objects.filter(policy_number__startswith="OL-SEED-").count(), 8)

    def test_seed_is_idempotent_and_preserves_the_eight_policy_set(self):
        first = StringIO()
        second = StringIO()
        call_command("seed_ol_policy_scenarios", "--json", stdout=first)
        call_command("seed_ol_policy_scenarios", "--json", stdout=second)
        first_result = json.loads(first.getvalue())
        second_result = json.loads(second.getvalue())

        self.assertEqual(first_result["seeded_policy_numbers"], second_result["seeded_policy_numbers"])
        self.assertEqual(Policy.objects.filter(policy_number__startswith="OL-SEED-").count(), 8)
        self.assertEqual(second_result["policy_count"], 8)
        self.assertTrue(second_result["idempotent"])
