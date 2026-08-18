from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardPagination

from .models import OLParameterTableRegistry
from .permissions import HasOLParameterPermission, has_ol_parameter_permission
from .serializers import OLTableRegistrySerializer
from .services.parameter_service import OLParameterService


class OLParameterTableRegistryViewSet(viewsets.ModelViewSet):
    """Declarative registry consumed by table-first OL parameter clients."""

    queryset = OLParameterTableRegistry.objects.select_related("created_by", "updated_by").all()
    serializer_class = OLTableRegistrySerializer
    pagination_class = StandardPagination
    permission_classes = [permissions.IsAuthenticated, HasOLParameterPermission]
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
        OLParameterService.deactivate_registry(
            actor=request.user,
            instance=instance,
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, *args, **kwargs):
        instance = self.get_object()
        OLParameterService.deactivate_registry(
            actor=request.user,
            instance=instance,
            request=request,
        )
        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)


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
            }
        )
