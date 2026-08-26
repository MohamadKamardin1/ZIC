from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import not_found
from .models import Policy
from .permissions import HasOLPolicyPermission
from .serializers import PolicyDetailSerializer, PolicyListSerializer


class PolicyListView(APIView):
    permission_classes = [HasOLPolicyPermission]

    def get(self, request):
        params = request.query_params
        queryset = Policy.objects.select_related("proposal_ref", "partner", "agent").all()

        for parameter, field in (
            ("status", "status__iexact"),
            ("currency", "currency__iexact"),
            ("agent", "agent_id"),
            ("partner", "partner_id"),
        ):
            value = params.get(parameter)
            if value:
                queryset = queryset.filter(**{field: value})

        product_plan = params.get("product_plan") or params.get("product_plan_ref")
        if product_plan:
            queryset = queryset.filter(product_plan_ref__icontains=product_plan)

        date_filters = (
            ("risk_commencement_from", "risk_commencement_date__gte"),
            ("risk_commencement_to", "risk_commencement_date__lte"),
            ("maturity_from", "maturity_date__gte"),
            ("maturity_to", "maturity_date__lte"),
        )
        for parameter, field in date_filters:
            value = params.get(parameter)
            if value:
                queryset = queryset.filter(**{field: value})

        search = (params.get("search") or "").strip()
        if search:
            queryset = queryset.filter(
                Q(policy_number__icontains=search)
                | Q(product_plan_ref__icontains=search)
                | Q(partner__partner_number__icontains=search)
                | Q(partner__legal_name__icontains=search)
                | Q(partner__first_name__icontains=search)
                | Q(partner__surname__icontains=search)
                | Q(partner__identification_number__icontains=search)
                | Q(partner__national_id__icontains=search)
                | Q(partner__phone__icontains=search)
                | Q(partner__mobile_number__icontains=search)
            )

        ordering = params.get("ordering", "-created_at")
        ordering_map = {
            "policy_number": "policy_number",
            "sum_assured": "sum_assured",
            "premium_amount": "premium_amount",
            "risk_commencement_date": "risk_commencement_date",
            "maturity_date": "maturity_date",
            "status": "status",
            "created_at": "created_at",
        }
        descending = ordering.startswith("-")
        ordering_key = ordering[1:] if descending else ordering
        queryset = queryset.order_by(
            f"{'-' if descending else ''}{ordering_map.get(ordering_key, 'created_at')}",
            "policy_number",
        )

        page, page_size = self._pagination(params)
        total = queryset.count()
        start = (page - 1) * page_size
        rows = queryset[start : start + page_size]
        return Response(
            {
                "data": {
                    "results": PolicyListSerializer(rows, many=True).data,
                    "count": total,
                    "page": page,
                    "page_size": page_size,
                    "next": page * page_size < total,
                    "previous": page > 1,
                }
            }
        )

    @staticmethod
    def _pagination(params):
        try:
            page = max(1, int(params.get("page", 1)))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(100, max(1, int(params.get("page_size", 20))))
        except (TypeError, ValueError):
            page_size = 20
        return page, page_size


class PolicyDetailView(APIView):
    permission_classes = [HasOLPolicyPermission]

    def get(self, request, policy_id):
        policy = (
            Policy.objects.select_related("proposal_ref", "partner", "agent")
            .prefetch_related("members", "riders", "benefits", "endorsements", "audit_logs")
            .filter(pk=policy_id)
            .first()
        )
        if not policy:
            raise not_found(policy_id)
        return Response({"data": PolicyDetailSerializer(policy).data})
