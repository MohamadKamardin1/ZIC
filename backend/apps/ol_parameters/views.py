import csv
import json

from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardPagination

from .models import (
    OLComputationApproach,
    OLDefaultSystemParameter,
    OLMaturityClaimSetup,
    OLOverrideCommissionSetup,
    OLParameterTableRegistry,
)
from .permissions import HasOLParameterPermission, has_ol_parameter_permission
from .serializers import (
    OLComputationApproachSerializer,
    OLDefaultSystemParameterSerializer,
    OLMaturityClaimSetupSerializer,
    OLOverrideCommissionSetupSerializer,
    OLTableRegistrySerializer,
)
from .services.default_setup_service import OLDefaultSetupService
from .services.parameter_service import OLParameterService


class OLParameterTableRegistryViewSet(viewsets.ModelViewSet):
    """Declarative registry consumed by table-first OL parameter clients."""

    queryset = OLParameterTableRegistry.objects.select_related("created_by", "updated_by").all()
    serializer_class = OLTableRegistrySerializer
    pagination_class = StandardPagination
    permission_classes = [permissions.IsAuthenticated, HasOLParameterPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["slug", "label", "description", "parameter_group", "model_label"]
    filterset_fields = ["is_active", "parameter_group", "export_support", "model_label"]
    ordering_fields = ["slug", "label", "parameter_group", "created_at", "updated_at"]
    ordering = ["parameter_group", "label", "slug"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if has_ol_parameter_permission(self.request.user, "configure"):
            return queryset
        return queryset.filter(is_active=True)

    def perform_create(self, serializer):
        instance = OLParameterService.create_registry(
            actor=self.request.user,
            data=serializer.validated_data,
            request=self.request,
        )
        serializer.instance = instance

    def perform_update(self, serializer):
        instance = OLParameterService.update_registry(
            actor=self.request.user,
            instance=self.get_object(),
            data=serializer.validated_data,
            request=self.request,
        )
        serializer.instance = instance

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        OLParameterService.deactivate_registry(actor=request.user, instance=instance, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, *args, **kwargs):
        instance = self.get_object()
        OLParameterService.deactivate_registry(actor=request.user, instance=instance, request=request)
        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)


class OLDefaultSetupViewSet(viewsets.ModelViewSet):
    """Shared table behavior for all OL Default Setup configuration entities."""

    model = None
    serializer_class = None
    pagination_class = StandardPagination
    permission_classes = [permissions.IsAuthenticated, HasOLParameterPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "name", "description"]
    filterset_fields = ["is_active", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "is_active", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["name", "code"]
    table_slug = ""

    def get_queryset(self):
        queryset = self.model.objects.select_related("created_by", "updated_by").all()
        if not has_ol_parameter_permission(self.request.user, "configure"):
            queryset = queryset.filter(is_active=True)
        return queryset

    def perform_create(self, serializer):
        serializer.instance = OLDefaultSetupService.create(
            model=self.model,
            actor=self.request.user,
            data=serializer.validated_data,
            request=self.request,
        )

    def perform_update(self, serializer):
        serializer.instance = OLDefaultSetupService.update(
            model=self.model,
            actor=self.request.user,
            instance=self.get_object(),
            data=serializer.validated_data,
            request=self.request,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        OLDefaultSetupService.deactivate(actor=request.user, instance=instance, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, *args, **kwargs):
        instance = self.get_object()
        OLDefaultSetupService.deactivate(actor=request.user, instance=instance, request=request)
        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        payload = self.get_serializer(queryset, many=True).data
        fieldnames = list(payload[0].keys()) if payload else [field.name for field in self.model._meta.fields]
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{self.table_slug or self.model._meta.model_name}.csv"'
        writer = csv.DictWriter(response, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in payload:
            writer.writerow({
                key: json.dumps(value, default=str) if isinstance(value, (dict, list)) else value
                for key, value in row.items()
            })
        return response


class OLDefaultSystemParameterViewSet(OLDefaultSetupViewSet):
    model = OLDefaultSystemParameter
    serializer_class = OLDefaultSystemParameterSerializer
    table_slug = "default-system-parameters"
    search_fields = ["code", "parameter_key", "name", "parameter_category", "description"]
    filterset_fields = ["is_active", "parameter_category", "value_type", "effective_from", "effective_to"]
    ordering_fields = ["code", "parameter_key", "name", "parameter_category", "value_type", "is_active", "effective_from", "created_at", "updated_at"]
    ordering = ["parameter_category", "name", "parameter_key"]


class OLOverrideCommissionSetupViewSet(OLDefaultSetupViewSet):
    model = OLOverrideCommissionSetup
    serializer_class = OLOverrideCommissionSetupSerializer
    table_slug = "override-commission-setups"
    search_fields = ["code", "name", "description", "intermediary_type", "channel", "currency", "reason"]
    filterset_fields = [
        "is_active", "partner", "product", "plan", "rider", "branch", "intermediary_type", "channel", "currency",
        "rate_type", "priority", "effective_from", "effective_to",
    ]
    ordering_fields = ["priority", "code", "name", "rate_value", "rate_type", "effective_from", "effective_to", "created_at", "updated_at"]
    ordering = ["priority", "-effective_from", "code"]


class OLComputationApproachViewSet(OLDefaultSetupViewSet):
    model = OLComputationApproach
    serializer_class = OLComputationApproachSerializer
    table_slug = "computation-approaches"
    search_fields = ["code", "name", "description", "calculation_area", "calculation_basis", "formula_key"]
    filterset_fields = ["is_active", "calculation_area", "calculation_basis", "sequence", "effective_from", "effective_to"]
    ordering_fields = ["calculation_area", "sequence", "code", "name", "formula_key", "is_active", "effective_from", "created_at", "updated_at"]
    ordering = ["calculation_area", "sequence", "name", "code"]


class OLMaturityClaimSetupViewSet(OLDefaultSetupViewSet):
    model = OLMaturityClaimSetup
    serializer_class = OLMaturityClaimSetupSerializer
    table_slug = "maturity-claim-setups"
    search_fields = ["code", "name", "description", "default_payout_method", "maturity_claim_status_to_create"]
    filterset_fields = ["is_active", "product", "plan", "auto_create_maturity_claim", "require_documents", "require_approval", "effective_from", "effective_to"]
    ordering_fields = ["code", "name", "days_before_maturity_to_initiate", "notification_days", "is_active", "effective_from", "created_at", "updated_at"]
    ordering = ["-effective_from", "name", "code"]


class OLParameterHealthView(APIView):
    """Low-sensitivity readiness endpoint for the OL Parameters bounded context."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(
            {
                "status": "ok",
                "service": "ol_parameters",
                "timestamp": timezone.now(),
                "registry": {
                    "total": OLParameterTableRegistry.objects.count(),
                    "active": OLParameterTableRegistry.objects.filter(is_active=True).count(),
                },
                "default_setup": {
                    "default_system_parameters": OLDefaultSystemParameter.objects.filter(is_active=True).count(),
                    "override_commission_setups": OLOverrideCommissionSetup.objects.filter(is_active=True).count(),
                    "computation_approaches": OLComputationApproach.objects.filter(is_active=True).count(),
                    "maturity_claim_setups": OLMaturityClaimSetup.objects.filter(is_active=True).count(),
                },
            }
        )
