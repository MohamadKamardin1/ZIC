from datetime import date

from django.db import transaction
from django.utils import timezone

from apps.governance.models import ApprovalRequest
from apps.governance.services.audit_service import AuditService

from ..errors import LoanError, loan_not_found
from ..events import emit_loan_approved
from ..models import LoanStatus, OLLoan


class LoanApprovalResult:
    def __init__(self, loan, changed):
        self.loan = loan
        self.changed = changed


def _invalid_transition(loan, action):
    raise LoanError(
        f"Loan {loan.loan_number} cannot be {action} from status {loan.get_status_display()}.",
        error_code="LOAN_INVALID_STATUS",
        status_code=409,
        resolution_steps=[
            "Review the current loan status and approval history.",
            f"Only a Requested loan can be {action}.",
            "Complete the preceding loan lifecycle action before retrying.",
        ],
        details={"loan_number": loan.loan_number, "current_status": loan.status, "required_status": LoanStatus.REQUESTED},
    )


def _approval_request_for(loan):
    if loan.approval_request_id:
        return loan.approval_request
    return ApprovalRequest.objects.filter(
        module="OL_LOANS",
        entity_type="OLLoan",
        entity_id=loan.pk,
        status="PENDING",
    ).order_by("-submitted_at").first()


@transaction.atomic
def approve_loan(loan_id, *, actor=None, request=None, reason="", source_channel="API"):
    loan = OLLoan.objects.select_for_update().select_related("policy_ref", "partner").filter(pk=loan_id).first()
    if loan is None:
        raise loan_not_found(str(loan_id))
    if loan.status != LoanStatus.REQUESTED:
        _invalid_transition(loan, "approved")
    if not loan.approval_required:
        raise LoanError(
            f"Loan {loan.loan_number} does not require manual approval.",
            error_code="LOAN_INVALID_STATUS",
            status_code=409,
            resolution_steps=[
                "Proceed to the configured disbursement workflow if all other checks are complete.",
                "Ask an administrator to review the Loan System Setup approval threshold if this is unexpected.",
            ],
        )
    now = timezone.now()
    before = AuditService.snapshot(loan)
    loan.status = LoanStatus.APPROVED
    loan.approved_by = actor
    loan.approved_at = now
    loan.updated_by = actor
    loan.save(update_fields=["status", "approved_by", "approved_at", "updated_by", "updated_at"])

    approval_request = _approval_request_for(loan)
    if approval_request:
        approval_request.status = "APPROVED"
        approval_request.reviewed_by = actor
        approval_request.reviewed_at = now
        approval_request.comments = reason or "Loan approved."
        approval_request.current_data = {"status": loan.status, "approved_at": now.isoformat()}
        approval_request.save(update_fields=["status", "reviewed_by", "reviewed_at", "comments", "current_data", "updated_at"])
        if not loan.approval_request_id:
            loan.approval_request = approval_request
            loan.save(update_fields=["approval_request", "updated_at"])

    after = AuditService.snapshot(loan)
    AuditService.log_action(
        "LOAN_APPROVED",
        loan,
        actor=actor,
        request=request,
        before_state=before,
        after_state=after,
        changed_fields=["status", "approved_by", "approved_at"],
        reason=reason or "Loan approved.",
        source_channel=source_channel,
    )
    emit_loan_approved(
        loan,
        actor=actor,
        from_status=before.get("status", ""),
        reason=reason or "Loan approved.",
        source_channel=source_channel,
    )
    return LoanApprovalResult(loan, True)


@transaction.atomic
def reject_loan(loan_id, *, reason, actor=None, request=None, source_channel="API"):
    reason = str(reason or "").strip()
    if not reason:
        raise LoanError(
            "A reason is required when rejecting a loan request.",
            error_code="LOAN_INVALID_STATUS",
            status_code=422,
            resolution_steps=[
                "Explain why the loan request cannot proceed.",
                "Include the reason in the rejection form and submit again.",
            ],
            field_errors={"reason": ["Rejection reason is required."]},
        )
    loan = OLLoan.objects.select_for_update().select_related("policy_ref", "partner").filter(pk=loan_id).first()
    if loan is None:
        raise loan_not_found(str(loan_id))
    if loan.status != LoanStatus.REQUESTED:
        _invalid_transition(loan, "rejected")
    now = timezone.now()
    before = AuditService.snapshot(loan)
    loan.status = LoanStatus.REJECTED
    loan.rejected_by = actor
    loan.rejected_at = now
    loan.rejection_reason = reason
    loan.updated_by = actor
    loan.save(update_fields=["status", "rejected_by", "rejected_at", "rejection_reason", "updated_by", "updated_at"])

    approval_request = _approval_request_for(loan)
    if approval_request:
        approval_request.status = "REJECTED"
        approval_request.reviewed_by = actor
        approval_request.reviewed_at = now
        approval_request.comments = reason
        approval_request.current_data = {"status": loan.status, "rejection_reason": reason}
        approval_request.save(update_fields=["status", "reviewed_by", "reviewed_at", "comments", "current_data", "updated_at"])

    AuditService.log_action(
        "LOAN_REJECTED",
        loan,
        actor=actor,
        request=request,
        before_state=before,
        after_state=AuditService.snapshot(loan),
        changed_fields=["status", "rejected_by", "rejected_at", "rejection_reason"],
        reason=reason,
        source_channel=source_channel,
    )
    return LoanApprovalResult(loan, True)


def bulk_approve(loan_ids, *, actor=None, request=None, source_channel="API"):
    results = []
    errors = []
    for loan_id in loan_ids:
        try:
            result = approve_loan(loan_id, actor=actor, request=request, source_channel=source_channel)
            results.append({"loan_id": str(result.loan.pk), "loan_number": result.loan.loan_number, "status": result.loan.status})
        except LoanError as exc:
            errors.append({"loan_id": str(loan_id), "error_code": exc.error_code, "message": str(exc), "resolution_steps": exc.resolution_steps})
    return results, errors


def bulk_reject(loan_ids, *, reason, actor=None, request=None, source_channel="API"):
    results = []
    errors = []
    for loan_id in loan_ids:
        try:
            result = reject_loan(loan_id, reason=reason, actor=actor, request=request, source_channel=source_channel)
            results.append({"loan_id": str(result.loan.pk), "loan_number": result.loan.loan_number, "status": result.loan.status})
        except LoanError as exc:
            errors.append({"loan_id": str(loan_id), "error_code": exc.error_code, "message": str(exc), "resolution_steps": exc.resolution_steps})
    return results, errors
