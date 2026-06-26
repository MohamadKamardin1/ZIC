from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ParameterGroupViewSet,
    SystemParameterViewSet,
    ChoiceListViewSet,
    ChoiceOptionViewSet,
)
from .views_config import (
    config_choices_list,
    config_choices_detail,
    config_workflow,
    config_workflow_validate_transition,
    config_cache_invalidate,
)

router = DefaultRouter()
router.register(r"groups", ParameterGroupViewSet, basename="param-groups")
router.register(r"parameters", SystemParameterViewSet, basename="system-parameters")
router.register(r"choice-lists", ChoiceListViewSet, basename="choice-lists")
router.register(r"choice-options", ChoiceOptionViewSet, basename="choice-options")

urlpatterns = [
    path("", include(router.urls)),
    # Configuration API
    path("configuration/choices/", config_choices_list, name="config-choices-list"),
    path(
        "configuration/choices/<str:code>/",
        config_choices_detail,
        name="config-choices-detail",
    ),
    path(
        "configuration/workflows/",
        config_workflow,
        name="config-workflows",
    ),
    path(
        "configuration/workflows/<str:workflow_code>/",
        config_workflow,
        name="config-workflow-detail",
    ),
    path(
        "configuration/workflows/validate-transition/",
        config_workflow_validate_transition,
        name="config-workflow-validate",
    ),
    path(
        "configuration/cache/invalidate/",
        config_cache_invalidate,
        name="config-cache-invalidate",
    ),
]
