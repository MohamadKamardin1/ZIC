"""Seed the default OL Proposal summary print template idempotently."""

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ol_proposals.models import OLProposalPrintTemplate
from apps.ol_proposals.services.print_service import (
    DEFAULT_COMPANY,
    DEFAULT_TEMPLATE_CODE,
    DEFAULT_TEMPLATE_HTML,
    DEFAULT_TEMPLATE_VERSION,
)


class Command(BaseCommand):
    help = "Seed the OL Proposal summary print template (code + version)."

    @transaction.atomic
    def handle(self, *args, **options):
        defaults = {
            "name": "Ordinary Life Proposal Summary",
            "description": "Summary printout for OL proposals.",
            "template_html": DEFAULT_TEMPLATE_HTML,
            "layout_variables": dict(DEFAULT_COMPANY),
            "effective_from": date(2020, 1, 1),
            "is_active": True,
        }
        OLProposalPrintTemplate.objects.update_or_create(
            code=DEFAULT_TEMPLATE_CODE,
            version=DEFAULT_TEMPLATE_VERSION,
            defaults=defaults,
        )
        self.stdout.write(
            self.style.SUCCESS(f"Seeded proposal print template {DEFAULT_TEMPLATE_CODE} v{DEFAULT_TEMPLATE_VERSION}.")
        )