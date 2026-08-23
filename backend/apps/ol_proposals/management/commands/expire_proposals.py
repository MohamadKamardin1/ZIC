"""Expire proposals whose expiry date has passed (idempotent, system-audited)."""

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ol_proposals.models import OLProposal
from apps.ol_proposals.services import parameter_resolver
from apps.ol_proposals.services.lifecycle_service import mark_expired


class Command(BaseCommand):
    help = "Mark proposals whose expiry date has passed as EXPIRED with a system audit."

    @transaction.atomic
    def handle(self, *args, **options):
        today = date.today()
        terminal = set(parameter_resolver.terminal_proposal_statuses() or ("CANCELLED", "CONVERTED", "EXPIRED"))
        candidates = OLProposal.objects.filter(expiry_date__isnull=False, expiry_date__lt=today).exclude(
            status__in=terminal
        )
        count = 0
        for proposal in candidates:
            mark_expired(
                proposal=proposal,
                reason=f"Proposal expired on {today.isoformat()}.",
                source_channel="SYSTEM",
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Expired {count} proposal(s)."))