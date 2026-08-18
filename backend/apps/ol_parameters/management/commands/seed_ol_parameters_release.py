from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction


SEED_COMMANDS = [
    "seed_ol_default_setup",
    "seed_ol_product_setup",
    "seed_ol_policy_setup",
    "seed_ol_product_rating",
    "seed_ol_product_rating_part2",
    "seed_ol_rider_setup",
    "seed_ol_agent_management",
    "seed_ol_loan_setup",
    "seed_ol_medical_underwriting",
    "seed_ol_claim_setup",
    "seed_ol_parameter_permissions",
    "seed_ol_parameter_registry",
]


class Command(BaseCommand):
    help = "Seed all nine OL Parameter groups, permissions, roles, and table registry idempotently."

    @transaction.atomic
    def handle(self, *args, **options):
        for command_name in SEED_COMMANDS:
            self.stdout.write(f"Running {command_name}...")
            call_command(command_name, verbosity=0)
        self.stdout.write(
            self.style.SUCCESS(
                f"OL Parameters release seed completed: {len(SEED_COMMANDS)} commands executed."
            )
        )
