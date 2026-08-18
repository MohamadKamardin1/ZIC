import logging
import os

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import FileResponse, HttpResponseNotFound

from apps.core.permissions import IsAdminUser, IsOwnerOrAdmin
from apps.core.pagination import StandardPagination
from apps.partner_onboarding.models import (
    PartnerApplication,
    PartnerApplicationDocument,
    PartnerApplicationTask,
    ApplicationPartnerType,
    ApplicationContact,
    ApplicationBankAccount,
    ApplicationFieldValue,
    Branch,
    Location,
    UnifiedOnboardingRecord,
    PartnerApplicationEvent,
)
from apps.partner_onboarding.serializers import (
    PartnerApplicationListSerializer,
    PartnerApplicationDetailSerializer,
    PartnerApplicationCreateSerializer,
    PartnerApplicationUpdateSerializer,
    PartnerApplicationSubmitSerializer,
    PartnerApplicationReviewSerializer,
    PartnerApplicationComplianceSerializer,
    PartnerConvertSerializer,
    PartnerApplicationDocumentSerializer,
    PartnerApplicationDocumentUploadSerializer,
    PartnerApplicationTaskSerializer,
    ChoicesSerializer,
    BranchSerializer,
    LocationSerializer,
    ApplicationPartnerTypeSerializer,
    ApplicationPartnerTypeCreateSerializer,
    ApplicationContactSerializer,
    ApplicationBankAccountSerializer,
    ApplicationFieldValueSerializer,
    ApplicationFieldValueBatchSerializer,
    UnifiedOnboardingRecordSerializer,
)
from apps.partner_onboarding.services import ApplicationService, ComplianceService
from apps.governance.services.audit_service import AuditService
from apps.partner_onboarding.exceptions import (
    ApplicationTransitionError,
    ApplicationValidationError,
    PartnerConversionError,
)
from apps.partner_onboarding.filters import PartnerApplicationFilter, UnifiedOnboardingRecordFilter
from apps.partner_onboarding.validators import validate_and_parse_excel
from apps.partner_onboarding.permissions import (
    IsOwnerOrReviewer,
    CanSubmitApplication,
    CanReviewApplication,
    CanPerformComplianceAction,
    CanRejectApplication,
    CanConvertApplication,
    CanCreateApplication,
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


def _can_access_application(user, application, write=False, approve=False):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or application.submitted_by_id == user.id:
        return True
    if approve:
        return user.has_module_permission("partner_onboarding", "APPROVE")
    return user.has_module_permission(
        "partner_onboarding", "UPDATE" if write else "READ"
    ) or user.has_module_permission("partner_onboarding", "APPROVE")


class PartnerApplicationViewSet(viewsets.ModelViewSet):
    queryset = PartnerApplication.objects.select_related(
        "submitted_by", "reviewed_by", "approved_by",
    ).prefetch_related(
        "documents", "tasks", "partner_types", "contacts", "bank_accounts",
        "field_values", "events",
    )
    pagination_class = StandardPagination
    filterset_class = PartnerApplicationFilter
    search_fields = [
        "application_number", "first_name", "surname",
        "company_name", "email", "mobile_number",
    ]
    ordering_fields = [
        "created_at", "submitted_at", "application_number", "status",
    ]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return PartnerApplicationListSerializer
        if self.action == "create":
            return PartnerApplicationCreateSerializer
        if self.action in ("update", "partial_update"):
            return PartnerApplicationUpdateSerializer
        return PartnerApplicationDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if user.is_superuser or user.has_module_permission("partner_onboarding", "READ") or user.has_module_permission("partner_onboarding", "APPROVE"):
            return queryset
        return queryset.filter(submitted_by=user)

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), CanCreateApplication()]
        if self.action in ("update", "partial_update"):
            return [permissions.IsAuthenticated(), IsOwnerOrReviewer()]
        if self.action == "destroy":
            return [permissions.IsAuthenticated(), IsOwnerOrReviewer()]
        if self.action == "retrieve":
            return [permissions.IsAuthenticated(), IsOwnerOrReviewer()]
        if self.action in ("list",):
            return [permissions.IsAuthenticated()]
        if self.action == "submit":
            return [permissions.IsAuthenticated(), CanSubmitApplication()]
        if self.action in ("start_review", "request_documents", "send_to_compliance"):
            return [permissions.IsAuthenticated(), CanReviewApplication()]
        if self.action in ("approve", "suspend"):
            return [permissions.IsAuthenticated(), CanPerformComplianceAction()]
        if self.action == "reject":
            return [permissions.IsAuthenticated(), CanRejectApplication()]
        if self.action == "convert":
            return [permissions.IsAuthenticated(), CanConvertApplication()]
        if self.action == "resume":
            return [permissions.IsAuthenticated(), CanPerformComplianceAction()]
        if self.action == "run_compliance":
            return [permissions.IsAuthenticated(), CanPerformComplianceAction()]
        return [permissions.IsAuthenticated()]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return _response(
            data=serializer.data,
            message="Application retrieved successfully.",
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
            message="Applications retrieved successfully.",
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = ApplicationService.create_draft(
            request.user, serializer.validated_data,
        )
        return _response(
            data=PartnerApplicationDetailSerializer(application).data,
            message="Application draft created successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        application = self.get_object()
        if application.status not in ("DRAFT", "ACTIVE"):
            return _response(
                message="Only DRAFT or ACTIVE applications can be updated.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(application, data=request.data, partial=kwargs.get("partial", False))
        serializer.is_valid(raise_exception=True)
        try:
            application = ApplicationService.update_draft(
                application, request.user, serializer.validated_data
            )
        except ApplicationValidationError as exc:
            return _response(message=str(exc), status_code=exc.status_code)
        return _response(
            data=PartnerApplicationDetailSerializer(application).data,
            message="Application updated successfully.",
        )

    def destroy(self, request, *args, **kwargs):
        application = self.get_object()
        if application.status not in ("DRAFT", "ACTIVE"):
            return _response(
                message="Only DRAFT or ACTIVE applications can be deleted.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if application.submitted_by_id != request.user.id and not request.user.has_module_permission("partner_onboarding", "DELETE"):
            return _response(message="You do not have permission to delete this application.", status_code=status.HTTP_403_FORBIDDEN)
        application.delete()
        return _response(
            message="Application deleted successfully.",
            status_code=status.HTTP_204_NO_CONTENT,
        )

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        application = self.get_object()
        serializer = PartnerApplicationSubmitSerializer(instance=application, data={})
        serializer.is_valid(raise_exception=True)
        try:
            result = ApplicationService.submit(application, request.user)
        except (ApplicationTransitionError, ApplicationValidationError) as e:
            return _response(message=str(e), status_code=e.status_code)
        return _response(
            data=PartnerApplicationDetailSerializer(result).data,
            message="Application submitted successfully.",
        )

    @action(detail=True, methods=["post"], url_path="start-review")
    def start_review(self, request, pk=None):
        application = self.get_object()
        try:
            result = ApplicationService.start_review(application, request.user)
        except (ApplicationTransitionError, ApplicationValidationError) as e:
            return _response(message=str(e), status_code=e.status_code)
        return _response(
            data=PartnerApplicationDetailSerializer(result).data,
            message="Application review started.",
        )

    @action(detail=True, methods=["post"], url_path="request-documents")
    def request_documents(self, request, pk=None):
        application = self.get_object()
        serializer = PartnerApplicationReviewSerializer(
            instance=application, data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        try:
            result = ApplicationService.request_documents(
                application,
                request.user,
                requested_documents=serializer.validated_data.get("requested_documents", []),
                notes=serializer.validated_data.get("notes", ""),
            )
        except (ApplicationTransitionError, ApplicationValidationError) as e:
            return _response(message=str(e), status_code=e.status_code)
        return _response(
            data=PartnerApplicationDetailSerializer(result).data,
            message="Documents requested from applicant.",
        )

    @action(detail=True, methods=["post"], url_path="send-to-compliance")
    def send_to_compliance(self, request, pk=None):
        application = self.get_object()
        notes = request.data.get("notes", "")
        try:
            result = ApplicationService.send_to_compliance(
                application, request.user, notes=notes,
            )
        except (ApplicationTransitionError, ApplicationValidationError) as e:
            return _response(message=str(e), status_code=e.status_code)
        return _response(
            data=PartnerApplicationDetailSerializer(result).data,
            message="Application sent to compliance check.",
        )

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        application = self.get_object()
        serializer = PartnerApplicationComplianceSerializer(
            instance=application, data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        notes = serializer.validated_data.get("notes", "")
        try:
            result = ApplicationService.approve(
                application, request.user, notes=notes,
            )
        except (ApplicationTransitionError, ApplicationValidationError) as e:
            return _response(message=str(e), status_code=e.status_code)
        return _response(
            data=PartnerApplicationDetailSerializer(result).data,
            message="Application approved successfully.",
        )

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        application = self.get_object()
        serializer = PartnerApplicationComplianceSerializer(
            instance=application, data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        notes = serializer.validated_data.get("notes", "")
        reason = serializer.validated_data.get("rejection_reason", "")
        try:
            result = ApplicationService.reject(
                application, request.user, reason=reason, notes=notes,
            )
        except (ApplicationTransitionError, ApplicationValidationError) as e:
            return _response(message=str(e), status_code=e.status_code)
        return _response(
            data=PartnerApplicationDetailSerializer(result).data,
            message="Application rejected.",
        )

    @action(detail=True, methods=["post"], url_path="suspend")
    def suspend(self, request, pk=None):
        application = self.get_object()
        serializer = PartnerApplicationComplianceSerializer(
            instance=application, data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        notes = serializer.validated_data.get("notes", "")
        try:
            result = ApplicationService.suspend(
                application, request.user, notes=notes,
            )
        except (ApplicationTransitionError, ApplicationValidationError) as e:
            return _response(message=str(e), status_code=e.status_code)
        return _response(
            data=PartnerApplicationDetailSerializer(result).data,
            message="Application suspended.",
        )

    @action(detail=True, methods=["post"], url_path="resume")
    def resume(self, request, pk=None):
        application = self.get_object()
        if application.status != "SUSPENDED":
            return _response(
                message="Only SUSPENDED applications can be resumed.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            application = ApplicationService.resume(application, request.user, request.data.get("notes", ""))
        except (ApplicationTransitionError, ApplicationValidationError) as e:
            return _response(message=str(e), status_code=e.status_code)
        return _response(
            data=PartnerApplicationDetailSerializer(application).data,
            message="Application resumed and returned to compliance check.",
        )

    @action(detail=True, methods=["post"], url_path="convert")
    def convert(self, request, pk=None):
        application = self.get_object()
        serializer = PartnerConvertSerializer(instance=application, data={})
        serializer.is_valid(raise_exception=True)
        try:
            partner = ApplicationService.convert_to_partner(
                application, request.user,
            )
        except (ApplicationTransitionError, ApplicationValidationError, PartnerConversionError) as e:
            return _response(message=str(e), status_code=e.status_code)
        application.refresh_from_db()
        return _response(
            data=PartnerApplicationDetailSerializer(application).data,
            message=f"Application converted to partner {partner.partner_number}.",
        )

    @action(detail=True, methods=["post"], url_path="run-compliance")
    def run_compliance(self, request, pk=None):
        application = self.get_object()
        result = ComplianceService.flag_high_risk(application)
        return _response(
            data=result,
            message="Compliance risk assessment completed.",
        )


class PartnerApplicationDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = PartnerApplicationDocumentSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        application_pk = self.kwargs.get("application_pk")
        application = get_object_or_404(PartnerApplication, pk=application_pk)
        if not _can_access_application(self.request.user, application):
            return PartnerApplicationDocument.objects.none()
        return PartnerApplicationDocument.objects.filter(
            application_id=application_pk,
        ).select_related("uploaded_by", "verified_by")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["application"] = get_object_or_404(
            PartnerApplication, pk=self.kwargs.get("application_pk")
        )
        return context

    def get_permissions(self):
        if self.action == "verify":
            return [permissions.IsAuthenticated(), IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def create(self, request, application_pk=None, *args, **kwargs):
        application = get_object_or_404(PartnerApplication, pk=application_pk)
        if not _can_access_application(request.user, application, write=True):
            return _response(message="You do not have permission to upload documents for this application.", status_code=status.HTTP_403_FORBIDDEN)
        if application.status in ("REJECTED", "CONVERTED"):
            return _response(message="Documents cannot be changed after rejection or conversion.", status_code=status.HTTP_400_BAD_REQUEST)
        serializer = PartnerApplicationDocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = PartnerApplicationDocument.objects.create(
            application=application,
            application_partner_type=serializer.validated_data.get("application_partner_type"),
            document_type=serializer.validated_data["document_type"],
            document_name=serializer.validated_data["document_name"],
            file=serializer.validated_data["file"],
            file_size=serializer.validated_data["file"].size,
            mime_type=serializer.validated_data["file"].content_type,
            uploaded_by=request.user,
        )
        return _response(
            data=PartnerApplicationDocumentSerializer(document).data,
            message="Document uploaded successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="verify")
    def verify(self, request, application_pk=None, pk=None):
        document = get_object_or_404(
            PartnerApplicationDocument,
            pk=pk,
            application_id=application_pk,
        )
        if not _can_access_application(request.user, document.application, approve=True):
            return _response(message="You do not have permission to verify documents.", status_code=status.HTTP_403_FORBIDDEN)
        notes = request.data.get("verification_notes", "")
        document.is_verified = True
        document.verified_by = request.user
        document.verified_at = timezone.now()
        document.verification_notes = notes
        document.save(
            update_fields=[
                "is_verified", "verified_by",
                "verified_at", "verification_notes",
            ],
        )
        return _response(
            data=PartnerApplicationDocumentSerializer(document).data,
            message="Document verified successfully.",
        )


class PartnerApplicationTaskViewSet(viewsets.ModelViewSet):
    serializer_class = PartnerApplicationTaskSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        application_pk = self.kwargs.get("application_pk")
        application = get_object_or_404(PartnerApplication, pk=application_pk)
        if not _can_access_application(self.request.user, application):
            return PartnerApplicationTask.objects.none()
        return PartnerApplicationTask.objects.filter(
            application_id=application_pk,
        ).select_related("assigned_to", "completed_by")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["application"] = get_object_or_404(
            PartnerApplication, pk=self.kwargs.get("application_pk")
        )
        return context

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def create(self, request, application_pk=None, *args, **kwargs):
        application = get_object_or_404(PartnerApplication, pk=application_pk)
        if not _can_access_application(request.user, application, write=True):
            return _response(message="You do not have permission to create tasks for this application.", status_code=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = PartnerApplicationTask.objects.create(
            application=application,
            **serializer.validated_data,
        )
        return _response(
            data=PartnerApplicationTaskSerializer(task).data,
            message="Task created successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, application_pk=None, pk=None):
        task = get_object_or_404(
            PartnerApplicationTask,
            pk=pk,
            application_id=application_pk,
        )
        if not _can_access_application(request.user, task.application, write=True):
            return _response(message="You do not have permission to manage tasks for this application.", status_code=status.HTTP_403_FORBIDDEN)
        if task.status == "COMPLETED":
            return _response(
                message="Task is already completed.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        task.status = "COMPLETED"
        task.completed_at = timezone.now()
        task.completed_by = request.user
        task.notes = request.data.get("notes", task.notes)
        task.save(
            update_fields=["status", "completed_at", "completed_by", "notes", "updated_at"],
        )
        return _response(
            data=PartnerApplicationTaskSerializer(task).data,
            message="Task completed successfully.",
        )


# ---------------------------------------------------------------------------
# Bulk Upload Views
# ---------------------------------------------------------------------------

TEMPLATE_DIR = os.path.join(settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else settings.STATIC_ROOT, "templates")

TEMPLATE_FILES = {
    "INDIVIDUAL": "Individual_Partners_Template.xlsx",
    "CORPORATE": "Corporate_Partners_Template.xlsx",
}


@api_view(["GET"])
def choices(request):
    """Return all dropdown choices for the frontend."""
    serializer = ChoicesSerializer({})
    return _response(data=serializer.data, message="Choices retrieved successfully.")


# ---------------------------------------------------------------------------
# Branch / Location / Partner Type / Contact / Bank Viewsets
# ---------------------------------------------------------------------------


class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.all().order_by("name")
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    ordering_fields = ["name", "code", "created_at"]
    ordering = ["name"]


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all().order_by("name")
    serializer_class = LocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    ordering_fields = ["name", "code", "created_at", "branch"]
    ordering = ["name"]

    def get_queryset(self):
        qs = super().get_queryset()
        branch_id = self.request.query_params.get("branch_id")
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs


def _application_partner_type_snapshot(instance):
    return {
        "id": str(instance.id),
        "application_id": str(instance.application_id),
        "partner_type_id": str(instance.partner_type_id),
        "partner_type": instance.partner_type.name,
        "branch_id": str(instance.branch_id) if instance.branch_id else None,
        "branch": instance.branch.name if instance.branch else None,
        "location_id": str(instance.location_id) if instance.location_id else None,
        "location": instance.location.name if instance.location else None,
        "region": instance.region,
        "share_data_externally": instance.share_data_externally,
        "kyc_status": instance.kyc_status,
    }


class ApplicationPartnerTypeViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationPartnerTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        application = get_object_or_404(
            PartnerApplication, pk=self.kwargs.get("application_pk")
        )
        if not _can_access_application(self.request.user, application):
            return ApplicationPartnerType.objects.none()
        return ApplicationPartnerType.objects.filter(
            application_id=application.id
        ).select_related("partner_type", "branch", "location").order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return ApplicationPartnerTypeCreateSerializer
        return ApplicationPartnerTypeSerializer

    def perform_create(self, serializer):
        instances = serializer.save()
        created = instances if isinstance(instances, list) else [instances]
        for instance in created:
            snapshot = _application_partner_type_snapshot(instance)
            PartnerApplicationEvent.objects.create(
                application=instance.application,
                event_type="UPDATED",
                actor=self.request.user,
                notes="Assigned partner type created.",
                metadata={"entity": "application_partner_type", "action": "created", "after": snapshot},
            )
            AuditService.log(
                action_type="CREATE",
                entity_type="partner_onboarding.ApplicationPartnerType",
                entity_id=instance.id,
                entity_repr=str(instance),
                after_state=snapshot,
                description="Assigned partner type created.",
                actor=self.request.user,
                request=self.request,
                app_label="partner_onboarding",
                model_name="ApplicationPartnerType",
                object_id=str(instance.id),
                object_repr=str(instance),
                changed_fields=list(snapshot.keys()),
                reason="Assigned partner type created.",
            )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        instances = serializer.instance
        if isinstance(instances, list):
            result = ApplicationPartnerTypeSerializer(instances, many=True, context=self.get_serializer_context()).data
        else:
            result = ApplicationPartnerTypeSerializer(instances, context=self.get_serializer_context()).data
        return _response(data=result, message="Partner type added successfully.", status_code=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        before = _application_partner_type_snapshot(instance)
        partial = kwargs.pop("partial", False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance.refresh_from_db()
        after = _application_partner_type_snapshot(instance)
        changed = [key for key in after if before.get(key) != after.get(key)]
        PartnerApplicationEvent.objects.create(
            application=instance.application,
            event_type="UPDATED",
            actor=self.request.user,
            notes="Assigned partner type updated.",
            metadata={"entity": "application_partner_type", "action": "updated", "before": before, "after": after, "changed_fields": changed},
        )
        AuditService.log(
            action_type="UPDATE",
            entity_type="partner_onboarding.ApplicationPartnerType",
            entity_id=instance.id,
            entity_repr=str(instance),
            before_state=before,
            after_state=after,
            changed_fields=changed,
            description="Assigned partner type updated.",
            actor=self.request.user,
            request=self.request,
            app_label="partner_onboarding",
            model_name="ApplicationPartnerType",
            object_id=str(instance.id),
            object_repr=str(instance),
            reason="Assigned partner type updated.",
        )
        return _response(data=ApplicationPartnerTypeSerializer(instance, context=self.get_serializer_context()).data, message="Partner type updated successfully.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        before = _application_partner_type_snapshot(instance)
        application = instance.application
        response = super().destroy(request, *args, **kwargs)
        PartnerApplicationEvent.objects.create(
            application=application,
            event_type="UPDATED",
            actor=request.user,
            notes="Assigned partner type removed.",
            metadata={"entity": "application_partner_type", "action": "deleted", "before": before},
        )
        AuditService.log(
            action_type="DELETE",
            entity_type="partner_onboarding.ApplicationPartnerType",
            entity_id=instance.id,
            entity_repr=before.get("partner_type", "Assigned partner type"),
            before_state=before,
            description="Assigned partner type removed.",
            actor=request.user,
            request=request,
            app_label="partner_onboarding",
            model_name="ApplicationPartnerType",
            object_id=str(instance.id),
            object_repr=before.get("partner_type", "Assigned partner type"),
            changed_fields=list(before.keys()),
            reason="Assigned partner type removed.",
        )
        return response

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["application"] = get_object_or_404(
            PartnerApplication, id=self.kwargs.get("application_pk")
        )
        return ctx


class ApplicationContactViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationContactSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        application = get_object_or_404(
            PartnerApplication, pk=self.kwargs.get("application_pk")
        )
        if not _can_access_application(self.request.user, application):
            return ApplicationContact.objects.none()
        return ApplicationContact.objects.filter(
            application_id=application.id
        ).order_by("-is_primary", "last_name")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["application"] = get_object_or_404(
            PartnerApplication, pk=self.kwargs.get("application_pk")
        )
        return context

    def perform_create(self, serializer):
        serializer.save(application_id=self.kwargs.get("application_pk"))


class ApplicationBankAccountViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationBankAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        application = get_object_or_404(
            PartnerApplication, pk=self.kwargs.get("application_pk")
        )
        if not _can_access_application(self.request.user, application):
            return ApplicationBankAccount.objects.none()
        return ApplicationBankAccount.objects.filter(
            application_id=application.id
        ).order_by("-is_primary")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["application"] = get_object_or_404(
            PartnerApplication, pk=self.kwargs.get("application_pk")
        )
        return context

    def perform_create(self, serializer):
        serializer.save(application_id=self.kwargs.get("application_pk"))


class ApplicationFieldValueViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationFieldValueSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        application = get_object_or_404(
            PartnerApplication, pk=self.kwargs.get("application_pk")
        )
        if not _can_access_application(self.request.user, application):
            return ApplicationFieldValue.objects.none()
        return ApplicationFieldValue.objects.filter(
            application_id=application.id
        ).select_related("field_config")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["application"] = get_object_or_404(
            PartnerApplication, pk=self.kwargs.get("application_pk")
        )
        return context

    def perform_create(self, serializer):
        serializer.save(application_id=self.kwargs.get("application_pk"))

    @action(detail=False, methods=["patch"], url_path="batch")
    def batch_update(self, request, application_pk=None):
        application = get_object_or_404(PartnerApplication, pk=application_pk)
        if not _can_access_application(request.user, application, write=True):
            return _response(message="You do not have permission to update fields for this application.", status_code=status.HTTP_403_FORBIDDEN)
        serializer = ApplicationFieldValueBatchSerializer(
            data=request.data,
            many=True,
            context={"request": request, "application": application},
        )
        serializer.is_valid(raise_exception=True)
        results = []
        for item in serializer.validated_data:
            fv, _ = ApplicationFieldValue.objects.update_or_create(
                application_id=application_pk,
                field_config_id=item["field_config"],
                defaults={"value_json": item.get("value_json", {})},
            )
            results.append(ApplicationFieldValueSerializer(fv).data)
        return _response(data=results, message="Field values updated.")


class ApplicationPartnerTypeSetupViewSet(viewsets.GenericViewSet):
    """Scoped setup API for one assigned partner type inside an application.

    ApplicationPartnerType is intentionally separate from the partner-master
    PartnerTypeAssignment model. These endpoints prevent the onboarding popup
    from accidentally querying the post-conversion partner namespace.
    """

    permission_classes = [permissions.IsAuthenticated]

    def _get_scope(self, request, application_pk, pk, write=False):
        application = get_object_or_404(PartnerApplication, pk=application_pk)
        if not _can_access_application(request.user, application, write=write):
            raise PermissionDenied("You do not have permission to access this application setup.")
        assignment = get_object_or_404(
            ApplicationPartnerType,
            pk=pk,
            application_id=application.id,
        )
        return application, assignment

    @staticmethod
    def _scoped_payload(request, assignment):
        payload = request.data.copy()
        payload["application_partner_type"] = str(assignment.id)
        return payload

    def field_values(self, request, application_pk=None, pk=None):
        application, assignment = self._get_scope(request, application_pk, pk, write=request.method == "PATCH")
        queryset = ApplicationFieldValue.objects.filter(
            application_id=application.id,
            application_partner_type_id=assignment.id,
        ).select_related("field_config")
        if request.method == "GET":
            return _response(
                data=ApplicationFieldValueSerializer(queryset, many=True).data,
                message="Configured field values retrieved.",
            )

        if not isinstance(request.data, list):
            return _response(message="Field values must be submitted as a list.", status_code=status.HTTP_400_BAD_REQUEST)
        serializer = ApplicationFieldValueBatchSerializer(
            data=[{**item, "application_partner_type": str(assignment.id)} for item in request.data],
            many=True,
            context={
                "request": request,
                "application": application,
                "application_partner_type": assignment,
            },
        )
        serializer.is_valid(raise_exception=True)
        results = []
        for item in serializer.validated_data:
            field_value, created = ApplicationFieldValue.objects.update_or_create(
                application_id=application.id,
                application_partner_type_id=assignment.id,
                field_config_id=item["field_config"],
                defaults={"value_json": item.get("value_json")},
            )
            if created:
                AuditService.log_create(
                    field_value,
                    actor=request.user,
                    request=request,
                    reason="Partner-type dynamic field value created.",
                )
            else:
                AuditService.log_action(
                    "UPDATE",
                    field_value,
                    actor=request.user,
                    request=request,
                    reason="Partner-type dynamic field value updated.",
                )
            results.append(field_value)
        return _response(
            data=ApplicationFieldValueSerializer(results, many=True).data,
            message="Configured field values updated.",
        )

    def contacts(self, request, application_pk=None, pk=None):
        application, assignment = self._get_scope(request, application_pk, pk, write=request.method == "POST")
        queryset = ApplicationContact.objects.filter(
            application_id=application.id,
            application_partner_type_id=assignment.id,
        )
        if request.method == "GET":
            return _response(data=ApplicationContactSerializer(queryset, many=True).data, message="Partner-type contacts retrieved.")
        serializer = ApplicationContactSerializer(
            data=self._scoped_payload(request, assignment),
            context={"request": request, "application": application},
        )
        serializer.is_valid(raise_exception=True)
        contact = serializer.save(application=application, application_partner_type=assignment)
        AuditService.log_create(contact, actor=request.user, request=request, reason="Partner-type contact created.")
        return _response(data=ApplicationContactSerializer(contact).data, message="Partner-type contact created.", status_code=status.HTTP_201_CREATED)

    def contact_detail(self, request, application_pk=None, pk=None, contact_pk=None):
        application, assignment = self._get_scope(request, application_pk, pk, write=request.method in {"PATCH", "PUT", "DELETE"})
        contact = get_object_or_404(
            ApplicationContact,
            pk=contact_pk,
            application_id=application.id,
            application_partner_type_id=assignment.id,
        )
        if request.method == "DELETE":
            AuditService.log_delete(contact, actor=request.user, request=request, reason="Partner-type contact deleted.")
            contact.delete()
            return _response(message="Partner-type contact deleted.")
        before = AuditService.snapshot(contact)
        serializer = ApplicationContactSerializer(
            contact,
            data=self._scoped_payload(request, assignment),
            partial=True,
            context={"request": request, "application": application},
        )
        serializer.is_valid(raise_exception=True)
        contact = serializer.save(application=application, application_partner_type=assignment)
        AuditService.log_update(contact, before_state=before, actor=request.user, request=request, reason="Partner-type contact updated.")
        return _response(data=ApplicationContactSerializer(contact).data, message="Partner-type contact updated.")

    def banks(self, request, application_pk=None, pk=None):
        application, assignment = self._get_scope(request, application_pk, pk, write=request.method == "POST")
        queryset = ApplicationBankAccount.objects.filter(
            application_id=application.id,
            application_partner_type_id=assignment.id,
        )
        if request.method == "GET":
            return _response(data=ApplicationBankAccountSerializer(queryset, many=True).data, message="Partner-type bank accounts retrieved.")
        serializer = ApplicationBankAccountSerializer(
            data=self._scoped_payload(request, assignment),
            context={"request": request, "application": application},
        )
        serializer.is_valid(raise_exception=True)
        account = serializer.save(application=application, application_partner_type=assignment)
        AuditService.log_create(account, actor=request.user, request=request, reason="Partner-type bank account created.")
        return _response(data=ApplicationBankAccountSerializer(account).data, message="Partner-type bank account created.", status_code=status.HTTP_201_CREATED)

    def bank_detail(self, request, application_pk=None, pk=None, bank_pk=None):
        application, assignment = self._get_scope(request, application_pk, pk, write=request.method in {"PATCH", "PUT", "DELETE"})
        account = get_object_or_404(
            ApplicationBankAccount,
            pk=bank_pk,
            application_id=application.id,
            application_partner_type_id=assignment.id,
        )
        if request.method == "DELETE":
            AuditService.log_delete(account, actor=request.user, request=request, reason="Partner-type bank account deleted.")
            account.delete()
            return _response(message="Partner-type bank account deleted.")
        before = AuditService.snapshot(account)
        serializer = ApplicationBankAccountSerializer(
            account,
            data=self._scoped_payload(request, assignment),
            partial=True,
            context={"request": request, "application": application},
        )
        serializer.is_valid(raise_exception=True)
        account = serializer.save(application=application, application_partner_type=assignment)
        AuditService.log_update(account, before_state=before, actor=request.user, request=request, reason="Partner-type bank account updated.")
        return _response(data=ApplicationBankAccountSerializer(account).data, message="Partner-type bank account updated.")


@api_view(["GET"])
def download_template(request):
    """Download the Excel template for the given partner type."""
    partner_type = request.query_params.get("partner_type", "").upper()
    if partner_type not in ("INDIVIDUAL", "CORPORATE"):
        return Response(
            {"success": False, "status_code": 400, "message": "Invalid partner_type. Use INDIVIDUAL or CORPORATE.",
             "data": None, "meta": {"timestamp": timezone.now().isoformat(), "version": "v1"}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    filename = TEMPLATE_FILES[partner_type]
    filepath = os.path.join(TEMPLATE_DIR, filename)

    if not os.path.exists(filepath):
        return Response(
            {"success": False, "status_code": 404, "message": f"Template file not found: {filename}",
             "data": None, "meta": {"timestamp": timezone.now().isoformat(), "version": "v1"}},
            status=status.HTTP_404_NOT_FOUND,
        )

    response = FileResponse(open(filepath, "rb"), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@api_view(["POST"])
def bulk_upload(request):
    """Accept an Excel file, validate, and create partner applications."""
    if not request.user.is_authenticated:
        return Response(
            {"success": False, "status_code": 401, "message": "Authentication required.",
             "data": None, "meta": {"timestamp": timezone.now().isoformat(), "version": "v1"}},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    file = request.FILES.get("file")
    if not file:
        return _response(
            message="No file provided. Please upload an Excel file.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Validate file extension
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in (".xlsx", ".xls"):
        return _response(
            message=f"Invalid file type '{ext}'. Only .xlsx files are accepted.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Parse and validate
    try:
        partner_type, rows = validate_and_parse_excel(file)
    except ValueError as e:
        return _response(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if not rows:
        return _response(
            message="The Excel file contains no data rows.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    imported = 0
    skipped = 0
    errors = []

    for row in rows:
        if row["_errors"]:
            skipped += 1
            errors.append({
                "row": row["_row"],
                "message": "; ".join(row["_errors"]),
            })
            continue

        try:
            data = {k: v for k, v in row.items() if not k.startswith("_")}
            ApplicationService.deduplicate_drafts(data.get("email"))
            data["application_number"] = ApplicationService.generate_application_number(data.get("partner_type"))
            data["submitted_by"] = request.user
            PartnerApplication.objects.create(**data)
            imported += 1
        except Exception as e:
            skipped += 1
            errors.append({
                "row": row["_row"],
                "message": str(e),
            })

    return _response(
        data={"imported": imported, "skipped": skipped, "errors": errors},
        message=f"Bulk upload completed. {imported} imported, {skipped} skipped.",
        status_code=status.HTTP_200_OK if imported > 0 else status.HTTP_400_BAD_REQUEST,
    )


class UnifiedOnboardingRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A unified read-only view that combines applications and converted partners
    into a single list, allowing cross-entity filtering and pagination.
    """
    queryset = UnifiedOnboardingRecord.objects.all()
    serializer_class = UnifiedOnboardingRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filterset_class = UnifiedOnboardingRecordFilter
    search_fields = ["reference_number", "display_name", "email", "mobile_number"]
    ordering_fields = ["created_at", "application_status", "kyc_status", "reference_number"]
    ordering = ["-created_at"]

