from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .option_registry import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, get_options, list_entities
from .quick_create import (
    QUICK_CREATE_REASON,
    create_quick_option,
    get_quick_create_schema,
    list_quick_create_entities,
)


def _error_message(error: Exception) -> dict:
    if hasattr(error, "message_dict"):
        return {key: [str(item) for item in values] for key, values in error.message_dict.items()}
    if hasattr(error, "detail"):
        detail = error.detail
        if isinstance(detail, dict):
            return detail
        return {"detail": str(detail)}
    return {"detail": str(error)}


class OLOptionRegistryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, entity: str):
        try:
            page = max(int(request.query_params.get("page", 1)), 1)
            page_size = min(max(int(request.query_params.get("page_size", request.query_params.get("limit", DEFAULT_PAGE_SIZE))), 1), MAX_PAGE_SIZE)
        except (TypeError, ValueError):
            return Response(
                {
                    "success": False,
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "page and page_size must be positive integers.",
                    "data": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            canonical, result = get_options(
                entity,
                q=request.query_params.get("q", "").strip(),
                page=page,
                page_size=page_size,
            )
        except KeyError:
            return Response(
                {
                    "success": False,
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Unknown OL option entity '{entity}'.",
                    "data": {"available_entities": list_entities()},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "success": True,
                "status_code": status.HTTP_200_OK,
                "message": "OL options retrieved successfully.",
                "data": {
                    "entity": canonical,
                    "items": result.items,
                    "results": result.items,
                    "count": result.count,
                    "pagination": {
                        "page": result.page,
                        "page_size": result.page_size,
                        "total": result.count,
                        "has_next": result.page * result.page_size < result.count,
                        "has_previous": result.page > 1,
                    },
                },
            }
        )


class OLOptionQuickCreateSchemaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, entity: str):
        try:
            schema = get_quick_create_schema(entity)
        except KeyError:
            return Response(
                {
                    "success": False,
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Quick-create is not registered for '{entity}'.",
                    "data": {"available_entities": list_quick_create_entities()},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {
                "success": True,
                "status_code": status.HTTP_200_OK,
                "message": "OL quick-create schema retrieved successfully.",
                "data": schema,
            }
        )


class OLOptionQuickCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, entity: str):
        try:
            created = create_quick_option(entity, request.data, request.user, request)
        except KeyError:
            return Response(
                {
                    "success": False,
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Quick-create is not registered for '{entity}'.",
                    "data": {"available_entities": list_quick_create_entities()},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except PermissionDenied as exc:
            return Response(
                {
                    "success": False,
                    "status_code": status.HTTP_403_FORBIDDEN,
                    "message": str(exc.detail if hasattr(exc, "detail") else exc),
                    "data": None,
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except (DjangoValidationError, ValueError, TypeError) as exc:
            return Response(
                {
                    "success": False,
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Quick-create validation failed.",
                    "errors": _error_message(exc),
                    "data": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "success": True,
                "status_code": status.HTTP_201_CREATED,
                "message": QUICK_CREATE_REASON,
                "data": {
                    "entity": entity,
                    "option": created,
                    "value": created["value"],
                    "label": created["label"],
                },
            },
            status=status.HTTP_201_CREATED,
        )
