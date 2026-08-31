from datetime import date

from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import MaturityInstallmentError, not_found
from .models import OLMaturityInstallmentPlan
from .permissions import HasOLMaturityInstallmentPermission
from .serializers import OLMaturityInstallmentPlanDetailSerializer, OLMaturityInstallmentPlanListSerializer

SORT_FIELDS = {
    "plan_number": "plan_number",
    "policy_number": "policy_ref__policy_number",
    "start_date": "start_date",
    "end_date": "end_date",
    "status": "status",
    "created_at": "created_at",
}


def _parse_date(value, field_name):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise MaturityInstallmentError(
            message=f"{field_name.replace('_', ' ').title()} must use YYYY-MM-DD format.",
            error_code="INSTALLMENT_INVALID_FILTER",
            status_code=400,
            field_errors={field_name: ["Enter a valid date in YYYY-MM-DD format."]},
            resolution_steps=[
                "Correct the date filter and retry the search.",
                "Leave the filter blank when no date restriction is needed.",
            ],
        ) from exc


def _paginate(queryset, request):
    try:
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
    except (TypeError, ValueError) as exc:
        raise MaturityInstallmentError(
            message="Installment plan list pagination values must be whole numbers.",
            error_code="INSTALLMENT_INVALID_FILTER",
            status_code=400,
            field_errors={
                "page": ["Use a positive whole-number page."],
                "page_size": ["Use a whole number from 1 to 100."],
            },
            resolution_steps=[
                "Set page to 1 or another positive whole number.",
                "Set page_size between 1 and 100, then retry.",
            ],
        ) from exc
    if page < 1 or page_size < 1 or page_size > 100:
        raise MaturityInstallmentError(
            message="Installment plan list pagination values are outside the supported range.",
            error_code="INSTALLMENT_INVALID_FILTER",
            status_code=400,
            field_errors={"page": ["Page must be at least 1."], "page_size": ["Page size must be between 1 and 100."]},
            resolution_steps=[
                "Set page to 1 or another positive whole number.",
                "Set page_size between 1 and 100, then retry.",
            ],
        )

    total = queryset.count()
    start = (page - 1) * page_size
    rows = queryset[start : start + page_size]
    return {
        "count": total,
        "results": rows,
        "page": page,
        "page_size": page_size,
        "next": page * page_size < total,
        "previous": page > 1,
    }


def _base_queryset():
    return (
        OLMaturityInstallmentPlan.objects.select_related(
            "policy_ref",
            "policy_ref__partner",
            "maturity_claim_ref",
            "partner",
            "created_by",
        )
        .prefetch_related("items", "config")
        .order_by("-created_at", "plan_number")
    )


def _apply_filters(queryset, params):
    query = (params.get("q") or params.get("search") or "").strip()
    if query:
        queryset = queryset.filter(
            Q(plan_number__icontains=query)
            | Q(policy_ref__policy_number__icontains=query)
            | Q(maturity_claim_ref__claim_number__icontains=query)
            | Q(partner__legal_name__icontains=query)
            | Q(partner__first_name__icontains=query)
            | Q(partner__surname__icontains=query)
        ).distinct()
    if params.get("status"):
        queryset = queryset.filter(status__iexact=params["status"])
    if params.get("frequency"):
        queryset = queryset.filter(frequency__iexact=params["frequency"])
    if params.get("policy_number"):
        queryset = queryset.filter(policy_ref__policy_number__iexact=params["policy_number"])
    date_from = _parse_date(params.get("date_from"), "date_from")
    date_to = _parse_date(params.get("date_to"), "date_to")
    if date_from:
        queryset = queryset.filter(start_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(start_date__lte=date_to)
    sort = (params.get("sort") or "").strip()
    if sort:
        descending = sort.startswith("-")
        field = sort[1:] if descending else sort
        if field not in SORT_FIELDS:
            raise MaturityInstallmentError(
                message="The requested installment plan sort field is not supported.",
                error_code="INSTALLMENT_INVALID_FILTER",
                status_code=400,
                field_errors={"sort": [f"Choose one of: {', '.join(SORT_FIELDS)}."]},
                resolution_steps=["Choose a supported table column and retry the search."],
            )
        queryset = queryset.order_by(("-" if descending else "") + SORT_FIELDS[field])
    return queryset


class InstallmentPlanListView(APIView):
    permission_classes = [HasOLMaturityInstallmentPermission]
    action = "view"

    def get(self, request):
        queryset = _apply_filters(_base_queryset(), request.query_params)
        page = _paginate(queryset, request)
        page["results"] = OLMaturityInstallmentPlanListSerializer(
            page.pop("results"), many=True, context={"request": request}
        ).data
        return Response({"data": page})


class InstallmentPlanDetailView(APIView):
    permission_classes = [HasOLMaturityInstallmentPermission]
    action = "view"

    def get(self, request, plan_id):
        plan = _base_queryset().filter(pk=plan_id).first()
        if not plan:
            raise not_found()
        return Response({"data": OLMaturityInstallmentPlanDetailSerializer(plan, context={"request": request}).data})
