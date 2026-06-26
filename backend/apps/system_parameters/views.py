from rest_framework import viewsets, permissions

from apps.core.pagination import StandardPagination
from .models import ParameterGroup, SystemParameter, ChoiceList, ChoiceOption
from .serializers import (
    ParameterGroupSerializer,
    ParameterGroupFlatSerializer,
    SystemParameterSerializer,
    SystemParameterWriteSerializer,
    ChoiceListSerializer,
    ChoiceOptionSerializer,
)


class ParameterGroupViewSet(viewsets.ModelViewSet):
    queryset = ParameterGroup.objects.prefetch_related("children").all()
    pagination_class = StandardPagination
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return ParameterGroupFlatSerializer
        return ParameterGroupSerializer


class SystemParameterViewSet(viewsets.ModelViewSet):
    queryset = SystemParameter.objects.select_related("group").all()
    serializer_class = SystemParameterSerializer
    pagination_class = StandardPagination
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name", "code", "description"]
    filterset_fields = ["group", "is_active", "value_type"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return SystemParameterWriteSerializer
        return SystemParameterSerializer


class ChoiceListViewSet(viewsets.ModelViewSet):
    queryset = ChoiceList.objects.prefetch_related("options").all()
    serializer_class = ChoiceListSerializer
    pagination_class = StandardPagination
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name", "code"]


class ChoiceOptionViewSet(viewsets.ModelViewSet):
    queryset = ChoiceOption.objects.all()
    serializer_class = ChoiceOptionSerializer
    pagination_class = StandardPagination
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["choice_list"]
