from datetime import date, timedelta
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.users.models import User

from ...models import LoanStatus
from ...services.accrual_service import accrue_batch


SYSTEM_USERNAME = "system"
SYSTEM_EMAIL = "system@zic.local"


def _system_actor():
    actor, _created = User.objects.get_or_create(
        username=SYSTEM_USERNAME,
        defaults={
            "email": SYSTEM_EMAIL,
            "first_name": "ZIC",
            "last_name": "System",
            "user_type": "SYSTEM_MANAGER",
            "status": User.AccountStatus.ACTIVE,
            "is_active": True,
            "is_approved": True,
        },
    )
    return actor


def _parse_date(value, name):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise CommandError(f"{name} must use YYYY-MM-DD format.") from exc


def _periods(as_of, frequency, period_start=None, period_end=None):
    if bool(period_start) != bool(period_end):
        raise CommandError("--period-start and --period-end must be supplied together.")
    if period_start and period_end:
        return _parse_date(period_start, "--period-start"), _parse_date(period_end, "--period-end")

    end = _parse_date(as_of, "--as-of") if as_of else timezone.localdate()
    if frequency == "monthly":
        start = end.replace(day=1)
        if start >= end:
            previous_day = start - timedelta(days=1)
            start = previous_day.replace(day=1)
    else:
        start = end - timedelta(days=1)
    return start, end


class Command(BaseCommand):
    help = "Accrue effective OL Loan interest and overdue penalties for a daily or monthly period."

    def add_arguments(self, parser):
        parser.add_argument("--as-of", default=timezone.localdate().isoformat())
        parser.add_argument("--frequency", choices=("daily", "monthly"), default="daily")
        parser.add_argument("--period-start")
        parser.add_argument("--period-end")
        parser.add_argument("--loan-id")
        parser.add_argument("--correlation-id")

    def handle(self, *args, **options):
        start, end = _periods(
            options.get("as_of"),
            options["frequency"],
            options.get("period_start"),
            options.get("period_end"),
        )
        if end <= start:
            raise CommandError("The accrual period end must be after the start.")
        correlation_id = options.get("correlation_id") or f"OL-ACCRUAL-{timezone.now():%Y%m%d%H%M%S}-{uuid4().hex[:8].upper()}"
        results, errors = accrue_batch(
            period_start=start,
            period_end=end,
            actor=_system_actor(),
            loan_id=options.get("loan_id"),
            source_channel="BATCH",
            correlation_id=correlation_id,
        )
        created = sum(1 for result in results if result.created)
        replayed = sum(1 for result in results if not result.created)
        self.stdout.write(
            self.style.SUCCESS(
                f"OL interest accrual batch {correlation_id}: processed={len(results)}, created={created}, replayed={replayed}, errors={len(errors)}; period={start}..{end}."
            )
        )
        for error in errors:
            self.stdout.write(self.style.WARNING(f"{error['loan_number']}: {error['error_code']} — {error['message']}"))
        if errors:
            self.stdout.write(self.style.WARNING("The batch completed with per-loan errors; review the warnings and audit row."))
