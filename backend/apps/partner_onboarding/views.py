import logging
import os

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
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
)
from apps.partner_onboarding.services import ApplicationService, ComplianceService
from apps.partner_onboarding.exceptions import (
    ApplicationTransitionError,
    ApplicationValidationError,
    PartnerConversionError,
)
from apps.partner_onboarding.filters import PartnerApplicationFilter
from apps.partner_onboarding.validators import validate_and_parse_excel
from apps.partner_onboarding.permissions import (
    IsOwnerOrReviewer,
    CanSubmitApplication,
    CanReviewApplication,
    CanPerformComplianceAction,
    CanRejectApplication,
    CanConvertApplication,
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


class PartnerApplicationViewSet(viewsets.ModelViewSet):
    queryset = PartnerApplication.objects.select_related(
        "submitted_by", "reviewed_by", "approved_by",
    ).prefetch_related("documents", "tasks")
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

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        if self.action in ("update", "partial_update", "destroy"):
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
        for attr, value in serializer.validated_data.items():
            setattr(application, attr, value)
        application.save()
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
        except ApplicationTransitionError as e:
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
            result = ApplicationService.request_documents(application, request.user)
        except ApplicationTransitionError as e:
            return _response(message=str(e), status_code=e.status_code)
        requested_docs = serializer.validated_data.get("requested_documents", [])
        for doc_type in requested_docs:
            PartnerApplicationTask.objects.create(
                application=result,
                task_type="DOCUMENT_REQUEST",
                title=f"Upload {doc_type}",
                description=f"Please upload the required {doc_type} document.",
                priority="HIGH",
            )
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
        except ApplicationTransitionError as e:
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
        except ApplicationTransitionError as e:
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
        except ApplicationTransitionError as e:
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
        except ApplicationTransitionError as e:
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
        application.status = "COMPLIANCE_CHECK"
        application.save(update_fields=["status", "updated_at"])
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
        except (ApplicationTransitionError, PartnerConversionError) as e:
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
        return PartnerApplicationDocument.objects.filter(
            application_id=application_pk,
        ).select_related("uploaded_by", "verified_by")

    def get_permissions(self):
        if self.action == "verify":
            return [permissions.IsAuthenticated(), IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def create(self, request, application_pk=None, *args, **kwargs):
        application = get_object_or_404(PartnerApplication, pk=application_pk)
        serializer = PartnerApplicationDocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = PartnerApplicationDocument.objects.create(
            application=application,
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
        return PartnerApplicationTask.objects.filter(
            application_id=application_pk,
        ).select_related("assigned_to", "completed_by")

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def create(self, request, application_pk=None, *args, **kwargs):
        application = get_object_or_404(PartnerApplication, pk=application_pk)
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
