"""Options endpoints for OL Maturity Installments (frequencies and terms)."""

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ol_parameters.models import OLAnticipatedEndowmentInstallmentRate

from .errors import MaturityInstallmentError
from .models import InstallmentFrequency
from .permissions import HasOLMaturityInstallmentPermission
from .services.calculation import FREQUENCY_MONTHS

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100
DEFAULT_TERM_YEARS = list(range(1, 31))


def _q_filter(items, query):
    if not query:
        return items
    needle = query.casefold()
    return [
        item
        for item in items
        if needle in str(item.get("label", "")).casefold()
        or needle in str(item.get("value", "")).casefold()
        or needle in str(item.get("meta", {})).casefold()
    ]


def _option(value, label, **meta):
    return {"value": str(value), "label": label, "meta": meta}


def _paged(items, request):
    try:
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", DEFAULT_PAGE_SIZE))
    except (TypeError, ValueError) as exc:
        raise MaturityInstallmentError(
            message="Maturity installment options pagination values must be whole numbers.",
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
    if page < 1 or page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise MaturityInstallmentError(
            message="Maturity installment options pagination values are outside the supported range.",
            error_code="INSTALLMENT_INVALID_FILTER",
            status_code=400,
            field_errors={"page": ["Page must be at least 1."], "page_size": ["Page size must be between 1 and 100."]},
            resolution_steps=[
                "Set page to 1 or another positive whole number.",
                "Set page_size between 1 and 100, then retry.",
            ],
        )
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": items[start:end],
        "results": items[start:end],
        "count": total,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_next": end < total,
            "has_previous": page > 1,
        },
    }


def frequency_options(query=""):
    options = [
        _option(
            frequency.value,
            frequency.label,
            months_between=FREQUENCY_MONTHS[frequency.value],
            payout_per_year=12 // FREQUENCY_MONTHS[frequency.value] if FREQUENCY_MONTHS[frequency.value] else 1,
        )
        for frequency in InstallmentFrequency
    ]
    return _q_filter(options, query)


def term_options(query="", product_code=None):
    rows = OLAnticipatedEndowmentInstallmentRate.objects.filter(is_active=True)
    if product_code:
        rows = rows.filter(product__code__iexact=product_code)
    years = set()
    for row in rows.iterator():
        low = row.term_from or 1
        high = row.term_to or low
        if high < low:
            high = low
        years.update(range(low, high + 1))
    source = "INSTALLMENT_RATE_TABLE" if years else "DEFAULT"
    if not years:
        years = set(DEFAULT_TERM_YEARS)
    options = [
        _option(year, f"{year} year{'s' if year != 1 else ''}", term_months=year * 12, source=source)
        for year in sorted(years)
    ]
    return _q_filter(options, query)


class InstallmentOptionsBaseView(APIView):
    permission_classes = [HasOLMaturityInstallmentPermission]
    action = "view"

    def _response(self, entity, items, request):
        data = _paged(items, request)
        data["entity"] = entity
        return Response(
            {
                "success": True,
                "status_code": 200,
                "message": "OL maturity installment options retrieved successfully.",
                "data": data,
            }
        )


class InstallmentFrequencyOptionsView(InstallmentOptionsBaseView):
    def get(self, request):
        return self._response(
            "frequencies",
            frequency_options(request.query_params.get("q", "").strip()),
            request,
        )


class InstallmentTermOptionsView(InstallmentOptionsBaseView):
    def get(self, request):
        return self._response(
            "terms",
            term_options(
                request.query_params.get("q", "").strip(),
                request.query_params.get("product") or request.query_params.get("product_code"),
            ),
            request,
        )
