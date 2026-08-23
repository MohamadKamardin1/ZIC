"""First-premium commitment tracking and BR-03 posting guard.

The proposals module links the first-premium commitment (``source_type``
``PROPOSAL``, ``installment_number`` ``1``) exactly once when a proposal
becomes payment-ready, then only ever *reads* the commitment state. Receipt
allocation is owned by the future receipts module (see
``docs/OL_PROPOSALS_RECEIPTS_SEAM.md``); this module's guard
``first_premium_posted`` is the single airtight source of truth for BR-03 and
is reusable by the receipts and policies modules.
"""

from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib.contenttypes.models import ContentType

from apps.governance.services.audit_service import AuditService
from apps.ol_commitments.events import emit_generated as emit_commitment_generated
from apps.ol_commitments.models import CommitmentSourceType, OLCommitment
from apps.ol_proposals.errors import ProposalError, first_premium_not_posted
from apps.ol_proposals.models import OLProposal
from apps.system_parameters.services.numbering_service import NumberingEngine

COMPLETED = "COMPLETED"
ZERO = Decimal("0.00")


def _resolve_premium(proposal):
    """First-premium amount from selected plan configs, then the financial snapshot."""
    total = ZERO
    for config in proposal.plan_configs.filter(is_selected=True):
        if config.premium_amount is not None and config.premium_amount > 0:
            total += Decimal(str(config.premium_amount))
    if total > 0:
        return total
    snapshot = proposal.financial_summary_snapshot
    if isinstance(snapshot, dict):
        for key in ("total_premium", "premium_amount"):
            raw = snapshot.get(key)
            if raw is None:
                continue
            try:
                value = Decimal(str(raw))
            except (InvalidOperation, TypeError, ValueError):
                continue
            if value > 0:
                return value
    return ZERO


def link_first_premium_commitment(*, proposal, actor=None, request=None, source_channel="API"):
    """Link (and create once) the proposal's first-premium commitment.

    Idempotent: locates the existing ``PROPOSAL`` commitment for installment 1
    (or the already-linked reference) before creating. Returns
    ``(commitment, created)``.
    """
    from apps.ol_commitments.models import CommitmentSourceChannel

    if proposal.first_premium_commitment_id:
        return proposal.first_premium_commitment, False

    content_type = ContentType.objects.get_for_model(OLProposal)
    existing = (
        OLCommitment.objects.filter(
            source_content_type=content_type,
            source_object_id=str(proposal.pk),
            installment_number=1,
        )
        .order_by("-created_at")
        .first()
    )
    if existing is not None:
        proposal.first_premium_commitment = existing
        proposal.save(update_fields=["first_premium_commitment"])
        return existing, False

    premium_amount = _resolve_premium(proposal)
    if premium_amount <= 0:
        raise ProposalError(
            "The proposal first-premium amount cannot be determined.",
            error_code="PROPOSAL_ERROR",
            status_code=422,
            resolution_steps=[
                "Confirm the proposal has a selected plan configuration with a premium amount.",
                "Recalculate the source quotation if the financial snapshot is empty.",
                "Re-run payment readiness afterwards.",
            ],
        )

    plan_config = proposal.plan_configs.filter(is_selected=True).first()
    commitment = OLCommitment.objects.create(
        commitment_number=NumberingEngine.generate_number("OL_COMMITMENT", OLCommitment, field_name="commitment_number"),
        source_type=CommitmentSourceType.PROPOSAL,
        source_content_type=content_type,
        source_object_id=str(proposal.pk),
        source_reference=proposal.proposal_number,
        partner=proposal.partner,
        partner_name_snapshot=proposal.partner_name_snapshot,
        product=None,
        plan=plan_config.plan if plan_config else None,
        currency=proposal.currency,
        premium_frequency=(plan_config.premium_frequency or "").strip().upper() if plan_config else "",
        installment_number=1,
        installment_count=1,
        due_date=date.today(),
        premium_amount=premium_amount,
        status="",
        source_channel=CommitmentSourceChannel.API if source_channel == "API" else CommitmentSourceChannel.SYSTEM,
    )

    proposal.first_premium_commitment = commitment
    proposal.save(update_fields=["first_premium_commitment"])

    AuditService.log_action(
        "LINK_FIRST_PREMIUM_COMMITMENT",
        proposal,
        actor=actor,
        request=request,
        after_state={
            "commitment": commitment.commitment_number,
            "premium_amount": str(commitment.premium_amount),
            "status": commitment.status,
        },
        changed_fields=["first_premium_commitment"],
        reason=f"First premium commitment {commitment.commitment_number} linked to proposal.",
        source_channel=source_channel,
    )
    emit_commitment_generated(
        commitment,
        actor=actor,
        reason="First premium commitment generated at payment readiness.",
        source_channel=source_channel,
        metadata={"proposal_id": str(proposal.pk), "proposal_number": proposal.proposal_number},
    )
    return commitment, True


def first_premium_posted(proposal):
    """BR-03 guard: posted only when the linked commitment is Completed and fully allocated."""
    commitment = proposal.first_premium_commitment
    if commitment is None:
        return False
    posted = (commitment.status or "").strip().upper() == COMPLETED
    paid = Decimal(str(commitment.amount_paid or ZERO)) + Decimal(str(commitment.amount_waived or ZERO))
    return posted and paid >= Decimal(str(commitment.premium_amount or ZERO))


def ensure_first_premium_posted(proposal):
    """Raise PROPOSAL_FIRST_PREMIUM_NOT_POSTED when the BR-03 guard fails."""
    if not first_premium_posted(proposal):
        raise first_premium_not_posted()
    return True


def first_premium_status(proposal):
    """Read-only payment status payload with next-action hints.

    Reads the linked commitment and its allocations; never writes to the
    commitments module (receipts own allocation writes).
    """
    commitment = proposal.first_premium_commitment
    if commitment is None:
        return {
            "linked": False,
            "commitment": None,
            "first_premium_posted": False,
            "next_actions": ["Mark the proposal payment-ready to generate the first premium commitment."],
        }

    allocations = list(
        commitment.allocations.filter(reversal_of__isnull=True).order_by("-allocated_at", "-created_at")
    )
    payment_modes = sorted({item.payment_mode for item in allocations if item.payment_mode})
    last_allocation = allocations[0] if allocations else None
    posted = first_premium_posted(proposal)

    if posted:
        next_actions = ["Proceed to policy conversion (first premium is fully allocated)."]
    elif proposal.status == "AWAITING_FIRST_PREMIUM" or proposal.payment_ready:
        next_actions = [
            "Record receipt in Front Office.",
            f"Allocate the receipt against commitment {commitment.commitment_number}.",
        ]
    else:
        next_actions = ["Mark the proposal payment-ready to generate the first premium commitment."]

    return {
        "linked": True,
        "commitment": {
            "commitment_number": commitment.commitment_number,
            "status": commitment.status,
            "amount_due": str(commitment.premium_amount),
            "amount_paid": str(commitment.amount_paid),
            "balance": str(commitment.balance),
            "payment_modes": payment_modes,
            "payment_mode": last_allocation.payment_mode if last_allocation else "",
            "last_payment_date": last_allocation.allocated_at.isoformat() if last_allocation else None,
            "allocations": [
                {
                    "receipt_reference": item.receipt_reference,
                    "amount": str(item.amount),
                    "payment_mode": item.payment_mode,
                    "currency": item.currency,
                    "allocated_at": item.allocated_at.isoformat(),
                }
                for item in allocations
            ],
        },
        "first_premium_posted": posted,
        "next_actions": next_actions,
    }