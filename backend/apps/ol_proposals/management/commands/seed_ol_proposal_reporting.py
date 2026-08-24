"""Seed the OL Proposals reporting category and dataset registry idempotently."""

from django.core.management.base import BaseCommand

from apps.ol_proposals.services.reporting_service import register


class Command(BaseCommand):
    help = "Register the 'Ordinary Life Proposals' report category and dataset registry."

    def handle(self, *args, **options):
        contract = register()
        self.stdout.write(
            self.style.SUCCESS(
                f"Reporting category '{contract['category']['name']}' registered with {len(contract['fields'])} dataset fields."
            )
        )