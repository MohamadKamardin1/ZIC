from django.utils import timezone

from apps.governance.models import AuditLog

from ..models import OLLoan


LOAN_AUDIT_MODEL = "olloan"


def verify_loan_audit_consistency(*, loan_ids=None):
    """Return a deterministic audit coverage report for OL Loan actions.

    The check is intentionally read-only. It compares central audit rows whose
    normalized source is ``ol_loans.olloan`` with the current loan resource
    table, so missing and orphan records can be reconciled without mutating
    financial data.
    """
    loans = OLLoan.objects.only("id", "loan_number").order_by("loan_number")
    if loan_ids is not None:
        normalized_ids = {str(value) for value in loan_ids}
        loans = loans.filter(pk__in=normalized_ids)
    loan_rows = list(loans)
    loan_by_id = {str(loan.pk): loan for loan in loan_rows}
    audit_rows = list(
        AuditLog.objects.filter(app_label="ol_loans", model_name=LOAN_AUDIT_MODEL)
        .only("id", "object_id", "action", "action_type", "object_repr", "created_at", "source_channel")
        .order_by("object_id", "created_at", "id")
    )
    audit_by_object = {}
    orphan_records = []
    for row in audit_rows:
        object_id = str(row.object_id or "")
        if object_id not in loan_by_id:
            orphan_records.append(
                {
                    "audit_id": str(row.pk),
                    "object_id": object_id,
                    "action": row.action or row.action_type,
                    "object_repr": row.object_repr,
                    "created_at": row.created_at,
                    "source_channel": row.source_channel,
                }
            )
            continue
        audit_by_object.setdefault(object_id, []).append(row)

    missing_loans = [
        {"loan_id": str(loan.pk), "loan_number": loan.loan_number}
        for loan in loan_rows
        if str(loan.pk) not in audit_by_object
    ]
    covered = len(loan_rows) - len(missing_loans)
    return {
        "passed": not missing_loans and not orphan_records,
        "checked_at": timezone.now(),
        "loan_count": len(loan_rows),
        "audited_loan_count": covered,
        "audit_row_count": sum(len(rows) for rows in audit_by_object.values()),
        "missing_audit_loans": missing_loans,
        "orphan_audit_records": orphan_records,
    }
