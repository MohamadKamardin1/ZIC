from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.ol_policies.services.maturity_service import process_policy_maturity


class Command(BaseCommand):
    help = "Create configured maturity claims for active policies at or past maturity."

    def add_arguments(self, parser):
        parser.add_argument("--as-of", dest="as_of", help="Evaluation date in YYYY-MM-DD format.")
        parser.add_argument("--dry-run", action="store_true", help="Reserved for reporting-only integrations.")

    def handle(self, *args, **options):
        as_of = self._parse_date(options.get("as_of"))
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY RUN: maturity claims were not created."))
            return
        result = process_policy_maturity(as_of=as_of, source_channel="BATCH")
        self.stdout.write(
            self.style.SUCCESS(
                f"Policy maturity processing complete: processed={result['processed']}, created={result['created']}, skipped={result['skipped']}."
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
