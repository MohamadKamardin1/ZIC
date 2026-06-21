import logging

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from apps.core.permissions import IsAdminUser
from apps.core.pagination import StandardPagination
from apps.partners.models import Partner
from apps.partners.serializers import (
    PartnerListSerializer,
    PartnerDetailSerializer,
    PartnerUpdateSerializer,
)
from apps.partners.filters import PartnerFilter

logger = logging.getLogger(__name__)


def _response(data=None, message="", status_code=200):
    return Response({
        "success": status_code < 400,
        "status_code": status_code,
        "message": message,
        "data": data,
        "meta": {"timestamp": timezone.now().isoformat(), "version": "v1"},
    }, status=status_code)


class PartnerViewSet(viewsets.ModelViewSet):
    queryset = Partner.objects.select_related(
        "created_from_application",
    ).prefetch_related("contacts", "bank_accounts")
    pagination_class = StandardPagination
    filterset_class = PartnerFilter
    search_fields = [
        "partner_number", "first_name", "surname",
        "company_name", "email", "mobile_number",
    ]
    ordering_fields = [
        "created_at", "partner_number", "status", "partner_type",
    ]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return PartnerListSerializer
        if self.action in ("update", "partial_update"):
            return PartnerUpdateSerializer
        return PartnerDetailSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdminUser()]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return _response(
            data=serializer.data,
            message="Partner retrieved successfully.",
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return _response(
            data=serializer.data,
            message="Partners retrieved successfully.",
        )

    def create(self, request, *args, **kwargs):
        return _response(
            message="Partners must be created via the onboarding conversion process.",
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        return _response(
            message="Partners cannot be deleted. Use deactivate instead.",
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        partner = self.get_object()
        if partner.status == "INACTIVE":
            return _response(
                message="Partner is already inactive.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        reason = request.data.get("reason", "")
        partner.status = "INACTIVE"
        partner.deactivated_at = timezone.now()
        partner.deactivation_reason = reason
        partner.save(
            update_fields=["status", "deactivated_at", "deactivation_reason", "updated_at"],
        )
        logger.info(
            "Partner %s deactivated by %s: %s",
            partner.partner_number, request.user.email, reason,
        )
        return _response(
            data=PartnerDetailSerializer(partner).data,
            message=f"Partner {partner.partner_number} deactivated.",
        )

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        partner = self.get_object()
        if partner.status == "ACTIVE":
            return _response(
                message="Partner is already active.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        partner.status = "ACTIVE"
        partner.activated_at = timezone.now()
        partner.deactivated_at = None
        partner.deactivation_reason = ""
        partner.save(
            update_fields=[
                "status", "activated_at", "deactivated_at",
                "deactivation_reason", "updated_at",
            ],
        )
        logger.info(
            "Partner %s activated by %s",
            partner.partner_number, request.user.email,
        )
        return _response(
            data=PartnerDetailSerializer(partner).data,
            message=f"Partner {partner.partner_number} activated.",
        )
