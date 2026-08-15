from rest_framework import viewsets, permissions

from apps.core.pagination import StandardPagination
from apps.core.permissions import HasModulePermission
from apps.governance.services.audit_service import AuditService
from .models import ParameterGroup, SystemParameter, ChoiceList, ChoiceOption
from .serializers import (
    ParameterGroupSerializer,
    ParameterGroupFlatSerializer,
    SystemParameterSerializer,
    SystemParameterWriteSerializer,
    ChoiceListSerializer,
    ChoiceOptionSerializer,
)
from .services.config_service import ConfigurationService


class AuditedConfigurationMixin:
    """Persist configuration mutations with central audit metadata."""

    def perform_create(self, serializer):
        instance = serializer.save()
        AuditService.log_create(
            instance,
            actor=self.request.user,
            request=self.request,
            reason="Configuration created from partner onboarding Settings.",
        )
        ConfigurationService.invalidate_cache()

    def perform_update(self, serializer):
        instance = self.get_object()
        before_state = AuditService.snapshot(instance)
        instance = serializer.save()
        AuditService.log_update(
            instance,
            before_state=before_state,
            actor=self.request.user,
            request=self.request,
            reason="Configuration updated from partner onboarding Settings.",
        )
        ConfigurationService.invalidate_cache()

    def perform_destroy(self, instance):
        AuditService.log_delete(
            instance,
            actor=self.request.user,
            request=self.request,
            reason="Configuration deleted from partner onboarding Settings.",
        )
        instance.delete()
        ConfigurationService.invalidate_cache()


class ParameterGroupViewSet(AuditedConfigurationMixin, viewsets.ModelViewSet):
    queryset = ParameterGroup.objects.prefetch_related("children").all()
    pagination_class = StandardPagination

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), HasModulePermission("system_parameters", "MANAGE")]

    def get_serializer_class(self):
        if self.action == "list":
            return ParameterGroupFlatSerializer
        return ParameterGroupSerializer


class SystemParameterViewSet(AuditedConfigurationMixin, viewsets.ModelViewSet):
    queryset = SystemParameter.objects.select_related("group").all()
    serializer_class = SystemParameterSerializer
    pagination_class = StandardPagination
    search_fields = ["name", "code", "description"]
    filterset_fields = ["group", "is_active", "value_type"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), HasModulePermission("system_parameters", "MANAGE")]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return SystemParameterWriteSerializer
        return SystemParameterSerializer


class ChoiceListViewSet(AuditedConfigurationMixin, viewsets.ModelViewSet):
    queryset = ChoiceList.objects.prefetch_related("options").all()
    serializer_class = ChoiceListSerializer
    pagination_class = StandardPagination
    search_fields = ["name", "code"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), HasModulePermission("system_parameters", "MANAGE")]


class ChoiceOptionViewSet(AuditedConfigurationMixin, viewsets.ModelViewSet):
    queryset = ChoiceOption.objects.select_related("choice_list").all()
    serializer_class = ChoiceOptionSerializer
    pagination_class = StandardPagination
    filterset_fields = ["choice_list", "is_active"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), HasModulePermission("system_parameters", "MANAGE")]
