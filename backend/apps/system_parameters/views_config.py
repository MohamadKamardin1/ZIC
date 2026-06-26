import logging

from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone

from .services.config_service import ConfigurationService, ConfigurationError
from .services.workflow_service import WorkflowEngine

logger = logging.getLogger(__name__)


def _response(data=None, message="", status_code=200):
    return Response({
        "success": status_code < 400,
        "status_code": status_code,
        "message": message,
        "data": data,
        "meta": {"timestamp": timezone.now().isoformat(), "version": "v1"},
    }, status=status_code)


# ---------------------------------------------------------------------------
# Configuration API
# ---------------------------------------------------------------------------


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def config_choices_list(request):
    """List all available choice lists with their options."""
    from apps.system_parameters.models import ChoiceList

    lists = ChoiceList.objects.filter(is_active=True).order_by("code")
    result = {}
    for cl in lists:
        try:
            result[cl.code] = ConfigurationService.get_choice_list(cl.code)
        except ConfigurationError:
            result[cl.code] = []
    return _response(data=result, message="All choice lists retrieved.")


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def config_choices_detail(request, code):
    """Return options for a specific choice list."""
    try:
        options = ConfigurationService.get_choice_list(code.upper())
        return _response(data=options, message=f"Choice list '{code}' retrieved.")
    except ConfigurationError as e:
        return _response(message=str(e), status_code=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def config_workflow(request, workflow_code=None):
    """Return workflow configuration."""
    try:
        state_machine = WorkflowEngine.get_state_machine()
        terminal_statuses = WorkflowEngine.get_terminal_statuses()
        all_statuses = WorkflowEngine.get_all_statuses()

        result = {
            "state_machine": state_machine,
            "terminal_statuses": terminal_statuses,
            "all_statuses": all_statuses,
            "status_labels": {
                s: WorkflowEngine.get_status_label(s) for s in all_statuses
            },
        }
        return _response(data=result, message="Workflow configuration retrieved.")
    except ConfigurationError as e:
        return _response(
            message=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def config_workflow_validate_transition(request):
    """Validate whether a status transition is allowed."""
    current = request.data.get("current_status", "").upper()
    target = request.data.get("target_status", "").upper()

    if not current or not target:
        return _response(
            message="Both current_status and target_status are required.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    allowed = WorkflowEngine.can_transition(current, target)
    return _response(
        data={
            "current_status": current,
            "target_status": target,
            "allowed": allowed,
            "allowed_transitions": WorkflowEngine.get_allowed_transitions(current),
        },
        message="Transition validation complete.",
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def config_cache_invalidate(request):
    """Invalidate the configuration cache."""
    pattern = request.data.get("pattern")
    ConfigurationService.invalidate_cache(pattern)
    return _response(message="Configuration cache invalidated.")
