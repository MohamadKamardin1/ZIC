from rest_framework.permissions import BasePermission

OL_COMMITMENTS_MODULE = "ol_commitments"

ACTIONS = ("view", "create", "generate", "record_payment", "reverse", "suspend", "waive", "cancel", "reschedule")


class OLCommitmentPermission:
    VIEW = "ol_commitments.view"
    CREATE = "ol_commitments.create"
    GENERATE = "ol_commitments.generate"
    RECORD_PAYMENT = "ol_commitments.record_payment"
    REVERSE = "ol_commitments.reverse"
    SUSPEND = "ol_commitments.suspend"
    WAIVE = "ol_commitments.waive"
    CANCEL = "ol_commitments.cancel"
    RESCHEDULE = "ol_commitments.reschedule"

    ACTION_TO_CODE = {
        "list": VIEW,
        "retrieve": VIEW,
        "view": VIEW,
        "export": VIEW,
        "kpi": VIEW,
        "create": CREATE,
        "manual": CREATE,
        "generate": GENERATE,
        "generate_from_proposal": GENERATE,
        "generate_from_policy": GENERATE,
        "regenerate": GENERATE,
        "record_payment": RECORD_PAYMENT,
        "allocate": RECORD_PAYMENT,
        "process_overdue": GENERATE,
        "reverse": REVERSE,
        "reverse_allocation": REVERSE,
        "suspend": SUSPEND,
        "reactivate": SUSPEND,
        "waive": WAIVE,
        "cancel": CANCEL,
        "reschedule": RESCHEDULE,
    }

    @classmethod
    def code_for(cls, action):
        return cls.ACTION_TO_CODE.get((action or "").lower(), cls.VIEW)

    @classmethod
    def allowed_codes(cls):
        return tuple(f"{OL_COMMITMENTS_MODULE}.{action}" for action in ACTIONS)


def has_ol_commitment_permission(actor, action="view"):
    """Return whether an actor may perform an OL Commitments action."""
    if not actor or not getattr(actor, "is_authenticated", False):
        return False
    if getattr(actor, "is_superuser", False):
        return True
    code = OLCommitmentPermission.code_for(action)
    if hasattr(actor, "has_permission") and actor.has_permission(code):
        return True
    if action in {"list", "retrieve", "view", "export", "kpi"}:
        if hasattr(actor, "has_module_permission") and actor.has_module_permission(OL_COMMITMENTS_MODULE, "READ"):
            return True
    module_action = code.rsplit(".", 1)[-1].upper()
    return bool(
        hasattr(actor, "has_module_permission")
        and any(
            actor.has_module_permission(OL_COMMITMENTS_MODULE, candidate) for candidate in (module_action, "CONFIGURE")
        )
    )


class HasOLCommitmentPermission(BasePermission):
    """DRF permission using the view action's OL Commitments entitlement."""

    def has_permission(self, request, view):
        action = getattr(view, "action", None) or request.method.lower()
        return has_ol_commitment_permission(request.user, action)
