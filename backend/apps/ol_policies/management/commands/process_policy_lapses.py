from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.ol_policies.models import Policy, PolicyStatus
from apps.ol_policies.services.lifecycle_service import process_policy_lapses


class Command(BaseCommand):
    help = "Mark eligible Ordinary Life policies as lapsed using configured grace periods."

    def add_arguments(self, parser):
        parser.add_argument("--as-of", dest="as_of", help="Evaluation date in YYYY-MM-DD format.")
        parser.add_argument("--dry-run", action="store_true", help="Report candidates without changing data.")

    def handle(self, *args, **options):
        as_of = self._parse_date(options.get("as_of"))
        if options["dry_run"]:
            count = Policy.objects.filter(status=PolicyStatus.ACTIVE).count()
            self.stdout.write(self.style.WARNING(f"DRY RUN: inspected {count} active policies; no changes made."))
            return
        result = process_policy_lapses(as_of=as_of, source_channel="BATCH")
        self.stdout.write(
            self.style.SUCCESS(
                f"Policy lapse processing complete: processed={result.processed}, changed={result.changed}, skipped={result.skipped}."
            )
        )

    @staticmethod
    def _parse_date(raw):
        if not raw:
            return date.today()
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise CommandError("--as-of must use YYYY-MM-DD format.") from exc
