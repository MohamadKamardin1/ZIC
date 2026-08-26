import csv
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from django.db.models import Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import not_found
from .models import Policy, PolicyStatus
from .permissions import HasOLPolicyPermission
from .serializers import PolicyDetailSerializer, PolicyListSerializer

ORDERING_FIELDS = {
    "policy_number": "policy_number",
    "sum_assured": "sum_assured",
    "premium_amount": "premium_amount",
    "risk_commencement_date": "risk_commencement_date",
    "maturity_date": "maturity_date",
    "status": "status",
    "created_at": "created_at",
}


def _money(value):
    return format(Decimal(str(value or 0)).quantize(Decimal("0.01")), "f")


def _uuid_value(value):
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def build_policy_queryset(params):
    queryset = Policy.objects.select_related("proposal_ref", "partner", "agent").all()

    status = params.get("status")
    if status:
        queryset = queryset.filter(status__iexact=status)

    currency = params.get("currency")
    if currency:
        queryset = queryset.filter(currency__iexact=currency)

    product = params.get("product") or params.get("product_plan") or params.get("product_plan_ref")
    if product:
        queryset = queryset.filter(product_plan_ref__icontains=product)

    agent = (params.get("agent") or "").strip()
    if agent:
        agent_query = (
            Q(agent__partner_number__icontains=agent)
            | Q(agent__legal_name__icontains=agent)
            | Q(agent__first_name__icontains=agent)
            | Q(agent__surname__icontains=agent)
        )
        agent_id = _uuid_value(agent)
        if agent_id:
            agent_query |= Q(agent_id=agent_id)
        queryset = queryset.filter(agent_query)

    branch = (params.get("branch") or params.get("branch_id") or "").strip()
    if branch:
        branch_id = _uuid_value(branch)
        if branch_id:
            queryset = queryset.filter(partner__type_assignments__branch_id=branch_id).distinct()
        else:
            queryset = queryset.filter(
                Q(partner__type_assignments__branch__code__icontains=branch)
                | Q(partner__type_assignments__branch__name__icontains=branch)
            ).distinct()

    date_filters = (
        ("risk_commencement_from", "risk_commencement_date__gte"),
        ("commencement_from", "risk_commencement_date__gte"),
        ("risk_commencement_to", "risk_commencement_date__lte"),
        ("commencement_to", "risk_commencement_date__lte"),
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
            | Q(agent__partner_number__icontains=search)
            | Q(agent__legal_name__icontains=search)
        )

    ordering = (params.get("ordering") or "-created_at").strip()
    descending = ordering.startswith("-")
    ordering_key = ordering[1:] if descending else ordering
    field = ORDERING_FIELDS.get(ordering_key, "created_at")
    return queryset.order_by(f"{'-' if descending else ''}{field}", "policy_number")


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


def _paginated_payload(queryset, request):
    page, page_size = _pagination(request.query_params)
    total = queryset.count()
    start = (page - 1) * page_size
    rows = queryset[start : start + page_size]
    return {
        "results": PolicyListSerializer(rows, many=True).data,
        "count": total,
        "page": page,
        "page_size": page_size,
        "next": page * page_size < total,
        "previous": page > 1,
    }


class PolicyListView(APIView):
    action = "list"
    permission_classes = [HasOLPolicyPermission]

    def get(self, request):
        return Response({"data": _paginated_payload(build_policy_queryset(request.query_params), request)})


class PolicyDetailView(APIView):
    action = "retrieve"
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


class PolicyKPIsView(APIView):
    action = "kpi"
    permission_classes = [HasOLPolicyPermission]

    def get(self, request):
        queryset = build_policy_queryset(request.query_params)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        month_end = today + timedelta(days=30)
        active = queryset.filter(status=PolicyStatus.ACTIVE)
        lapsed = queryset.filter(status=PolicyStatus.LAPSED)
        maturing = active.filter(maturity_date__gte=today, maturity_date__lte=month_end)
        currency = (request.query_params.get("currency") or "").strip().upper()

        total_sum_assured = active.aggregate(value=Sum("sum_assured"))["value"] or 0
        lapsed_value = lapsed.aggregate(value=Sum("sum_assured"))["value"] or 0
        by_currency = {
            row["currency"]: _money(row["value"])
            for row in active.values("currency").annotate(value=Sum("sum_assured")).order_by("currency")
        }
        return Response(
            {
                "data": {
                    "total_active_policies": active.count(),
                    "total_sum_assured": _money(total_sum_assured),
                    "new_policies_this_month": queryset.filter(
                        risk_commencement_date__gte=month_start,
                        risk_commencement_date__lte=today,
                    ).count(),
                    "lapsed_policies_count": lapsed.count(),
                    "lapsed_policies_value": _money(lapsed_value),
                    "maturing_soon_count": maturing.count(),
                    "currency": currency or (next(iter(by_currency)) if len(by_currency) == 1 else "MULTI"),
                    "sum_assured_by_currency": by_currency,
                    "timestamp": timezone.now().isoformat(),
                }
            }
        )


class PolicyExportView(APIView):
    action = "export"
    permission_classes = [HasOLPolicyPermission]

    def get(self, request):
        queryset = build_policy_queryset(request.query_params)
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="ol-policies.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "Policy Number",
                "Policyholder",
                "Product / Plan",
                "Sum Assured",
                "Premium",
                "Currency",
                "Status",
                "Commencement Date",
                "Maturity Date",
                "Agent",
            ]
        )
        for row in PolicyListSerializer(queryset, many=True).data:
            writer.writerow(
                [
                    row["policy_number"],
                    row["policyholder_display"],
                    row["product_plan_display"],
                    row["sum_assured"],
                    row["premium_amount"],
                    row["currency"],
                    row["status_display"],
                    row["risk_commencement_date"],
                    row["maturity_date"],
                    row["agent_display"],
                ]
            )
        return response
