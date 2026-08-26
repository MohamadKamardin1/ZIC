from datetime import date
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ...services.default_service import detect_loan_defaults, system_actor


def _parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise CommandError("--as-of must use YYYY-MM-DD format.") from exc


class Command(BaseCommand):
    help = "Detect OL Loans whose overdue installments exceed configured grace and penalty periods."

    def add_arguments(self, parser):
        parser.add_argument("--as-of", default=timezone.localdate().isoformat())
        parser.add_argument("--loan-id")
        parser.add_argument("--correlation-id")

    def handle(self, *args, **options):
        as_of = _parse_date(options["as_of"])
        correlation_id = options.get("correlation_id") or f"OL-DEFAULT-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:8].upper()}"
        result = detect_loan_defaults(
            as_of=as_of,
            actor=system_actor(),
            source_channel="BATCH",
            correlation_id=correlation_id,
            loan_id=options.get("loan_id"),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"OL default detection batch {correlation_id}: processed={result.processed}, defaulted={result.defaulted}, skipped={result.skipped}, errors={len(result.errors)}; as_of={as_of}."
            )
        )
        for error in result.errors:
            self.stdout.write(self.style.WARNING(f"{error['loan_number']}: {error['error_code']} — {error['message']}"))
        if result.errors:
            self.stdout.write(self.style.WARNING("The batch completed with per-loan errors; review the warnings and audit row."))
