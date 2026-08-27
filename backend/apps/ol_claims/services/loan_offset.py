from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.governance.services.audit_service import AuditService
from apps.ol_policies.models import LoanStatus, PolicyLoan, PolicyLoanRepayment

from ..errors import registry_error
from ..events import emit_claim_loan_offset_applied
from ..models import ClaimLoanOffsetStatus, OLClaim, OLClaimLoanOffset


ACTIVE_LOAN_STATUSES = (LoanStatus.DISBURSED, LoanStatus.PARTIALLY_REPAID)


def _gross_amount(claim):
    approved = [item.approved_amount for item in claim.items.all() if item.approved_amount is not None]
    return sum(approved, Decimal("0.00")).quantize(Decimal("0.01"))


def _loan_balance(loan):
    return (loan.outstanding_principal + loan.outstanding_interest).quantize(Decimal("0.01"))


def _summary(claim, gross, loan_balance, net, *, applied=False, breakdown=None):
    return {
        "claim_number": claim.claim_number,
        "policy_number": claim.policy_ref.policy_number,
        "currency": claim.policy_ref.currency,
        "gross_amount": gross,
        "loan_offset": loan_balance,
        "net_payout": net,
        "loan_offset_applied": applied,
        "loan_breakdown": breakdown or [],
    }


def calculate_net_payout(claim_id):
    claim = (
        OLClaim.objects.select_related("policy_ref")
        .prefetch_related("items")
        .filter(pk=claim_id)
        .first()
    )
    if not claim:
        raise registry_error("CLAIM_NOT_FOUND")
    gross = _gross_amount(claim)
    active_loans = PolicyLoan.objects.filter(policy_id=claim.policy_ref_id, status__in=ACTIVE_LOAN_STATUSES)
    balance = sum((_loan_balance(loan) for loan in active_loans), Decimal("0.00")).quantize(Decimal("0.01"))
    net = max(gross - balance, Decimal("0.00")).quantize(Decimal("0.01"))
    existing = getattr(claim, "loan_offset", None)
    if existing and existing.status == ClaimLoanOffsetStatus.APPLIED:
        return _summary(
            claim,
            existing.gross_amount,
            existing.offset_amount,
            existing.net_payout,
            applied=True,
            breakdown=existing.loan_breakdown,
        )
    return _summary(claim, gross, balance, net)


@transaction.atomic
def apply_loan_offset(claim_id, *, actor=None, source_channel="API", reason="Claim settlement loan offset.", request=None):
    claim = (
        OLClaim.objects.select_for_update()
        .select_related("policy_ref")
        .prefetch_related("items")
        .filter(pk=claim_id)
        .first()
    )
    if not claim:
        raise registry_error("CLAIM_NOT_FOUND")
    existing = getattr(claim, "loan_offset", None)
    if existing and existing.status == ClaimLoanOffsetStatus.APPLIED:
        return existing
    gross = _gross_amount(claim)
    if gross <= 0:
        raise registry_error(
            "CLAIM_FINANCIAL_SUMMARY_UNAVAILABLE",
            details={"claim_number": claim.claim_number, "gross_amount": str(gross)},
        )

    loans = list(
        PolicyLoan.objects.select_for_update()
        .filter(policy_id=claim.policy_ref_id, status__in=ACTIVE_LOAN_STATUSES)
        .order_by("requested_at", "loan_number")
    )
    total_balance = sum((_loan_balance(loan) for loan in loans), Decimal("0.00")).quantize(Decimal("0.01"))
    if not loans or total_balance <= 0:
        return None

    force_close = total_balance > gross
    remaining_claim_amount = gross
    breakdown = []
    first_loan = loans[0]
    before_loans = [
        {
            "loan_number": loan.loan_number,
            "loan_balance": str(_loan_balance(loan)),
            "outstanding_principal": str(loan.outstanding_principal),
            "outstanding_interest": str(loan.outstanding_interest),
            "status": loan.status,
        }
        for loan in loans
    ]
    for loan in loans:
        principal_before = loan.outstanding_principal
        interest_before = loan.outstanding_interest
        balance_before = _loan_balance(loan)
        if force_close:
            payout_offset = min(balance_before, remaining_claim_amount)
            remaining_claim_amount = max(remaining_claim_amount - payout_offset, Decimal("0.00"))
            principal_component = principal_before
            interest_component = interest_before
            write_off_amount = max(balance_before - payout_offset, Decimal("0.00"))
        else:
            payout_offset = min(balance_before, remaining_claim_amount)
            remaining_claim_amount = max(remaining_claim_amount - payout_offset, Decimal("0.00"))
            interest_component = min(interest_before, payout_offset)
            principal_component = min(principal_before, payout_offset - interest_component)
            write_off_amount = Decimal("0.00")

        loan.outstanding_interest = max(interest_before - interest_component, Decimal("0.00"))
        loan.outstanding_principal = max(principal_before - principal_component, Decimal("0.00"))
        if force_close or (loan.outstanding_interest <= 0 and loan.outstanding_principal <= 0):
            loan.outstanding_interest = Decimal("0.00")
            loan.outstanding_principal = Decimal("0.00")
            loan.status = LoanStatus.REPAID
        else:
            loan.status = LoanStatus.PARTIALLY_REPAID
        loan.updated_by = actor
        loan.save(update_fields=["outstanding_interest", "outstanding_principal", "status", "updated_by", "updated_at"])
        repayment = PolicyLoanRepayment.objects.create(
            loan=loan,
            payment_date=timezone.localdate(),
            amount=(interest_component + principal_component + write_off_amount).quantize(Decimal("0.01")),
            interest_component=interest_component,
            principal_component=principal_component,
            reason=f"Claim {claim.claim_number} loan offset.",
            created_by=actor,
            updated_by=actor,
        )
        breakdown.append(
            {
                "loan_number": loan.loan_number,
                "loan_balance_before": str(balance_before),
                "offset_amount": str(payout_offset.quantize(Decimal("0.01"))),
                "interest_component": str(interest_component.quantize(Decimal("0.01"))),
                "principal_component": str(principal_component.quantize(Decimal("0.01"))),
                "write_off_amount": str(write_off_amount.quantize(Decimal("0.01"))),
                "loan_balance_after": str(_loan_balance(loan)),
                "repayment_number": repayment.repayment_number,
                "status": loan.status,
            }
        )

    offset_amount = gross if force_close else min(total_balance, gross)
    net_payout = max(gross - offset_amount, Decimal("0.00")).quantize(Decimal("0.01"))
    offset = OLClaimLoanOffset.objects.create(
        claim=claim,
        loan=first_loan,
        gross_amount=gross,
        offset_amount=offset_amount.quantize(Decimal("0.01")),
        net_payout=net_payout,
        status=ClaimLoanOffsetStatus.APPLIED,
        reason=reason,
        loan_breakdown=breakdown,
        created_by=actor,
        updated_by=actor,
    )
    emit_claim_loan_offset_applied(
        claim,
        actor=actor,
        reason=reason,
        source_channel=source_channel,
        metadata={
            "gross_amount": str(gross),
            "loan_offset": str(offset.offset_amount),
            "net_payout": str(net_payout),
            "loans": breakdown,
        },
    )
    AuditService.log(
        action_type="LOAN_OFFSET",
        entity_type="ol_claims.claim_loan_offset",
        entity_id=offset.pk,
        entity_repr=claim.claim_number,
        before_state={"claim_number": claim.claim_number, "loans": before_loans},
        after_state={
            "claim_number": claim.claim_number,
            "gross_amount": str(gross),
            "loan_offset": str(offset.offset_amount),
            "net_payout": str(net_payout),
            "loan_breakdown": breakdown,
        },
        description=f"Policy loan offset applied to claim {claim.claim_number}.",
        actor=actor,
        reason=reason,
        source_channel=source_channel,
        request=request,
        app_label="ol_claims",
        model_name="claimloanoffset",
        object_id=str(offset.pk),
        object_repr=str(offset),
    )
    return offset
