from ..models import LoanStatus
from ..permissions import has_ol_loan_permission


_BASE_ACTIONS = {
    LoanStatus.REQUESTED: {"view", "approve", "reject", "print"},
    LoanStatus.APPROVED: {"view", "disburse", "print"},
    LoanStatus.DISBURSED: {"view", "repay", "offset", "print"},
    LoanStatus.ACTIVE: {"view", "repay", "offset", "print"},
    LoanStatus.PARTIALLY_REPAID: {"view", "repay", "offset", "print"},
    LoanStatus.DEFAULTED: {"view", "repay", "offset", "print"},
    LoanStatus.SETTLED: {"view", "print"},
    LoanStatus.OFFSET_ON_SURRENDER: {"view", "print"},
    LoanStatus.OFFSET_ON_MATURITY: {"view", "print"},
    LoanStatus.OFFSET_ON_CLAIM: {"view", "print"},
    LoanStatus.CLOSED: {"view", "print"},
    LoanStatus.REJECTED: {"view", "print"},
}

_PERMISSION_BY_ACTION = {
    "approve": "approve",
    "reject": "approve",
    "disburse": "disburse",
    "repay": "repay",
    "offset": "offset",
    "print": "print",
}


def allowed_actions(loan, user=None):
    """Return deterministic action codes allowed for this user and loan status."""
    actions = set(_BASE_ACTIONS.get(loan.status, {"view"}))
    if user is None:
        actions.discard("view")
        return []
    visible = {"view"}
    for action in actions - {"view"}:
        permission = _PERMISSION_BY_ACTION.get(action)
        if permission and has_ol_loan_permission(user, permission):
            visible.add(action)
    if not has_ol_loan_permission(user, "view"):
        return []
    return sorted(visible)
