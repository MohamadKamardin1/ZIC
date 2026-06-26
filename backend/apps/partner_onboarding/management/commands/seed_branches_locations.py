from django.core.management.base import BaseCommand
from apps.partner_onboarding.models import Branch, Location


BRANCHES = [
    ("HQ", "Head Office — Dar es Salaam"),
    ("DSM-UP", "Upanga Branch — Dar es Salaam"),
    ("DSM-KA", "Kariakoo Branch — Dar es Salaam"),
    ("MZA", "Mwanza Branch"),
    ("ARU", "Arusha Branch"),
    ("MBE", "Mbeya Branch"),
    ("TAN", "Tanga Branch"),
    ("ZNZ", "Zanzibar Branch"),
    ("DOD", "Dodoma Branch"),
    ("MWA", "Mtwara Branch"),
]

LOCATIONS_PER_BRANCH = [
    "Main Office",
    "Customer Service Desk",
    "Claims Processing",
    "Underwriting",
    "Finance & Accounts",
    "HR Office",
    "IT Support",
    "Legal & Compliance",
    "Executive Suite",
    "Archives & Records",
]


class Command(BaseCommand):
    help = "Seed 10 branches and 10 locations per branch"

    def handle(self, *args, **options):
        created_branches = 0
        created_locations = 0

        for code, name in BRANCHES:
            branch, was_created = Branch.objects.get_or_create(
                code=code,
                defaults={"name": name, "is_active": True},
            )
            if was_created:
                created_branches += 1
                self.stdout.write(f"  Created branch: {code} — {name}")
            else:
                self.stdout.write(f"  Already exists: {code}")

            for loc_name in LOCATIONS_PER_BRANCH:
                loc_code = f"{code}-{loc_name[:2].upper()}{loc_name[-2:].upper()}"
                _, loc_created = Location.objects.get_or_create(
                    branch=branch,
                    code=loc_code,
                    defaults={"name": loc_name, "is_active": True},
                )
                if loc_created:
                    created_locations += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Created {created_branches} branches, {created_locations} locations."
        ))
