from datetime import date

from django.db.models import Q

from apps.governance.services.audit_service import AuditService
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import loan_not_found
from .models import OLLoan
from apps.ol_parameters.models import OLLoanInterestControl, OLLoanSystemSetup
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
    except ValueError:
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
