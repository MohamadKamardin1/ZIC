import json

from django.core.management.base import BaseCommand, CommandError

from apps.ol_loans.services.audit_consistency import verify_loan_audit_consistency


class Command(BaseCommand):
    help = "Verify central audit coverage and orphan records for OL Loans."

    def add_arguments(self, parser):
        parser.add_argument("--loan-id", action="append", dest="loan_ids", help="Limit the check to one or more loan UUIDs.")
        parser.add_argument("--json", action="store_true", dest="as_json", help="Print the full report as JSON.")

    def handle(self, *args, **options):
        report = verify_loan_audit_consistency(loan_ids=options.get("loan_ids"))
        if options.get("as_json"):
            self.stdout.write(json.dumps(report, default=str, sort_keys=True))
        else:
            self.stdout.write(
                "OL Loan audit consistency: "
                f"{'PASS' if report['passed'] else 'FAIL'}; "
                f"loans={report['loan_count']}; "
                f"audited={report['audited_loan_count']}; "
                f"audit_rows={report['audit_row_count']}; "
                f"missing={len(report['missing_audit_loans'])}; "
                f"orphans={len(report['orphan_audit_records'])}"
            )
        if not report["passed"]:
            raise CommandError("OL Loan audit consistency failed; inspect the report for missing or orphan records.")
