from __future__ import annotations

import json

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from apps.governance.services.audit_service import AuditService

from .models import BrandingConfiguration, DocumentInstance
from .services.engine import CompanyBranding, DocumentEngine, DocumentEngineError, DocumentTypeRegistry


def _success(data, message, status_code=status.HTTP_200_OK):
    return Response(
        {
            "success": True,
            "status_code": status_code,
            "message": message,
            "data": data,
        },
        status=status_code,
    )


def _failure(message, status_code, details=None, code=None, resolution_steps=None):
    payload = {
        "success": False,
        "status_code": status_code,
        "message": message,
        "error": details or message,
    }
    if code:
        payload["code"] = code
    if resolution_steps:
        payload["resolution_steps"] = resolution_steps
    return Response(payload, status=status_code)


class DocumentRenderView(APIView):
    authentication_classes = api_settings.DEFAULT_AUTHENTICATION_CLASSES
    permission_classes = [IsAuthenticated]

    def post(self, request, document_type, object_id):
        try:
            instance = DocumentEngine.render(
                document_type=document_type,
                object_id=object_id,
                actor=request.user,
                request=request,
            )
            document_payload = DocumentEngine.payload(instance, request=request, actor=request.user, signed=True)
            return _success(
                {
                    **document_payload,
                    "instance": document_payload,
                    "preview_blob_base64_or_url": document_payload["preview_url"],
                    "signed_download_url": document_payload["signed_download_url"],
                },
                "Document rendered successfully.",
                status.HTTP_201_CREATED,
            )
        except DocumentEngineError as exc:
            return _failure(str(exc), exc.status_code, code=exc.code, resolution_steps=exc.resolution_steps)


class DocumentInstanceListView(APIView):
    authentication_classes = api_settings.DEFAULT_AUTHENTICATION_CLASSES
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not self._can_list(request.user):
            return _failure("You do not have permission to view generated documents.", status.HTTP_403_FORBIDDEN)

        queryset = DocumentInstance.objects.select_related("template", "generated_by").order_by("-generated_at", "-created_at")
        source_type = (request.query_params.get("source_type") or "").strip().lower()
        object_id = (request.query_params.get("object_id") or "").strip()
        if source_type:
            if "." not in source_type:
                return _failure("source_type must use the app_label.model format.", status.HTTP_400_BAD_REQUEST)
            source_app, source_model = source_type.split(".", 1)
            queryset = queryset.filter(source_app_label=source_app, source_model=source_model)
        if object_id:
            queryset = queryset.filter(source_object_id=object_id)

        try:
            page = max(int(request.query_params.get("page", 1)), 1)
            page_size = min(max(int(request.query_params.get("page_size", 50)), 1), 200)
        except (TypeError, ValueError):
            return _failure("page and page_size must be positive integers.", status.HTTP_400_BAD_REQUEST)
        all_instances = list(queryset)
        visible = []
        for instance in all_instances:
            try:
                definition = DocumentTypeRegistry.for_instance(instance)
                source = DocumentEngine.resolve_source(definition, instance.source_object_id)
                DocumentEngine.ensure_access(request.user, definition, source)
            except (DocumentEngineError, Http404):
                continue
            visible.append(instance)
        start = (page - 1) * page_size
        page_items = visible[start : start + page_size]
        return _success(
            {
                "count": len(visible),
                "page": page,
                "page_size": page_size,
                "results": [DocumentEngine.payload(item, request=request, actor=request.user, signed=True) for item in page_items],
            },
            "Generated documents retrieved.",
        )

    @staticmethod
    def _can_list(actor):
        if getattr(actor, "is_superuser", False):
            return True
        if DocumentEngine.has_permission(actor, "documents.view"):
            return True
        return any(DocumentEngine.has_permission(actor, definition.permission) for definition in DocumentTypeRegistry.definitions())


class BrandingConfigurationView(APIView):
    authentication_classes = api_settings.DEFAULT_AUTHENTICATION_CLASSES
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _allowed(actor):
        return getattr(actor, "is_superuser", False) or DocumentEngine.has_permission(actor, "documents.manage") or DocumentEngine.has_permission(actor, "system_parameters.manage")

    @staticmethod
    def _payload(configuration):
        return {
            "code": configuration.code,
            "version": configuration.version,
            "logo_url": configuration.logo_file.url if configuration.logo_file else None,
            "company_name": configuration.company_name,
            "address": configuration.address,
            "phone": configuration.phone,
            "email": configuration.email,
            "registration_number": configuration.registration_number,
            "footer_legal_text": configuration.footer_legal_text,
            "accent_colors": configuration.accent_colors,
            "is_active": configuration.is_active,
            "created_at": configuration.created_at.isoformat() if configuration.created_at else None,
        }

    def get(self, request):
        if not self._allowed(request.user):
            return _failure("You do not have permission to manage document branding.", status.HTTP_403_FORBIDDEN)
        all_versions = BrandingConfiguration.objects.filter(code="COMPANY_BRANDING").order_by("-version")[:20]
        configuration = next((item for item in all_versions if item.is_active), None)
        history = [self._payload(item) for item in all_versions]
        if configuration is None:
            resolved = CompanyBranding.resolve()
            return _success({
                "code": "COMPANY_BRANDING",
                "version": 0,
                "logo_url": resolved.logo_url or None,
                "company_name": resolved.company_name,
                "address": resolved.address,
                "phone": resolved.phone,
                "email": resolved.email,
                "registration_number": resolved.registration_number,
                "footer_legal_text": resolved.footer_legal_text,
                "accent_colors": resolved.accent_colors,
                "is_active": True,
                "created_at": None,
                "history": history,
            }, "Effective document branding retrieved.")
        payload = self._payload(configuration)
        payload["history"] = history
        return _success(payload, "Document branding retrieved.")

    def post(self, request):
        if not self._allowed(request.user):
            return _failure("You do not have permission to manage document branding.", status.HTTP_403_FORBIDDEN)
        raw_colors = request.data.get("accent_colors", {})
        if isinstance(raw_colors, str):
            try:
                raw_colors = json.loads(raw_colors)
            except json.JSONDecodeError:
                return _failure("accent_colors must be a valid JSON object.", status.HTTP_400_BAD_REQUEST)
        if not isinstance(raw_colors, dict):
            return _failure("accent_colors must be a JSON object.", status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            current = BrandingConfiguration.objects.select_for_update().filter(
                code="COMPANY_BRANDING", is_active=True
            ).order_by("-version").first()
            def value(field, default=""):
                return request.data.get(field, getattr(current, field, default) if current else default)

            company_name = str(value("company_name", "")).strip()
            if not company_name:
                return _failure(
                    "company_name is required so documents have an identified issuer.",
                    status.HTTP_400_BAD_REQUEST,
                    {"company_name": ["Enter the legal company name."]},
                )
            if not request.data.get("accent_colors") and current:
                raw_colors = current.accent_colors
            version = (current.version + 1) if current else 1
            retired_state = AuditService.snapshot(current) if current else None
            if current:
                current.is_active = False
                current.save(update_fields=["is_active"])
                AuditService.log_action(
                    action="BRANDING_VERSION_RETIRED",
                    instance=current,
                    actor=request.user,
                    request=request,
                    before_state=retired_state,
                    after_state=AuditService.snapshot(current),
                    reason="Previous document branding version retired by a newer configuration.",
                    changed_fields=["is_active"],
                    source_channel="API",
                )
            configuration = BrandingConfiguration.objects.create(
                code="COMPANY_BRANDING",
                version=version,
                logo_file=request.FILES.get("logo_file") or (current.logo_file.name if current and current.logo_file else None),
                company_name=company_name,
                address=str(value("address")),
                phone=str(value("phone")),
                email=str(value("email")),
                registration_number=str(value("registration_number")),
                footer_legal_text=str(value("footer_legal_text", "This document is system generated.")),
                accent_colors=raw_colors,
                is_active=True,
                created_by=request.user,
            )
            AuditService.log_action(
                action="BRANDING_VERSION_CREATED",
                instance=configuration,
                actor=request.user,
                request=request,
                after_state=AuditService.snapshot(configuration),
                reason="Document branding configuration version created.",
                source_channel="API",
            )
        return _success(self._payload(configuration), "Document branding version created.", status.HTTP_201_CREATED)


class DocumentDownloadView(APIView):
    """Protected stream endpoint: Bearer is primary, a signed PDF ticket is supplementary."""

    authentication_classes = api_settings.DEFAULT_AUTHENTICATION_CLASSES
    permission_classes = [AllowAny]

    def get(self, request, pk):
        instance = get_object_or_404(DocumentInstance.objects.select_related("template"), pk=pk)
        is_preview = request.path.rstrip("/").endswith("/preview")
        ticket = request.query_params.get("ticket") if not is_preview else None
        if not ticket and not getattr(request.user, "is_authenticated", False):
            raise NotAuthenticated("Authentication credentials were not provided.")
        try:
            return DocumentEngine.stream(
                instance=instance,
                actor=request.user if getattr(request.user, "is_authenticated", False) else None,
                request=request,
                ticket=ticket,
                format_name="html" if is_preview else "pdf",
            )
        except DocumentEngineError as exc:
            return _failure(str(exc), exc.status_code, code=exc.code, resolution_steps=exc.resolution_steps)
