import logging

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from django.utils import timezone
from django.shortcuts import get_object_or_404

from apps.core.permissions import IsAdminUser
from apps.core.pagination import StandardPagination

from apps.governance.models import (
    AuditLog, ApprovalRequest, ConfigurationVersion,
    AUDIT_ACTION_CHOICES,
)
from apps.governance.serializers import (
    AuditLogSerializer,
    ApprovalRequestSerializer,
    ApprovalActionSerializer,
    ConfigurationVersionSerializer,
    DocumentVersionSerializer,
    KYCReviewHistorySerializer,
    PartnerTypeAssignmentHistorySerializer,
)
from apps.governance.services.approval_service import ApprovalService
from apps.governance.services.audit_service import AuditService

from apps.partners.models import (
    DocumentVersion, KYCReviewHistory, PartnerTypeAssignmentHistory,
    PartnerDocument, PartnerKYCProfile, PartnerTypeAssignment,
)
from apps.partners.serializers import (
    PartnerDocumentSerializer,
)

logger = logging.getLogger(__name__)


def _response(data=None, message="", status_code=200):
    return Response({
        "success": status_code < 400,
        "status_code": status_code,
        "message": message,
        "data": data,
        "meta": {"timestamp": timezone.now().isoformat(), "version": "v1"},
    }, status=status_code)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("user").all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    pagination_class = StandardPagination
    ordering_fields = ["timestamp", "action_type", "entity_type"]
    ordering = ["-timestamp"]
    search_fields = ["entity_type", "entity_repr", "description", "action_type"]

    def get_queryset(self):
        qs = super().get_queryset()
        entity_type = self.request.query_params.get("entity_type")
        entity_id = self.request.query_params.get("entity_id")
        action_type = self.request.query_params.get("action_type")
        user_id = self.request.query_params.get("user_id")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        if action_type:
            qs = qs.filter(action_type=action_type)
        if user_id:
            qs = qs.filter(user_id=user_id)
        if date_from:
            qs = qs.filter(timestamp__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__lte=date_to)
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return _response(data=serializer.data, message="Audit logs retrieved.")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return _response(data=serializer.data, message="Audit log retrieved.")

    @action(detail=False, methods=["get"])
    def actions(self, request):
        return _response(data=AUDIT_ACTION_CHOICES, message="Audit actions retrieved.")

    @action(detail=False, methods=["get"])
    def stats(self, request):
        qs = AuditLog.objects
        days = int(request.query_params.get("days", 30))
        since = timezone.now() - timezone.timedelta(days=days)
        total = qs.filter(timestamp__gte=since).count()
        by_action = {}
        for row in qs.filter(timestamp__gte=since).values("action_type").annotate(
            count=models.Count("id")
        ).order_by("-count"):
            by_action[row["action_type"]] = row["count"]
        by_entity = {}
        for row in qs.filter(timestamp__gte=since).values("entity_type").annotate(
            count=models.Count("id")
        ).order_by("-count")[:10]:
            by_entity[row["entity_type"]] = row["count"]
        return _response(data={
            "total": total,
            "days": days,
            "by_action": by_action,
            "by_entity": by_entity,
        }, message="Audit stats retrieved.")


class ApprovalRequestViewSet(viewsets.ModelViewSet):
    queryset = ApprovalRequest.objects.select_related(
        "submitted_by", "reviewed_by",
    ).all()
    serializer_class = ApprovalRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    ordering_fields = ["submitted_at", "status", "module"]
    ordering = ["-submitted_at"]
    search_fields = ["module", "entity_type", "entity_repr", "action"]

    def get_queryset(self):
        qs = super().get_queryset()
        module = self.request.query_params.get("module")
        entity_type = self.request.query_params.get("entity_type")
        status = self.request.query_params.get("status")
        if module:
            qs = qs.filter(module=module)
        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        if status:
            qs = qs.filter(status=status)
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return _response(data=serializer.data, message="Approval requests retrieved.")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return _response(data=serializer.data, message="Approval request retrieved.")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        approval = ApprovalService.submit(
            module=serializer.validated_data["module"],
            entity_type=serializer.validated_data["entity_type"],
            entity_id=serializer.validated_data["entity_id"],
            action=serializer.validated_data["action"],
            requested_data=serializer.validated_data.get("requested_data"),
            current_data=serializer.validated_data.get("current_data"),
            entity_repr=serializer.validated_data.get("entity_repr", ""),
            submitted_by=request.user,
            comments=serializer.validated_data.get("comments", ""),
        )
        return _response(
            data=ApprovalRequestSerializer(approval).data,
            message="Approval request submitted.",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        approval = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            approval = ApprovalService.approve(
                approval_id=approval.pk,
                reviewed_by=request.user,
                comments=serializer.validated_data.get("comments", ""),
            )
            return _response(
                data=ApprovalRequestSerializer(approval).data,
                message="Approval approved.",
            )
        except ValueError as e:
            return _response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        approval = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            approval = ApprovalService.reject(
                approval_id=approval.pk,
                reviewed_by=request.user,
                comments=serializer.validated_data.get("comments", ""),
            )
            return _response(
                data=ApprovalRequestSerializer(approval).data,
                message="Approval rejected.",
            )
        except ValueError as e:
            return _response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        approval = self.get_object()
        try:
            approval = ApprovalService.cancel(
                approval_id=approval.pk,
                user=request.user,
                comments=request.data.get("comments", ""),
            )
            return _response(
                data=ApprovalRequestSerializer(approval).data,
                message="Approval cancelled.",
            )
        except ValueError as e:
            return _response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def pending(self, request):
        module = request.query_params.get("module")
        entity_type = request.query_params.get("entity_type")
        qs = ApprovalService.get_pending(module=module, entity_type=entity_type)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return _response(data=serializer.data, message="Pending approvals retrieved.")

    @action(detail=False, methods=["get"])
    def stats(self, request):
        qs = ApprovalRequest.objects
        total = qs.count()
        pending = qs.filter(status="PENDING").count()
        approved = qs.filter(status="APPROVED").count()
        rejected = qs.filter(status="REJECTED").count()
        cancelled = qs.filter(status="CANCELLED").count()
        return _response(data={
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "cancelled": cancelled,
        }, message="Approval stats retrieved.")


class ConfigurationVersionViewSet(viewsets.ModelViewSet):
    queryset = ConfigurationVersion.objects.select_related("created_by").all()
    serializer_class = ConfigurationVersionSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    pagination_class = StandardPagination
    ordering_fields = ["module", "version_number", "effective_from", "status"]
    ordering = ["module", "-version_number"]
    search_fields = ["module", "change_summary", "notes"]

    def get_queryset(self):
        qs = super().get_queryset()
        module = self.request.query_params.get("module")
        status = self.request.query_params.get("status")
        if module:
            qs = qs.filter(module=module)
        if status:
            qs = qs.filter(status=status)
        return qs

    def perform_create(self, serializer):
        module = serializer.validated_data["module"]
        last_version = ConfigurationVersion.objects.filter(
            module=module
        ).order_by("-version_number").first()
        next_version = (last_version.version_number + 1) if last_version else 1
        serializer.save(created_by=self.request.user, version_number=next_version)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return _response(data=serializer.data, message="Configuration versions retrieved.")

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        instance = self.get_object()
        if instance.status != "DRAFT":
            return _response(
                message=f"Cannot activate: current status is {instance.status}.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        instance.status = "ACTIVE"
        instance.save(update_fields=["status"])
        AuditService.log_model_action(
            action="ACTIVATE", instance=instance,
            after_state={"status": "ACTIVE"},
            description=f"Configuration version {instance.module} v{instance.version_number} activated.",
        )
        return _response(
            data=ConfigurationVersionSerializer(instance).data,
            message="Configuration version activated.",
        )

    @action(detail=True, methods=["post"])
    def retire(self, request, pk=None):
        instance = self.get_object()
        if instance.status != "ACTIVE":
            return _response(
                message=f"Cannot retire: current status is {instance.status}.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        instance.status = "RETIRED"
        instance.effective_to = timezone.now().date()
        instance.save(update_fields=["status", "effective_to"])
        AuditService.log_model_action(
            action="DEACTIVATE", instance=instance,
            before_state={"status": "ACTIVE"},
            after_state={"status": "RETIRED"},
            description=f"Configuration version {instance.module} v{instance.version_number} retired.",
        )
        return _response(
            data=ConfigurationVersionSerializer(instance).data,
            message="Configuration version retired.",
        )

    @action(detail=False, methods=["get"])
    def active(self, request):
        module = request.query_params.get("module")
        qs = ConfigurationVersion.objects.filter(status="ACTIVE")
        if module:
            qs = qs.filter(module=module)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return _response(data=serializer.data, message="Active versions retrieved.")


class DocumentVersionViewSet(viewsets.ModelViewSet):
    queryset = DocumentVersion.objects.select_related(
        "document", "uploaded_by", "verified_by",
    ).all()
    serializer_class = DocumentVersionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    ordering = ["document", "-version_number"]

    def get_queryset(self):
        qs = super().get_queryset()
        document_id = self.request.query_params.get("document_id")
        if document_id:
            qs = qs.filter(document_id=document_id)
        return qs

    def perform_create(self, serializer):
        document = serializer.validated_data["document"]
        last_version = DocumentVersion.objects.filter(
            document=document
        ).order_by("-version_number").first()
        next_version = (last_version.version_number + 1) if last_version else 1
        serializer.save(uploaded_by=self.request.user, version_number=next_version)
        AuditService.log(
            action_type="UPLOAD",
            entity_type="DocumentVersion",
            entity_id=serializer.instance.pk,
            entity_repr=str(serializer.instance),
            description=f"Version {next_version} uploaded for document {document.pk}",
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return _response(data=serializer.data, message="Document versions retrieved.")


class KYCReviewHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = KYCReviewHistory.objects.select_related("reviewed_by").all()
    serializer_class = KYCReviewHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    ordering = ["-decision_date"]

    def get_queryset(self):
        qs = super().get_queryset()
        kyc_profile_id = self.request.query_params.get("kyc_profile_id")
        review_type = self.request.query_params.get("review_type")
        if kyc_profile_id:
            qs = qs.filter(kyc_profile_id=kyc_profile_id)
        if review_type:
            qs = qs.filter(review_type=review_type)
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return _response(data=serializer.data, message="KYC review history retrieved.")


class PartnerTypeAssignmentHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PartnerTypeAssignmentHistory.objects.select_related("changed_by").all()
    serializer_class = PartnerTypeAssignmentHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    ordering = ["-changed_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        assignment_id = self.request.query_params.get("assignment_id")
        if assignment_id:
            qs = qs.filter(assignment_id=assignment_id)
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return _response(data=serializer.data, message="Assignment history retrieved.")


class ComplianceDashboardViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination

    @action(detail=False, methods=["get"])
    def overview(self, request):
        from apps.partners.models import (
            Partner, PartnerKYCProfile, PartnerDocument, PartnerTypeAssignment,
        )
        from django.db.models import Count, Q
        total_partners = Partner.objects.count()
        active_partners = Partner.objects.filter(status="ACTIVE").count()
        kyc_pending = PartnerKYCProfile.objects.filter(kyc_status="NOT_SET").count()
        kyc_cleared = PartnerKYCProfile.objects.filter(kyc_status="CLEARED").count()
        kyc_rejected = PartnerKYCProfile.objects.filter(kyc_status="REJECTED").count()
        kyc_escalated = PartnerKYCProfile.objects.filter(kyc_status="ESCALATED").count()
        docs_pending = PartnerDocument.objects.filter(status="NOT_SUBMITTED").count()
        docs_expired = PartnerDocument.objects.filter(
            status="APPROVED", expiry_date__lt=timezone.now().date()
        ).count()
        high_risk = PartnerKYCProfile.objects.filter(risk_level__in=["HIGH", "CRITICAL"]).count()
        return _response(data={
            "total_partners": total_partners,
            "active_partners": active_partners,
            "kyc_pending": kyc_pending,
            "kyc_cleared": kyc_cleared,
            "kyc_rejected": kyc_rejected,
            "kyc_escalated": kyc_escalated,
            "documents_pending": docs_pending,
            "documents_expired": docs_expired,
            "high_risk_partners": high_risk,
        }, message="Compliance overview retrieved.")

    @action(detail=False, methods=["get"])
    def expiring_documents(self, request):
        from apps.partners.models import PartnerDocument
        from django.utils import timezone
        days = int(request.query_params.get("days", 30))
        cutoff = timezone.now().date() + timezone.timedelta(days=days)
        qs = PartnerDocument.objects.filter(
            status="APPROVED",
            expiry_date__lte=cutoff,
            expiry_date__gte=timezone.now().date(),
        ).select_related("assignment__partner", "document_requirement")
        page = self.paginate_queryset(qs)
        if page is not None:
            data = [{
                "id": d.pk,
                "partner": str(d.assignment.partner),
                "document_type": d.document_requirement.code if d.document_requirement else "",
                "expiry_date": d.expiry_date,
                "days_remaining": (d.expiry_date - timezone.now().date()).days if d.expiry_date else 0,
            } for d in page]
            return self.get_paginated_response(data)
        return _response(data=[], message="Expiring documents retrieved.")

    @action(detail=False, methods=["get"])
    def high_risk_partners(self, request):
        from apps.partners.models import PartnerKYCProfile
        qs = PartnerKYCProfile.objects.filter(
            risk_level__in=["HIGH", "CRITICAL"],
        ).select_related("assignment__partner", "assignment__partner_type")
        page = self.paginate_queryset(qs)
        if page is not None:
            data = [{
                "id": k.pk,
                "partner": str(k.assignment.partner),
                "partner_number": k.assignment.partner.partner_number,
                "partner_type": k.assignment.partner_type.name if k.assignment.partner_type else "",
                "risk_score": float(k.risk_score) if k.risk_score else None,
                "risk_level": k.risk_level,
                "kyc_status": k.kyc_status,
            } for k in page]
            return self.get_paginated_response(data)
        return _response(data=[], message="High risk partners retrieved.")
