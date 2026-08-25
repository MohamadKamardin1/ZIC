"""Prove BR-03 end-to-end through the real services (Prompt 12).

Replays the first-premium lifecycle:
  1. a linked-but-unallocated proposal CANNOT convert (guard raises)
  2. once the first-premium receipt fully allocates the commitment, the
     proposal CAN convert to a policy
  3. reversing that receipt makes the guard evaluate ``False`` again — but the
     already-issued policy is NOT revoked: a re-conversion returns the existing
     policy idempotently (the converted_policy check precedes the guard)

The command is re-runnable: each proof step skips work already reflected in the
database and records whether it ran fresh or was already in that state.
"""

import json

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.front_office.receipts.models import ReceiptAllocationTargetType, ReceiptSourceModule
from apps.front_office.receipts.seed_data import (
    get_partner,
    get_seed_user,
    link_first_premium,
    make_proposal,
    scenario_receipt,
    seed_commitment_statuses,
)
from apps.front_office.receipts.services.allocation_service import allocate
from apps.front_office.receipts.services.receipt_service import create_draft, post_receipt
from apps.front_office.receipts.services.reversal_service import reverse_receipt
from apps.ol_proposals.errors import ProposalError
from apps.ol_proposals.services.first_premium_service import first_premium_posted
from apps.ol_proposals.services.policy_conversion_service import convert_proposal_to_policy

POST_POLICY_REVERSAL_ASSUMPTION = (
    "Once a proposal has converted to a policy, reversing its first-premium "
    "receipt restores the commitment balance and makes the BR-03 guard evaluate "
    "False again, but it does NOT revoke the issued policy. Conversion is "
    "idempotent: the converted_policy_id check precedes the guard, so a "
    "re-conversion returns the existing policy. Operators must not reverse "
    "first-premium receipts after policy issue without a compensating "
    "adjustment; this is a documented operational assumption, not an enforced block."
)


def _error_payload(exc):
    return {
        "code": getattr(exc, "error_code", "PROPOSAL_ERROR"),
        "status_code": getattr(exc, "status_code", 500),
        "message": str(exc) or "The operation was rejected.",
        "resolution_steps": getattr(exc, "resolution_steps", None) or [],
    }


class Command(BaseCommand):
    help = "Verify the BR-03 first-premium gate through the real services (Prompt 12)."

    def handle(self, *args, **options):
        results = run_verification()
        self.stdout.write(json.dumps(results, indent=2, sort_keys=True))
        self.stdout.write("")
        self.stdout.write(self.style.WARNING(f"Post-policy reversal assumption: {POST_POLICY_REVERSAL_ASSUMPTION}"))
        all_pass = all(step.get("passed", False) for step in results["steps"].values())
        self.stdout.write(
            self.style.SUCCESS("BR-03 verification: " + ("PASSED" if all_pass else "FAILED"))
        )


def run_verification():
    """Execute the BR-03 state machine; returns a structured verification result."""
    call_command("seed_receipt_parameters")
    seed_commitment_statuses()
    actor = get_seed_user()

    steps = {}
    steps["guard_blocks_before_allocation"] = _blocked_proposal(actor)
    full = _full_lifecycle(actor)
    steps["converts_after_full_allocation"] = full["conversion"]
    steps["guard_false_after_reversal"] = full["reversal"]
    steps["reconversion_returns_existing_policy"] = full["reconversion"]

    return {
        "br03": "first premium must be fully allocated to the linked commitment before a proposal converts to a policy",
        "steps": steps,
        "all_passed": all(step.get("passed", False) for step in steps.values()),
    }


def _blocked_proposal(actor):
    partner = get_partner("SEEDBR03P1", first_name="Baraka", surname="Mugisha")
    proposal = make_proposal("SEED-BR03-BLOCKED", "100000.00", partner)
    commitment, _ = link_first_premium(proposal, actor=actor)
    posted_before = first_premium_posted(proposal)
    try:
        convert_proposal_to_policy(proposal=proposal, actor=actor, source_channel="SYSTEM")
        caught = None
    except ProposalError as exc:
        caught = _error_payload(exc)
    passed = (
        posted_before is False
        and caught is not None
        and caught["code"] == "PROPOSAL_FIRST_PREMIUM_NOT_POSTED"
    )
    return {
        "proposal": proposal.proposal_number,
        "commitment": commitment.commitment_number,
        "first_premium_posted": posted_before,
        "conversion_attempted": True,
        "expected_error": "PROPOSAL_FIRST_PREMIUM_NOT_POSTED",
        "caught_error": caught,
        "passed": passed,
    }


def _full_lifecycle(actor):
    partner = get_partner("SEEDBR03P2", first_name="Zawadi", surname="Kessy")
    proposal = make_proposal("SEED-BR03-FULL", "100000.00", partner)
    commitment, _ = link_first_premium(proposal, actor=actor)
    receipt_key = "SEED-BR03-RECEIPT-FULL"
    receipt = scenario_receipt(receipt_key)
    if receipt is None:
        receipt, _created = create_draft(
            actor=actor,
            source_channel="SYSTEM",
            idempotency_key=receipt_key,
            receipt_date=timezone.localdate(),
            branch_id=None,
            partner_id=partner.pk,
            payer_name=str(partner),
            source_module=ReceiptSourceModule.OL_PROPOSAL,
            source_reference_type="PROPOSAL_NUMBER",
            source_reference_id=proposal.proposal_number,
            receipt_amount="100000.00",
            currency="TZS",
            payment_mode="CASH",
            narration=f"BR-03 verify: first premium for {proposal.proposal_number}.",
        )
        post_receipt(receipt, actor=actor, reason="BR-03 verify: first premium confirmed.", source_channel="SYSTEM")
    if receipt.status in ("POSTED", "PARTIALLY_ALLOCATED"):
        allocate(
            receipt,
            target_type=ReceiptAllocationTargetType.OL_COMMITMENT,
            target_id=commitment.commitment_number,
            amount="100000.00",
            narration="BR-03 verify: full first-premium allocation.",
            actor=actor,
            source_channel="SYSTEM",
        )
    proposal.refresh_from_db()
    posted_after = first_premium_posted(proposal)

    # Conversion
    created_this_run = False
    if proposal.converted_policy_id is None:
        policy, created_this_run = convert_proposal_to_policy(
            proposal=proposal, actor=actor, source_channel="SYSTEM"
        )
        policy_id = policy.pk
        policy_number = policy.policy_number
    else:
        policy = proposal.converted_policy
        policy_id = policy.pk
        policy_number = policy.policy_number
    conversion = {
        "proposal": proposal.proposal_number,
        "commitment": commitment.commitment_number,
        "receipt": receipt.receipt_number or str(receipt.pk),
        "first_premium_posted": posted_after,
        "policy_number": policy_number,
        "policy_created_this_run": created_this_run,
        "expected": "converts after full allocation",
        "passed": bool(policy_number),
    }

    # Reversal after policy issue
    if receipt.status != "REVERSED":
        reverse_receipt(
            receipt,
            reason="BR-03 verify: post-policy reversal proof.",
            actor=actor,
            source_channel="SYSTEM",
        )
        reversal_ran = True
    else:
        reversal_ran = False
    proposal.refresh_from_db()
    guard_after_reversal = first_premium_posted(proposal)
    reversal = {
        "proposal": proposal.proposal_number,
        "receipt": receipt.receipt_number or str(receipt.pk),
        "reversal_performed": reversal_ran,
        "first_premium_posted_after_reversal": guard_after_reversal,
        "policy_still_issued": proposal.converted_policy_id is not None,
        "expected": "guard evaluates False after reversal, but the issued policy is untouched",
        "passed": guard_after_reversal is False and proposal.converted_policy_id is not None,
    }

    # Re-conversion must return the existing policy (guard false does not un-issue)
    reconverted, reconverted_created = convert_proposal_to_policy(
        proposal=proposal, actor=actor, source_channel="SYSTEM"
    )
    reconversion = {
        "proposal": proposal.proposal_number,
        "reconverted_policy_number": reconverted.policy_number,
        "created_a_new_policy": reconverted_created,
        "returns_existing_policy": reconverted.pk == policy_id,
        "expected": "re-conversion returns the existing policy, never a duplicate",
        "passed": (not reconverted_created) and reconverted.pk == policy_id,
    }

    return {"conversion": conversion, "reversal": reversal, "reconversion": reconversion}
