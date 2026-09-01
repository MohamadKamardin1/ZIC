import csv
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import MaturityInstallmentError, not_found
from .models import InstallmentItemStatus, InstallmentPlanStatus, OLInstallmentItem, OLMaturityInstallmentPlan
from .permissions import HasOLMaturityInstallmentPermission
from .serializers import (
    OLMaturityInstallmentPlanDetailSerializer,
    OLMaturityInstallmentPlanListSerializer,
    _partner_name,
)

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


def _parse_boolean(value, field_name):
    if value in (None, ""):
        return None
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise MaturityInstallmentError(
        message=f"{field_name.replace('_', ' ').title()} must be true or false.",
        error_code="INSTALLMENT_INVALID_FILTER",
        status_code=400,
        field_errors={field_name: ["Choose true or false."]},
        resolution_steps=["Correct the filter value and retry the search."],
    )


def _money(value):
    return str((value or Decimal("0.00")).quantize(Decimal("0.01")))


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
            "policy_ref__proposal_ref",
            "policy_ref__proposal_ref__quotation",
            "policy_ref__proposal_ref__quotation__location_master",
            "policy_ref__proposal_ref__quotation__location_master__branch",
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
    if params.get("product"):
        queryset = queryset.filter(policy_ref__product_plan_ref__icontains=params["product"].strip())
    if params.get("branch"):
        branch = params["branch"].strip()
        queryset = queryset.filter(
            Q(policy_ref__proposal_ref__quotation__location__icontains=branch)
            | Q(policy_ref__proposal_ref__quotation__location_master__code__iexact=branch)
            | Q(policy_ref__proposal_ref__quotation__location_master__branch__code__iexact=branch)
            | Q(policy_ref__proposal_ref__quotation__location_master__branch__name__iexact=branch)
        ).distinct()
    missed_only = _parse_boolean(params.get("missed_only"), "missed_only")
    if missed_only is not None:
        matched = Q(items__status=InstallmentItemStatus.MISSED)
        queryset = queryset.filter(matched).distinct() if missed_only else queryset.exclude(matched).distinct()
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


def _paid_amount_by_plan(plan_ids):
    rows = (
        OLInstallmentItem.objects.filter(
            plan_ref_id__in=plan_ids,
            status=InstallmentItemStatus.PAID,
        )
        .values("plan_ref_id")
        .annotate(total=Sum("amount"))
    )
    return {row["plan_ref_id"]: row["total"] for row in rows}


class InstallmentPlanKpisView(APIView):
    permission_classes = [HasOLMaturityInstallmentPermission]
    action = "view"

    def get(self, request):
        queryset = _apply_filters(_base_queryset(), request.query_params)
        plan_ids = list(queryset.values_list("pk", flat=True))
        today = timezone.localdate()
        items = OLInstallmentItem.objects.filter(plan_ref_id__in=plan_ids)
        upcoming_payouts = items.filter(
            status__in=(InstallmentItemStatus.SCHEDULED, InstallmentItemStatus.PAYMENT_PENDING),
            due_date__gte=today,
        ).count()
        payload = {
            "total_plans_active": queryset.filter(status=InstallmentPlanStatus.ACTIVE).count(),
            "total_upcoming_payouts": upcoming_payouts,
            "missed_payments_count": items.filter(status=InstallmentItemStatus.MISSED).count(),
            "completed_plans_count": queryset.filter(status=InstallmentPlanStatus.COMPLETED).count(),
            "filters_applied": {
                key: request.query_params.get(key)
                for key in (
                    "q",
                    "search",
                    "status",
                    "product",
                    "branch",
                    "date_from",
                    "date_to",
                    "missed_only",
                )
                if request.query_params.get(key) not in (None, "")
            },
            "timestamp": timezone.now().isoformat(),
        }
        return Response({"data": payload})


class InstallmentPlanExportView(APIView):
    permission_classes = [HasOLMaturityInstallmentPermission]
    action = "view"

    def get(self, request):
        queryset = _apply_filters(_base_queryset(), request.query_params)
        paid_map = _paid_amount_by_plan([plan.pk for plan in queryset])
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="ol-maturity-installments-export.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "Plan Number",
                "Policy Number",
                "Policyholder Name",
                "Total Amount",
                "Paid Amount",
                "Balance",
                "Status",
                "Start Date",
                "End Date",
            ]
        )
        for plan in queryset:
            paid = paid_map.get(plan.pk, Decimal("0.00"))
            writer.writerow(
                [
                    plan.plan_number,
                    plan.policy_ref.policy_number,
                    _partner_name(plan.partner),
                    _money(plan.total_payable_amount),
                    _money(paid),
                    _money(Decimal(plan.total_payable_amount) - Decimal(paid)),
                    plan.get_status_display(),
                    plan.start_date.isoformat() if plan.start_date else "",
                    plan.end_date.isoformat() if plan.end_date else "",
                ]
            )
        return response
