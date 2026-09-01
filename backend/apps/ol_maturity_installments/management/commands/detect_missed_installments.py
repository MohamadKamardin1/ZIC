from datetime import date
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ...services.lifecycle import detect_missed_installments, system_actor


def _parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise CommandError("--as-of must use YYYY-MM-DD format.") from exc


class Command(BaseCommand):
    help = "Detect OL maturity installments past their due date and mark them MISSED."

    def add_arguments(self, parser):
        parser.add_argument("--as-of", default=timezone.localdate().isoformat())
        parser.add_argument("--plan-id")
        parser.add_argument("--correlation-id")

    def handle(self, *args, **options):
        as_of = _parse_date(options["as_of"])
        correlation_id = (
            options.get("correlation_id") or f"OL-MIP-MISSED-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:8].upper()}"
        )
        result = detect_missed_installments(
            as_of=as_of,
            actor=system_actor(),
            source_channel="BATCH",
            correlation_id=correlation_id,
            plan_id=options.get("plan_id"),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"OL maturity installment missed detection batch {correlation_id}: processed={result.processed}, missed={result.missed}, skipped={result.skipped}; as_of={as_of}."
            )
        )
        for error in result.errors:
            self.stdout.write(self.style.WARNING(f"{error['plan_id']}: {error['error_code']} — {error['message']}"))
