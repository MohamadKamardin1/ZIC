from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.ordinary_life.validation import validate_reference_data


class Command(BaseCommand):
    help = "Validate Ordinary Life reference data and active product configuration."

    def handle(self, *args, **options):
        try:
            validate_reference_data()
        except ValidationError as exc:
            raise CommandError("Ordinary Life reference data is invalid: " + "; ".join(exc.messages)) from exc
        self.stdout.write(self.style.SUCCESS("Ordinary Life reference data is valid."))
