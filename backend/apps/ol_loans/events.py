from apps.common.models import DomainEvent


AGGREGATE_TYPE = "OLLoan"

LOAN_REQUESTED = "LoanRequested"
LOAN_APPROVED = "LoanApproved"
LOAN_DISBURSED = "LoanDisbursed"
LOAN_INTEREST_ACCRUED = "LoanInterestAccrued"
LOAN_REPAID = "LoanRepaid"
LOAN_DEFAULTED = "LoanDefaulted"
LOAN_OFFSET = "LoanOffset"
LOAN_SETTLED = "LoanSettled"

EVENT_TYPES = (
    LOAN_REQUESTED,
    LOAN_APPROVED,
    LOAN_DISBURSED,
    LOAN_INTEREST_ACCRUED,
    LOAN_REPAID,
    LOAN_DEFAULTED,
    LOAN_OFFSET,
    LOAN_SETTLED,
)


def emit_loan_event(
    event_type,
    loan,
    *,
    actor=None,
    from_status="",
    to_status="",
    reason="",
    source_channel=None,
    metadata=None,
    payload_extra=None,
):
    """Persist a loan event to the common reliable outbox."""
    payload = {
        "loan_number": loan.loan_number,
        "loan_id": str(loan.pk),
        "policy_id": str(loan.policy_ref_id) if loan.policy_ref_id else None,
        "partner_id": str(loan.partner_id) if loan.partner_id else None,
        "actor_id": str(actor.pk) if actor and getattr(actor, "pk", None) else None,
        "from_status": from_status or "",
        "to_status": to_status or getattr(loan, "status", ""),
        "reason": reason or getattr(loan, "reason", ""),
        "source_channel": source_channel or getattr(loan, "source_channel", ""),
        "metadata": metadata or {},
    }
    if payload_extra:
        payload.update(payload_extra)
    return DomainEvent.objects.create(
        event_type=event_type,
        aggregate_type=AGGREGATE_TYPE,
        aggregate_id=str(loan.pk),
        payload=payload,
    )


def emit_loan_requested(loan, **kwargs):
    return emit_loan_event(LOAN_REQUESTED, loan, to_status=loan.status, **kwargs)


def emit_loan_approved(loan, **kwargs):
    return emit_loan_event(LOAN_APPROVED, loan, to_status=loan.status, **kwargs)


def emit_loan_disbursed(loan, **kwargs):
    return emit_loan_event(LOAN_DISBURSED, loan, to_status=loan.status, **kwargs)


def emit_loan_interest_accrued(loan, **kwargs):
    return emit_loan_event(LOAN_INTEREST_ACCRUED, loan, to_status=loan.status, **kwargs)


def emit_loan_repaid(loan, **kwargs):
    return emit_loan_event(LOAN_REPAID, loan, to_status=loan.status, **kwargs)


def emit_loan_defaulted(loan, **kwargs):
    return emit_loan_event(LOAN_DEFAULTED, loan, to_status=loan.status, **kwargs)


def emit_loan_offset(loan, **kwargs):
    return emit_loan_event(LOAN_OFFSET, loan, to_status=loan.status, **kwargs)


def emit_loan_settled(loan, **kwargs):
    return emit_loan_event(LOAN_SETTLED, loan, to_status=loan.status, **kwargs)
