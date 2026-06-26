import logging

from .config_service import ConfigurationService, ConfigurationError

logger = logging.getLogger(__name__)

WORKFLOW_PARAM = "STATE_MACHINE"
TERMINAL_STATUSES_PARAM = "TERMINAL_STATUSES"


class WorkflowEngine:
    """Configuration-driven workflow/state machine engine.

    Reads workflow definitions from System Parameters.
    Business teams can change workflows without code changes.
    """

    @staticmethod
    def get_state_machine() -> dict:
        """Return the state machine as {current_status: [allowed_next_statuses]}."""
        sm = ConfigurationService.get_json_parameter(WORKFLOW_PARAM)
        if not sm:
            logger.error("STATE_MACHINE parameter is missing or empty.")
            raise ConfigurationError("Workflow state machine is not configured.")
        return sm

    @staticmethod
    def get_terminal_statuses() -> list:
        """Return list of statuses that cannot transition further."""
        terminals = ConfigurationService.get_json_parameter(TERMINAL_STATUSES_PARAM, [])
        return terminals or []

    @staticmethod
    def get_allowed_transitions(status: str) -> list:
        """Return list of statuses reachable from the given status."""
        sm = WorkflowEngine.get_state_machine()
        return sm.get(status, [])

    @staticmethod
    def can_transition(current_status: str, target_status: str) -> bool:
        """Check whether a transition is allowed by the configured state machine."""
        allowed = WorkflowEngine.get_allowed_transitions(current_status)
        return target_status in allowed

    @staticmethod
    def is_terminal(status: str) -> bool:
        """Check whether a status is terminal (no further transitions allowed)."""
        return status in WorkflowEngine.get_terminal_statuses()

    @staticmethod
    def get_all_statuses() -> list:
        """Return all configured statuses from the state machine keys plus terminal values."""
        sm = WorkflowEngine.get_state_machine()
        statuses = set(sm.keys())
        for targets in sm.values():
            statuses.update(targets)
        return sorted(statuses)

    @staticmethod
    def validate_transition(current_status: str, target_status: str):
        """Raise ConfigurationError if transition is not allowed."""
        if not WorkflowEngine.can_transition(current_status, target_status):
            allowed = WorkflowEngine.get_allowed_transitions(current_status)
            raise ConfigurationError(
                f"Cannot transition from '{current_status}' to '{target_status}'. "
                f"Allowed transitions from '{current_status}': {allowed}"
            )

    @staticmethod
    def get_status_label(status_code: str) -> str:
        """Return the display label for a status code."""
        from apps.system_parameters.models import ChoiceList, ChoiceOption

        try:
            cl = ChoiceList.objects.get(code="APPLICATION_STATUS_CHOICES", is_active=True)
            option = ChoiceOption.objects.filter(
                choice_list=cl, code=status_code, is_active=True
            ).first()
            return option.label if option else status_code
        except Exception:
            return status_code


# Module-level convenience
workflow = WorkflowEngine
