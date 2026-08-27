from datetime import date

from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import ClaimError, not_found, registry_error
from .models import OLClaim
from .permissions import HasOLClaimPermission
from .serializers import OLClaimDetailSerializer, OLClaimListSerializer


def _parse_date(value, field_name):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ClaimError(
            message=f"{field_name.replace('_', ' ').title()} must use YYYY-MM-DD format.",
            error_code="CLAIM_INVALID_FILTER",
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
        raise ClaimError(
            message="Claim list pagination values must be whole numbers.",
            error_code="CLAIM_INVALID_FILTER",
            status_code=400,
            field_errors={"page": ["Use a positive whole-number page."], "page_size": ["Use a whole number from 1 to 100."]},
            resolution_steps=[
                "Set page to 1 or another positive whole number.",
                "Set page_size between 1 and 100, then retry.",
            ],
        ) from exc
    if page < 1 or page_size < 1 or page_size > 100:
        raise ClaimError(
            message="Claim list pagination values are outside the supported range.",
            error_code="CLAIM_INVALID_FILTER",
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
        OLClaim.objects.select_related(
            "policy_ref",
            "policy_ref__partner",
            "claimant_ref",
            "registered_by",
            "admitted_by",
            "loan_offset",
        )
        .prefetch_related("items", "claimants", "documents", "file_notes", "requisition")
        .order_by("-created_at", "claim_number")
    )


class ClaimListView(APIView):
    permission_classes = [HasOLClaimPermission]
    action = "view"

    def get(self, request):
        queryset = _base_queryset()
        params = request.query_params
        query = (params.get("q") or params.get("search") or "").strip()
        if query:
            queryset = queryset.filter(
                Q(claim_number__icontains=query)
                | Q(policy_ref__policy_number__icontains=query)
                | Q(policy_ref__partner__legal_name__icontains=query)
                | Q(policy_ref__partner__first_name__icontains=query)
                | Q(policy_ref__partner__surname__icontains=query)
            )
        if params.get("status"):
            queryset = queryset.filter(status__iexact=params["status"])
        if params.get("claim_type"):
            queryset = queryset.filter(claim_type__iexact=params["claim_type"])
        if params.get("product"):
            queryset = queryset.filter(policy_ref__product_plan_ref=params["product"])
        if params.get("fraud_flag") in {"true", "1", "TRUE"}:
            queryset = queryset.filter(fraud_flag=True)
        elif params.get("fraud_flag") in {"false", "0", "FALSE"}:
            queryset = queryset.filter(fraud_flag=False)
        date_from = _parse_date(params.get("date_from"), "date_from")
        date_to = _parse_date(params.get("date_to"), "date_to")
        if date_from:
            queryset = queryset.filter(claim_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(claim_date__lte=date_to)
        page = _paginate(queryset, request)
        page["results"] = OLClaimListSerializer(page.pop("results"), many=True).data
        return Response({"data": page})


class ClaimDetailView(APIView):
    permission_classes = [HasOLClaimPermission]
    action = "view"

    def get(self, request, claim_id):
        claim = _base_queryset().filter(pk=claim_id).first()
        if not claim:
            raise not_found()
        return Response({"data": OLClaimDetailSerializer(claim).data})
