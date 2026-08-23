from __future__ import annotations

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from .services.engine import DocumentEngine, DocumentEngineError, DocumentTypeRegistry
from .models import DocumentInstance


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


def _failure(message, status_code, details=None):
    return Response(
        {
            "success": False,
            "status_code": status_code,
            "message": message,
            "error": details or message,
        },
        status=status_code,
    )


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
            return _success(
                DocumentEngine.payload(instance, request=request, actor=request.user, signed=True),
                "Document rendered successfully.",
                status.HTTP_201_CREATED,
            )
        except DocumentEngineError as exc:
            return _failure(str(exc), exc.status_code)


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
            return _failure(str(exc), exc.status_code)
