import logging

from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q
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


def _json_safe(value):
    """Return values suitable for a JSON API without leaking file objects."""
    if value is None or isinstance(value, (str, int, float, bool, list, dict)):
        return value
    return str(value)


def _parameter_payload(parameter):
    return {
        "id": str(parameter.id),
        "code": parameter.code,
        "name": parameter.name,
        "description": parameter.description,
        "valueType": parameter.value_type,
        "value": _json_safe(parameter.value),
        "isActive": parameter.is_active,
        "isEncrypted": parameter.is_encrypted,
        "sortOrder": parameter.sort_order,
    }


def _choice_payload(choice_list):
    return {
        "id": str(choice_list.id),
        "code": choice_list.code,
        "name": choice_list.name,
        "description": choice_list.description,
        "isActive": choice_list.is_active,
        "options": [
            {
                "id": str(option.id),
                "code": option.code,
                "label": option.label,
                "isDefault": option.is_default,
                "isActive": option.is_active,
                "sortOrder": option.sort_order,
                "metadata": option.metadata,
            }
            for option in choice_list.options.all()
        ],
    }


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def config_partner_onboarding(request):
    """Return the complete parameterized partner-onboarding configuration.

    CRUD writes remain intentionally delegated to the protected resource
    endpoints. This read projection gives Settings and onboarding a stable,
    organized contract containing every active parameter domain and the
    partner-type-specific dynamic requirements.
    """
    from apps.partners.models import PartnerType
    from apps.system_parameters.models import ChoiceList, ParameterGroup

    groups = list(
        ParameterGroup.objects.filter(
            is_active=True,
        ).filter(
            Q(code__startswith="PARTNER") | Q(code="SYSTEM_CONFIG")
        ).prefetch_related("parameters", "children__parameters")
    )
    choice_lists = (
        ChoiceList.objects.filter(is_active=True)
        .prefetch_related("options")
        .order_by("name")
    )
    partner_types = (
        PartnerType.objects.filter(is_active=True)
        .prefetch_related(
            "document_requirements",
            "field_configurations",
            "contact_requirements",
            "bank_requirements",
        )
        .order_by("name")
    )

    group_payload = []
    for group in groups:
        if group.parent_id:
            continue
        child_payload = []
        for child in group.children.filter(is_active=True).order_by("sort_order", "name"):
            child_payload.append({
                "id": str(child.id),
                "code": child.code,
                "name": child.name,
                "description": child.description,
                "parameters": [
                    _parameter_payload(parameter)
                    for parameter in child.parameters.filter(is_active=True)
                ],
            })
        group_payload.append({
            "id": str(group.id),
            "code": group.code,
            "name": group.name,
            "description": group.description,
            "parameters": [
                _parameter_payload(parameter)
                for parameter in group.parameters.filter(is_active=True)
            ],
            "children": child_payload,
        })

    type_payload = []
    for partner_type in partner_types:
        type_payload.append({
            "id": str(partner_type.id),
            "code": partner_type.code,
            "name": partner_type.name,
            "description": partner_type.description,
            "isActive": partner_type.is_active,
            "documents": [
                {
                    "id": str(item.id),
                    "code": item.code,
                    "description": item.description,
                    "isRequired": item.is_required,
                    "isMandatory": item.is_mandatory,
                    "allowMultipleUploads": item.allow_multiple_uploads,
                    "sortOrder": item.sort_order,
                    "isActive": item.is_active,
                }
                for item in partner_type.document_requirements.filter(is_active=True)
            ],
            "attributes": [
                {
                    "id": str(item.id),
                    "fieldName": item.field_name,
                    "fieldCode": item.field_code,
                    "fieldType": item.field_type,
                    "defaultValue": item.default_value,
                    "isRequired": item.is_required,
                    "validationRules": item.validation_rules,
                    "displayOrder": item.display_order,
                    "visibilityRules": item.visibility_rules,
                    "isActive": item.is_active,
                }
                for item in partner_type.field_configurations.filter(is_active=True)
            ],
            "contacts": [
                {
                    "id": str(item.id),
                    "contactType": item.contact_type,
                    "isRequired": item.is_required,
                    "multipleAllowed": item.multiple_allowed,
                    "displayOrder": item.display_order,
                    "isActive": item.is_active,
                }
                for item in partner_type.contact_requirements.filter(is_active=True)
            ],
            "banks": [
                {
                    "id": str(item.id),
                    "bankType": item.bank_type,
                    "isRequired": item.is_required,
                    "multipleAllowed": item.multiple_allowed,
                    "validationRules": item.validation_rules,
                    "displayOrder": item.display_order,
                    "isActive": item.is_active,
                }
                for item in partner_type.bank_requirements.filter(is_active=True)
            ],
        })

    return _response(
        data={
            "version": "partner-onboarding.v1",
            "groups": group_payload,
            "choiceLists": [_choice_payload(choice_list) for choice_list in choice_lists],
            "partnerTypes": type_payload,
        },
        message="Partner onboarding configuration retrieved.",
    )


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
