
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ol_parameters.models import OLProposalStatus


def _statuses(as_of=None):
    return [
        {
            "code": "DRAFT",
            "name": "Draft (legacy handoff)",
            "display_order": 10,
            "is_terminal": False,
            "allowed_transitions": ["ENRICHMENT"],
            "description": "Created from a finalized quotation (legacy handoff status).",
        },
        {
            "code": "ENRICHMENT",
            "name": "Enrichment",
            "display_order": 20,
            "is_terminal": False,
            "allowed_transitions": ["ENRICHMENT", "PENDING_UNDERWRITING", "PAYMENT_READY", "CANCELLED"],
            "description": "Operator confirms carried quotation data and required documents.",
        },
        {
            "code": "PENDING_UNDERWRITING",
            "name": "Pending underwriting",
            "display_order": 30,
            "is_terminal": False,
            "allowed_transitions": ["PAYMENT_READY", "ENRICHMENT", "CANCELLED"],
            "description": "Underwriting review in progress; may raise medical requirements.",
        },
        {
            "code": "PAYMENT_READY",
            "name": "Payment ready",
            "display_order": 40,
            "is_terminal": False,
            "allowed_transitions": ["AWAITING_FIRST_PREMIUM", "ENRICHMENT", "CANCELLED"],
            "description": "Enrichment and mandatory documents complete; first premium can be generated.",
        },
        {
            "code": "AWAITING_FIRST_PREMIUM",
            "name": "Awaiting first premium",
            "display_order": 50,
            "is_terminal": False,
            "allowed_transitions": ["CONVERTED", "EXPIRED", "CANCELLED"],
            "description": "First-premium commitment created; awaiting settlement before policy conversion.",
        },
        {
            "code": "CONVERTED",
            "name": "Converted",
            "display_order": 60,
            "is_terminal": True,
            "allowed_transitions": [],
            "description": "Policy issued from this proposal.",
        },
        {
            "code": "CANCELLED",
            "name": "Cancelled",
            "display_order": 70,
            "is_terminal": True,
            "allowed_transitions": [],
            "description": "Proposal closed by an operator with a reason.",
        },
        {
            "code": "EXPIRED",
            "name": "Expired",
            "display_order": 80,
            "is_terminal": True,
            "allowed_transitions": [],
            "description": "Proposal passed its expiry date without conversion.",
        },
    ]


class Command(BaseCommand):
    help = "Seed the OL Proposal Status catalog idempotently."

    @transaction.atomic
    def handle(self, *args, **options):
        for payload in _statuses():
            effective_from = payload.get("effective_from") or date(2020, 1, 1)
            OLProposalStatus.objects.update_or_create(
                code=payload["code"],
                defaults={
                    "name": payload["name"],
                    "description": payload.get("description", ""),
                    "display_order": payload["display_order"],
                    "applies_to": "PROPOSAL",
                    "is_terminal": payload["is_terminal"],
                    "allowed_transitions": payload["allowed_transitions"],
                    "effective_from": effective_from,
                    "is_active": True,
                },
            )
        self.stdout.write(
            self.style.SUCCESS(f"OL Proposal Status catalog seeded: {len(_statuses())} statuses.")
        )