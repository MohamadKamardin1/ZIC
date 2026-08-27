import csv
from datetime import date
from decimal import Decimal

from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import ClaimError, not_found
from .models import ClaimStatus, OLClaim
from .permissions import HasOLClaimPermission
from .serializers import OLClaimDetailSerializer, OLClaimListSerializer


SORT_FIELDS = {
    "claim_number": "claim_number",
    "policy_number": "policy_ref__policy_number",
    "claim_date": "claim_date",
    "admitted_date": "admitted_date",
    "status": "status",
    "created_at": "created_at",
}


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


def _parse_boolean(value, field_name):
    if value in (None, ""):
        return None
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ClaimError(
        message=f"{field_name.replace('_', ' ').title()} must be true or false.",
        error_code="CLAIM_INVALID_FILTER",
        status_code=400,
        field_errors={field_name: ["Choose true or false."]},
        resolution_steps=["Correct the filter value and retry the search."],
    )


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
            "policy_ref__proposal_ref",
            "policy_ref__proposal_ref__quotation",
            "claimant_ref",
            "registered_by",
            "admitted_by",
            "loan_offset",
            "requisition__payment_requisition",
            "requisition__approval_request",
        )
        .prefetch_related("items", "claimants", "documents", "file_notes", "requisition")
        .order_by("-created_at", "claim_number")
    )


def _apply_claim_filters(queryset, params):
    query = (params.get("q") or params.get("search") or "").strip()
    if query:
        queryset = queryset.filter(
            Q(claim_number__icontains=query)
            | Q(policy_ref__policy_number__icontains=query)
            | Q(policy_ref__partner__legal_name__icontains=query)
            | Q(policy_ref__partner__first_name__icontains=query)
            | Q(policy_ref__partner__surname__icontains=query)
            | Q(claimants__name__icontains=query)
        ).distinct()
    if params.get("status"):
        queryset = queryset.filter(status__iexact=params["status"])
    if params.get("claim_type"):
        queryset = queryset.filter(claim_type__iexact=params["claim_type"])
    if params.get("product"):
        queryset = queryset.filter(policy_ref__product_plan_ref__icontains=params["product"])
    if params.get("branch"):
        branch = params["branch"].strip()
        queryset = queryset.filter(
            Q(policy_ref__proposal_ref__quotation__location__icontains=branch)
            | Q(policy_ref__proposal_ref__quotation__location_master__code__iexact=branch)
            | Q(policy_ref__proposal_ref__quotation__location_master__branch__code__iexact=branch)
            | Q(policy_ref__proposal_ref__quotation__location_master__branch__name__iexact=branch)
        ).distinct()
    fraud_flag = _parse_boolean(params.get("fraud_flag"), "fraud_flag")
    if fraud_flag is not None:
        queryset = queryset.filter(fraud_flag=fraud_flag)
    date_from = _parse_date(params.get("date_from"), "date_from")
    date_to = _parse_date(params.get("date_to"), "date_to")
    if date_from:
        queryset = queryset.filter(claim_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(claim_date__lte=date_to)
    sort = (params.get("sort") or "").strip()
    if sort:
        descending = sort.startswith("-")
        field = sort[1:] if descending else sort
        if field not in SORT_FIELDS:
            raise ClaimError(
                message="The requested claim sort field is not supported.",
                error_code="CLAIM_INVALID_FILTER",
                status_code=400,
                field_errors={"sort": [f"Choose one of: {', '.join(SORT_FIELDS)}."]},
                resolution_steps=["Choose a supported table column and retry the search."],
            )
        queryset = queryset.order_by(("-" if descending else "") + SORT_FIELDS[field])
    return queryset


def _claim_amount(claim):
    return sum(
        ((item.approved_amount if item.approved_amount is not None else item.calculated_amount) or Decimal("0.00") for item in claim.items.all()),
        Decimal("0.00"),
    ).quantize(Decimal("0.01"))


def _money(value):
    return str((value or Decimal("0.00")).quantize(Decimal("0.01")))


class ClaimListView(APIView):
    permission_classes = [HasOLClaimPermission]
    action = "view"

    def get(self, request):
        queryset = _apply_claim_filters(_base_queryset(), request.query_params)
        page = _paginate(queryset, request)
        page["results"] = OLClaimListSerializer(
            page.pop("results"), many=True, context={"request": request}
        ).data
        return Response({"data": page})


class ClaimKpisView(APIView):
    permission_classes = [HasOLClaimPermission]
    action = "view"

    def get(self, request):
        queryset = _apply_claim_filters(_base_queryset(), request.query_params)
        claims = list(queryset)
        outstanding = Decimal("0.00")
        settled = Decimal("0.00")
        pending_assessment = 0
        currency_totals = {}
        for claim in claims:
            amount = _claim_amount(claim)
            currency = claim.policy_ref.currency or "TZS"
            currency_totals.setdefault(currency, {"outstanding_amount": Decimal("0.00"), "settled_amount": Decimal("0.00")})
            if claim.status == ClaimStatus.SETTLED:
                settled_amount = claim.settlement_amount if claim.settlement_amount is not None else amount
                settled += settled_amount
                currency_totals[currency]["settled_amount"] += settled_amount
            else:
                outstanding += amount
                currency_totals[currency]["outstanding_amount"] += amount
            if claim.status in {ClaimStatus.REGISTERED, ClaimStatus.PENDING_MEDICAL, ClaimStatus.ASSESSMENT}:
                pending_assessment += 1
        currencies = sorted(currency_totals)
        currency = currencies[0] if len(currencies) == 1 else ("MULTI" if currencies else "TZS")
        payload = {
            "total_claims": len(claims),
            "outstanding_amount": _money(outstanding),
            "settled_amount_period": _money(settled),
            "pending_assessment_count": pending_assessment,
            "currency": currency,
            "currency_totals": {
                code: {key: _money(value) for key, value in values.items()}
                for code, values in currency_totals.items()
            },
            "filters_applied": {
                key: request.query_params.get(key)
                for key in ("q", "search", "status", "claim_type", "product", "branch", "date_from", "date_to", "fraud_flag")
                if request.query_params.get(key) not in (None, "")
            },
            "timestamp": timezone.now().isoformat(),
        }
        return Response({"data": payload})


class ClaimExportView(APIView):
    permission_classes = [HasOLClaimPermission]
    action = "view"

    def get(self, request):
        queryset = _apply_claim_filters(_base_queryset(), request.query_params)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="ol-claims-export.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "Claim Number",
                "Policy Number",
                "Policyholder Name",
                "Claim Type",
                "Claim Date",
                "Admitted Date",
                "Amount",
                "Currency",
                "Status",
                "Fraud Flag",
            ]
        )
        for claim in queryset:
            writer.writerow(
                [
                    claim.claim_number,
                    claim.policy_ref.policy_number,
                    claim.policy_ref.partner.legal_name or str(claim.policy_ref.partner),
                    claim.claim_type,
                    claim.claim_date.isoformat() if claim.claim_date else "",
                    claim.admitted_date.isoformat() if claim.admitted_date else "",
                    _money(claim.settlement_amount if claim.status == ClaimStatus.SETTLED and claim.settlement_amount is not None else _claim_amount(claim)),
                    claim.policy_ref.currency,
                    claim.get_status_display(),
                    "Yes" if claim.fraud_flag else "No",
                ]
            )
        return response


class ClaimDetailView(APIView):
    permission_classes = [HasOLClaimPermission]
    action = "view"

    def get(self, request, claim_id):
        claim = _base_queryset().filter(pk=claim_id).first()
        if not claim:
            raise not_found()
        return Response({"data": OLClaimDetailSerializer(claim, context={"request": request}).data})
