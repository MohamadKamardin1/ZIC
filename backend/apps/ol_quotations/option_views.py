from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .option_registry import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, get_options, list_entities


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
