from django.core.exceptions import ValidationError

from ..models import validate_policy_status_transition_graph


class OLPolicySetupService:
    """Application services specific to Policy Setup cross-record invariants."""

    @staticmethod
    def validate_status_transitions(*, queryset=None):
        validate_policy_status_transition_graph(queryset=queryset)
        return {"valid": True, "message": "Policy status transition graph is valid."}
