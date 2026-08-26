from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import loan_not_found
from .models import OLLoan
from .permissions import has_ol_loan_permission
from .serializers import OLLoanDetailSerializer, OLLoanListSerializer


class MustViewOLLoansPermission(IsAuthenticated):
    def has_permission(self, request, view):
        return bool(super().has_permission(request, view) and has_ol_loan_permission(request.user, "view"))


def _page_value(request, name, default, minimum, maximum):
    try:
        value = int(request.query_params.get(name, default))
    except (TypeError, ValueError):
        value = default
    return min(maximum, max(minimum, value))


def _paginate(queryset, request):
    page = _page_value(request, "page", 1, 1, 100_000)
    page_size = _page_value(request, "page_size", 20, 1, 100)
    total = queryset.count()
    start = (page - 1) * page_size
    return {
        "results": OLLoanListSerializer(queryset[start : start + page_size], many=True).data,
        "count": total,
        "page": page,
        "page_size": page_size,
        "next": page * page_size < total,
        "previous": page > 1,
    }


class OLLoanListView(APIView):
    permission_classes = [MustViewOLLoansPermission]

    def get(self, request):
        params = request.query_params
        queryset = OLLoan.objects.select_related("policy_ref", "partner").all()

        search = params.get("q") or params.get("search")
        if search:
            queryset = queryset.filter(
                Q(loan_number__icontains=search)
                | Q(policy_ref__policy_number__icontains=search)
                | Q(partner__legal_name__icontains=search)
                | Q(partner__partner_number__icontains=search)
            )
        for field in ("status", "currency", "compounding_frequency"):
            value = params.get(field)
            if value:
                queryset = queryset.filter(**{f"{field}__iexact": value})
        policy_id = params.get("policy_id") or params.get("policy")
        if policy_id:
            queryset = queryset.filter(policy_ref_id=policy_id)
        partner_id = params.get("partner_id") or params.get("partner")
        if partner_id:
            queryset = queryset.filter(partner_id=partner_id)
        maturity_from = params.get("maturity_from")
        if maturity_from:
            queryset = queryset.filter(maturity_date__gte=maturity_from)
        maturity_to = params.get("maturity_to")
        if maturity_to:
            queryset = queryset.filter(maturity_date__lte=maturity_to)

        order_map = {
            "loan_number": "loan_number",
            "status": "status",
            "principal_amount": "principal_amount",
            "outstanding_balance": "outstanding_balance",
            "maturity_date": "maturity_date",
            "created_at": "created_at",
        }
        ordering = params.get("ordering", "-created_at")
        descending = ordering.startswith("-")
        key = ordering[1:] if descending else ordering
        queryset = queryset.order_by(f"{'-' if descending else ''}{order_map.get(key, 'created_at')}", "loan_number")
        return Response({"data": _paginate(queryset, request)})


class OLLoanDetailView(APIView):
    permission_classes = [MustViewOLLoansPermission]

    def get(self, request, loan_id):
        loan = (
            OLLoan.objects.select_related("policy_ref", "partner")
            .prefetch_related("schedules", "repayments", "interest_accruals", "offsets")
            .filter(pk=loan_id)
            .first()
        )
        if loan is None:
            raise loan_not_found(str(loan_id))
        return Response({"data": OLLoanDetailSerializer(loan).data})
