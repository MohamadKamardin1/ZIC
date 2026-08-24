"""Audit consistency utility covering OL proposal actions.

Verifies that every materially significant proposal state is backed by the
audit trail: terminal statuses must have an audit row that produced them, every
recorded ``after_state.status`` must be a valid catalog code, and the proposal
must not be entirely un-audited.
"""

from apps.governance.models import AuditLog
from apps.ol_proposals.errors import ProposalError

TERMINAL_REQUIREMENTS = {
    "CANCELLED": {"actions": ("PROPOSAL_TRANSITION", "CANCELLED"), "status_in_after": "CANCELLED"},
    "EXPIRED": {"actions": ("PROPOSAL_EXPIRE", "EXPIRED"), "status_in_after": "EXPIRED"},
    "CONVERTED": {"actions": ("PROPOSAL_TRANSITION", "CONVERT"), "status_in_after": "CONVERTED"},
}


def proposal_audit_rows(proposal):
    return list(AuditLog.objects.filter(object_id=str(proposal.pk)).order_by("created_at", "id"))


def audit_actions(proposal):
    return list(dict.fromkeys(row.action for row in proposal_audit_rows(proposal)))


def audit_consistency(proposal):
    """Assess audit coverage for a proposal; returns a consistency report."""
    from apps.ol_proposals.services.parameter_resolver import is_valid_proposal_status

    rows = proposal_audit_rows(proposal)
    actions = [row.action for row in rows]
    problems = []

    if not rows:
        problems.append("No audit trail exists for this proposal.")

    status = (proposal.status or "").strip().upper()
    requirement = TERMINAL_REQUIREMENTS.get(status)
    if requirement:
        matched = [
            row
            for row in rows
            if row.action in requirement["actions"]
            and (row.after_state or {}).get("status") == requirement["status_in_after"]
        ]
        if not matched:
            actions_label = ", ".join(requirement["actions"])
            problems.append(
                f"Terminal status '{status}' lacks an audit action producing it (expected {actions_label})."
            )

    for row in rows:
        after_status = (row.after_state or {}).get("status", "")
        if after_status and is_valid_proposal_status(after_status, allow_empty_catalog=True) is False:
            problems.append(f"Audit row '{row.action}' records an invalid status '{after_status}'.")

    return {
        "proposal": proposal.proposal_number,
        "status": proposal.status,
        "audit_actions": actions,
        "audit_count": len(rows),
        "consistent": not problems,
        "problems": problems,
    }


def ensure_audit_consistency(proposal):
    """Raise a teachable error when the audit trail is inconsistent."""
    report = audit_consistency(proposal)
    if not report["consistent"]:
        raise ProposalError(
            "The proposal audit trail is inconsistent.",
            error_code="PROPOSAL_AUDIT_INCONSISTENT",
            status_code=422,
            resolution_steps=report["problems"],
        )
    return report