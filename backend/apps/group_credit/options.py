"""GC Parameters — SmartSelects Options Endpoints.

Each view returns a JSON array of ``{value, label, meta}`` items for frontend
SmartSelects. ``value`` is the record's UUID, ``label`` is its display name
(names, never UUIDs), and ``meta`` carries additional catalog fields.
"""

from uuid import UUID

from django.db.models import Q
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.group_credit.models import (
    GCClaimType,
    GCHealthQuestionnaire,
    GCProduct,
    GCSchemeType,
)
from apps.group_credit.serializers import gc_display_value

DEFAULT_LIMIT = 500


class GCOptionsBaseView(APIView):
    """Shared option building for an active catalog queryset."""

    permission_classes = [permissions.IsAuthenticated]
    model = None
    search_fields = ["code", "name"]
    option_limit = DEFAULT_LIMIT

    def base_queryset(self):
        return self.model.objects.filter(is_active=True)

    def get_queryset(self):
        queryset = self.base_queryset()
        search = self.request.query_params.get("search", "").strip()
        if search:
            query = Q()
            for field in self.search_fields:
                query |= Q(**{f"{field}__icontains": search})
            queryset = queryset.filter(query)
        return queryset

    def build_option(self, obj):
        return {
            "value": str(obj.pk),
            "label": gc_display_value(obj),
            "meta": {
                "code": getattr(obj, "code", None),
                "is_active": getattr(obj, "is_active", True),
            },
        }

    def get(self, request):
        options = [self.build_option(obj) for obj in self.get_queryset()[: self.option_limit]]
        return Response(options)


class GCSchemeTypeOptionView(GCOptionsBaseView):
    model = GCSchemeType
    search_fields = ["code", "name"]

    def build_option(self, obj):
        option = super().build_option(obj)
        option["meta"]["partner_type_restriction"] = obj.partner_type_restriction
        return option


class GCProductOptionView(GCOptionsBaseView):
    model = GCProduct
    search_fields = ["code", "name"]
    select_related = ["scheme_type_ref"]

    def base_queryset(self):
        queryset = super().base_queryset().select_related(*self.select_related)
        scheme_type = self.request.query_params.get("scheme_type", "").strip()
        if scheme_type:
            try:
                UUID(scheme_type)
                queryset = queryset.filter(scheme_type_ref_id=scheme_type)
            except (ValueError, AttributeError):
                queryset = queryset.filter(scheme_type_ref__code__iexact=scheme_type)
        return queryset

    def build_option(self, obj):
        option = super().build_option(obj)
        option["meta"]["scheme_type_code"] = (
            obj.scheme_type_ref.code if obj.scheme_type_ref else None
        )
        option["meta"]["currency"] = obj.currency
        return option


class GCQuestionnaireOptionView(GCOptionsBaseView):
    model = GCHealthQuestionnaire
    search_fields = ["code", "name"]

    def build_option(self, obj):
        option = super().build_option(obj)
        option["meta"]["version"] = obj.version
        return option


class GCClaimTypeOptionView(GCOptionsBaseView):
    model = GCClaimType
    search_fields = ["code", "name"]

    def build_option(self, obj):
        option = super().build_option(obj)
        option["meta"]["category"] = obj.category
        return option
