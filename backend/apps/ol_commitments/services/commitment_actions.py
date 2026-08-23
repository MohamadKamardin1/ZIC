"""Allowed-action computation for OL Commitments.

Mirrors the transition matrix in docs/OL_COMMITMENTS_DESIGN.md and feeds
permission + state gating for both the UI (detail allowed actions) and the
lifecycle action endpoint.
"""


STATUS_ACTIONS = {
    "PENDING": ["record_payment", "suspend", "waive", "cancel", "reschedule"],
    "PARTIALLY_PAID": ["record_payment", "suspend", "waive", "cancel", "reschedule"],
    "ACTIVE": ["record_payment", "suspend", "waive", "cancel", "reschedule"],
    "OVERDUE": ["record_payment", "suspend", "waive", "cancel", "reschedule"],
    "SUSPENDED": ["reactivate", "cancel"],
    "WAIVED": ["view"],
    "COMPLETED": ["view"],
    "CANCELLED": ["view"],
}

LIFECYCLE_ACTIONS = ("suspend", "reactivate", "waive", "cancel", "reschedule")


def allowed_actions(commitment):
    """Return the action codes allowed for a commitment state (permission-agnostic)."""
    status = (commitment.status or "").upper()
    actions = list(STATUS_ACTIONS.get(status, []))
    if commitment.pk and commitment.allocations.filter(reversal_of__isnull=True).exists():
        if "reverse" not in actions:
            actions.append("reverse")
    if "view" not in actions:
        actions.append("view")
    return actions


def is_allowed_action(commitment, action):
    return action in allowed_actions(commitment)