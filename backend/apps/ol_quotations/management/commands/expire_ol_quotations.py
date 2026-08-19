from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError

from apps.ol_quotations.services.quotation_service import QuotationService


class Command(BaseCommand):
    help = "Mark expired Ordinary Life quotations as EXPIRED using their configured expiry dates."

    def add_arguments(self, parser):
        parser.add_argument(
            "--as-of",
            dest="as_of",
            help="Evaluate expiry as of YYYY-MM-DD; defaults to the current local date.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report the number of quotations eligible for expiry without changing data.",
        )

    def handle(self, *args, **options):
        as_of = date.today()
        if options.get("as_of"):
            try:
                as_of = datetime.strptime(options["as_of"], "%Y-%m-%d").date()
            except ValueError as exc:
                raise CommandError("--as-of must use YYYY-MM-DD format.") from exc

        queryset = QuotationService.expirable_queryset(as_of=as_of)
        if options.get("dry_run"):
            self.stdout.write(
                self.style.WARNING(
                    f"{queryset.count()} OL quotations would expire as of {as_of.isoformat()}."
                )
            )
            return

        expired = QuotationService.expire_batch(as_of=as_of)
        self.stdout.write(
            self.style.SUCCESS(
                f"Expired {len(expired)} OL quotations as of {as_of.isoformat()}."
            )
        )
