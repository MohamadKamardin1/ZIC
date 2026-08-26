import csv
import uuid
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum
from django.http import HttpResponse
from django.utils import timezone

from apps.governance.services.audit_service import AuditService
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import loan_not_found
from .models import LoanStatus, OLLoan
from .permissions import has_ol_loan_permission
from .serializers import OLLoanDetailSerializer, OLLoanListSerializer
from apps.ol_parameters.models import OLLoanInterestControl, OLLoanSystemSetup


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
        "results": OLLoanListSerializer(
            queryset[start : start + page_size],
            many=True,
            context={"request": request},
        ).data,
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
        queryset = OLLoan.objects.select_related("policy_ref", "policy_ref__agent", "partner").all()
        search = params.get("q") or params.get("search")
        if search:
            queryset = queryset.filter(
                Q(loan_number__icontains=search)
                | Q(policy_ref__policy_number__icontains=search)
                | Q(partner__legal_name__icontains=search)
                | Q(partner__partner_number__icontains=search)
            )
        queryset = _apply_loan_filters(queryset, params)
        queryset = _order_loans(queryset, params.get("ordering", "-created_at"))
        return Response({"data": _paginate(queryset, request)})


class OLLoanKPIView(APIView):
    permission_classes = [MustViewOLLoansPermission]

    def get(self, request):
        queryset = _apply_loan_filters(
            OLLoan.objects.select_related("policy_ref", "policy_ref__agent", "partner").all(),
            request.query_params,
        )
        amounts = _currency_kpis(queryset.filter(disbursement_date__isnull=False), queryset)
        return Response({"data": _loan_kpis(queryset, amounts)})


class OLLoanExportView(APIView):
    permission_classes = [MustViewOLLoansPermission]

    def get(self, request):
        queryset = _order_loans(
            _apply_loan_filters(
                OLLoan.objects.select_related("policy_ref", "policy_ref__agent", "partner").all(),
                request.query_params,
            ),
            request.query_params.get("ordering", "-created_at"),
        )
        rows = OLLoanListSerializer(queryset, many=True, context={"request": request}).data
        fields = (
            "loan_number",
            "policy_number",
            "policyholder_name",
            "product_display",
            "principal_amount",
            "outstanding_balance",
            "status_display",
            "disbursement_date",
            "maturity_date",
            "agent_display",
            "branch_display",
            "allowed_actions",
        )
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="ol-loans.csv"'
        csv_writer = csv.writer(response)
        csv_writer.writerow(fields)
        for row in rows:
            csv_writer.writerow(
                [
                    ",".join(row[field]) if field == "allowed_actions" else row.get(field, "")
                    for field in fields
                ]
            )
        AuditService.log(
            "READ",
            "ol_loans.loan_export",
            None,
            entity_repr="OL Loans CSV export",
            description="OL Loans table exported as CSV.",
            actor=request.user,
            action="EXPORT",
            app_label="ol_loans",
            model_name="loanexport",
            object_repr="OL Loans CSV export",
            reason="User exported the filtered OL Loans table.",
            request=request,
            after_state={"count": queryset.count(), "filters": dict(request.query_params.lists())},
        )
        return response


def _true(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _date_filter(queryset, field, value, *, lower):
    if not value:
        return queryset
    try:
        parsed = date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return queryset
    return queryset.filter(**{f"{field}__{'gte' if lower else 'lte'}": parsed})


def _valid_uuid(value):
    try:
        uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return False
    return True


def _apply_loan_filters(queryset, params):
    status = params.get("status")
    if status:
        queryset = queryset.filter(status__iexact=status)
    currency = params.get("currency")
    if currency:
        queryset = queryset.filter(currency__iexact=currency)
    product = params.get("product") or params.get("product_code")
    if product:
        queryset = queryset.filter(policy_ref__product_plan_ref__icontains=product)
    agent = params.get("agent") or params.get("agent_id")
    if agent:
        agent_query = Q(policy_ref__agent__legal_name__icontains=agent) | Q(
            policy_ref__agent__partner_number__icontains=agent
        )
        if _valid_uuid(agent):
            agent_query |= Q(policy_ref__agent_id=agent)
        queryset = queryset.filter(agent_query)
    branch = params.get("branch") or params.get("branch_id")
    if branch:
        queryset = queryset.filter(
            Q(policy_ref__contract_snapshot__branch_id__icontains=branch)
            | Q(policy_ref__contract_snapshot__branch_code__icontains=branch)
            | Q(policy_ref__contract_snapshot__branch_name__icontains=branch)
            | Q(policy_ref__contract_snapshot__branch__icontains=branch)
        )
    policy_id = params.get("policy_id") or params.get("policy")
    if policy_id:
        queryset = queryset.filter(policy_ref_id=policy_id)
    partner_id = params.get("partner_id") or params.get("partner")
    if partner_id:
        queryset = queryset.filter(partner_id=partner_id)

    date_from = params.get("date_from") or params.get("disbursement_date_from")
    date_to = params.get("date_to") or params.get("disbursement_date_to")
    queryset = _date_filter(queryset, "disbursement_date", date_from, lower=True)
    queryset = _date_filter(queryset, "disbursement_date", date_to, lower=False)
    queryset = _date_filter(queryset, "maturity_date", params.get("maturity_from"), lower=True)
    queryset = _date_filter(queryset, "maturity_date", params.get("maturity_to"), lower=False)
    queryset = _date_filter(queryset, "created_at", params.get("created_from"), lower=True)
    queryset = _date_filter(queryset, "created_at", params.get("created_to"), lower=False)

    if _true(params.get("overdue_only")):
        queryset = queryset.filter(
            schedules__due_date__lt=timezone.localdate(),
            schedules__balance__gt=0,
        )
    if _true(params.get("balance_gt_zero")) or _true(params.get("balance_only")):
        queryset = queryset.filter(outstanding_balance__gt=0)
    return queryset.distinct()


def _order_loans(queryset, ordering):
    order_map = {
        "loan_number": "loan_number",
        "policy_number": "policy_ref__policy_number",
        "policyholder_name": "partner__legal_name",
        "product": "policy_ref__product_plan_ref",
        "product_display": "policy_ref__product_plan_ref",
        "agent": "policy_ref__agent__legal_name",
        "status": "status",
        "principal": "principal_amount",
        "principal_amount": "principal_amount",
        "outstanding_balance": "outstanding_balance",
        "disbursement_date": "disbursement_date",
        "maturity_date": "maturity_date",
        "created_at": "created_at",
    }
    ordering = str(ordering or "-created_at")
    descending = ordering.startswith("-")
    key = ordering.lstrip("-")
    field = order_map.get(key, "created_at")
    return queryset.order_by(f"{'-' if descending else ''}{field}", "loan_number")


def _currency_kpis(disbursed_queryset, queryset):
    currency_codes = sorted(set(queryset.values_list("currency", flat=True)))
    rows = {}
    for currency in currency_codes:
        rows[currency] = {
            "total_disbursed_period": str(
                disbursed_queryset.filter(currency=currency).aggregate(total=Sum("disbursed_amount"))["total"]
                or Decimal("0.00")
            ),
            "total_outstanding": str(
                queryset.filter(currency=currency).aggregate(total=Sum("outstanding_balance"))["total"]
                or Decimal("0.00")
            ),
        }
    return rows


def _loan_kpis(queryset, amounts):
    active_statuses = {LoanStatus.ACTIVE, LoanStatus.PARTIALLY_REPAID}
    settled_statuses = {LoanStatus.SETTLED, LoanStatus.CLOSED}
    currency_codes = sorted(amounts)
    currency = currency_codes[0] if len(currency_codes) == 1 else "MULTI"
    if len(currency_codes) == 1:
        total_disbursed_period = amounts[currency_codes[0]]["total_disbursed_period"]
        total_outstanding = amounts[currency_codes[0]]["total_outstanding"]
    else:
        total_disbursed_period = {
            code: values["total_disbursed_period"] for code, values in amounts.items()
        }
        total_outstanding = {code: values["total_outstanding"] for code, values in amounts.items()}
    return {
        "total_disbursed_period": total_disbursed_period,
        "total_outstanding": total_outstanding,
        "active_count": queryset.filter(status__in=active_statuses).count(),
        "defaulted_count": queryset.filter(status=LoanStatus.DEFAULTED).count(),
        "settled_count": queryset.filter(status__in=settled_statuses).count(),
        "currency": currency,
        "amounts_by_currency": amounts,
        "timestamp": timezone.now(),
    }


class OLLoanDetailView(APIView):
    permission_classes = [MustViewOLLoansPermission]

    def get(self, request, loan_id):
        loan = (
            OLLoan.objects.select_related("policy_ref", "policy_ref__agent", "partner")
            .prefetch_related(
                "disbursement",
                "schedules",
                "repayments",
                "interest_accruals",
                "offsets",
            )
            .filter(pk=loan_id)
            .first()
        )
        if loan is None:
            raise loan_not_found(str(loan_id))
        return Response({"data": OLLoanDetailSerializer(loan, context={"request": request}).data})


class OLLoanOptionsView(APIView):
    """Return active/effective SmartSelect-compatible loan reference options."""

    permission_classes = [MustViewOLLoansPermission]

    def get(self, request, kind):
        as_of = _parse_date(request.query_params.get("as_of"))
        if kind == "repayment-terms":
            rows = _repayment_terms(as_of, request)
        elif kind == "compounding-frequencies":
            rows = _compounding_frequencies(as_of, request)
        elif kind == "offset-rules":
            rows = _offset_rules(as_of, request)
        else:
            return Response({"data": {"kind": kind, "results": [], "count": 0}})
        AuditService.log(
            "READ",
            "ol_loans.loan_option",
            None,
            entity_repr=kind,
            description=f"OL Loan option catalog '{kind}' read.",
            actor=request.user,
            action="READ_OPTIONS",
            app_label="ol_loans",
            model_name="loanoption",
            object_repr=kind,
            reason="Loan option configuration read for UI or financial decision.",
            request=request,
            after_state={"kind": kind, "count": len(rows), "as_of": as_of.isoformat()},
        )
        return Response({"data": _paginate_options(rows, request, kind)})


def _parse_date(value):
    if not value:
        return date.today()
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return date.today()


def _effective_setup_rows(model, as_of, request):
    queryset = model.objects.filter(is_active=True).filter(
        Q(effective_from__isnull=True) | Q(effective_from__lte=as_of),
        Q(effective_to__isnull=True) | Q(effective_to__gte=as_of),
    )
    product_id = request.query_params.get("product_id") or request.query_params.get("product")
    plan_id = request.query_params.get("plan_id") or request.query_params.get("plan")
    if product_id:
        queryset = queryset.filter(Q(product_id=product_id) | Q(product__isnull=True))
    if plan_id:
        queryset = queryset.filter(Q(plan_id=plan_id) | Q(plan__isnull=True))
    return queryset.order_by("code")


def _humanize(code):
    return str(code or "").replace("_", " ").title()


def _repayment_terms(as_of, request):
    options = {}
    for setup in _effective_setup_rows(OLLoanSystemSetup, as_of, request):
        values = setup.repayment_options if isinstance(setup.repayment_options, list) else []
        if isinstance(setup.repayment_options, dict):
            values = [
                {"code": key, "enabled": value} if not isinstance(value, dict) else {"code": key, **value}
                for key, value in setup.repayment_options.items()
            ]
        for raw in values:
            if isinstance(raw, str):
                raw = {"code": raw, "enabled": True}
            if not isinstance(raw, dict) or raw.get("enabled", True) is False:
                continue
            code = str(raw.get("code") or raw.get("value") or "").strip().upper()
            if not code:
                continue
            options.setdefault(
                code,
                {
                    "value": code,
                    "label": str(raw.get("label") or raw.get("name") or _humanize(code)),
                    "meta": {"parameter_code": setup.code, "as_of": as_of.isoformat()},
                },
            )
    return list(options.values())


def _compounding_frequencies(as_of, request):
    from apps.ol_parameters.models import OLLoanCompoundingFrequency

    labels = dict(OLLoanCompoundingFrequency.choices)
    options = {}
    for setup in _effective_setup_rows(OLLoanInterestControl, as_of, request):
        code = (setup.compounding_frequency or "").strip().upper()
        if code:
            options.setdefault(
                code,
                {
                    "value": code,
                    "label": labels.get(code, _humanize(code)),
                    "meta": {
                        "parameter_code": setup.code,
                        "interest_rate": str(setup.interest_rate),
                        "interest_calculation_basis": setup.interest_calculation_basis,
                        "as_of": as_of.isoformat(),
                    },
                },
            )
    return list(options.values())


def _offset_rules(as_of, request):
    from apps.ol_parameters.models import OLLoanEffectRule

    labels = dict(OLLoanEffectRule.choices)
    options = {}
    source_fields = (
        ("CLAIM", "effect_on_claim"),
        ("SURRENDER", "effect_on_surrender"),
        ("MATURITY", "effect_on_maturity"),
    )
    for setup in _effective_setup_rows(OLLoanSystemSetup, as_of, request):
        for source_type, field_name in source_fields:
            code = (getattr(setup, field_name, "") or "").strip().upper()
            if not code:
                continue
            row = options.setdefault(
                code,
                {
                    "value": code,
                    "label": labels.get(code, _humanize(code)),
                    "meta": {"sources": [], "parameter_codes": [], "as_of": as_of.isoformat()},
                },
            )
            if source_type not in row["meta"]["sources"]:
                row["meta"]["sources"].append(source_type)
            if setup.code not in row["meta"]["parameter_codes"]:
                row["meta"]["parameter_codes"].append(setup.code)
    return list(options.values())


def _paginate_options(rows, request, kind):
    search = (request.query_params.get("q") or "").strip().lower()
    if search:
        rows = [row for row in rows if search in f"{row['value']} {row['label']}".lower()]
    rows = sorted(rows, key=lambda row: (row["label"].lower(), row["value"]))
    page = _page_value(request, "page", 1, 1, 100_000)
    page_size = _page_value(request, "page_size", 50, 1, 100)
    total = len(rows)
    start = (page - 1) * page_size
    return {
        "kind": kind,
        "results": rows[start : start + page_size],
        "count": total,
        "page": page,
        "page_size": page_size,
        "next": page * page_size < total,
        "previous": page > 1,
    }
