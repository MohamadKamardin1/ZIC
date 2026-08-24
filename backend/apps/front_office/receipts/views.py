from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.front_office.receipts.models import Receipt
from apps.front_office.receipts.permissions import has_receipt_permission
from apps.front_office.receipts.serializers import (
    ReceiptBaseSerializer,
    ReceiptDetailSerializer,
    ReceiptDraftSerializer,
)
from apps.front_office.receipts.services.receipt_service import get_receipt_or_404


def _true(value):
    return value in ("true", "1", "True")


def _paginate(query, request):
    page = max(1, int(request.query_params.get("page", 1)))
    page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
    total = query.count()
    start = (page - 1) * page_size
    rows = query[start : start + page_size]
    return {
        "results": ReceiptBaseSerializer(rows, many=True).data,
        "count": total,
        "page": page,
        "page_size": page_size,
        "next": page * page_size < total,
        "previous": page > 1,
    }


class MustViewReceiptsPermission(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return has_receipt_permission(request.user, "view")


class MustActionPermission(IsAuthenticated):
    """Gate a receipt action on its matching permission code."""

    def __init__(self, action="view"):
        self.action = action
        super().__init__()

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return has_receipt_permission(request.user, self.action)


class ReceiptListView(APIView):
    """GET list + POST create draft at /front-office/receipts/."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [MustActionPermission(action="create")]
        return [MustViewReceiptsPermission()]

    def get(self, request):
        params = request.query_params
        queryset = Receipt.objects.select_related("branch", "partner", "bank_account").all()

        status = params.get("status")
        if status:
            queryset = queryset.filter(status__iexact=status)
        branch = params.get("branch")
        if branch:
            queryset = queryset.filter(branch_id=branch)
        partner = params.get("partner")
        if partner:
            queryset = queryset.filter(partner_id=partner)
        source_module = params.get("source_module")
        if source_module:
            queryset = queryset.filter(source_module__iexact=source_module)
        currency = params.get("currency")
        if currency:
            queryset = queryset.filter(currency__iexact=currency)
        payment_mode = params.get("payment_mode")
        if payment_mode:
            queryset = queryset.filter(payment_mode__iexact=payment_mode)
        date_from = params.get("receipt_date_from")
        if date_from:
            queryset = queryset.filter(receipt_date__gte=date_from)
        date_to = params.get("receipt_date_to")
        if date_to:
            queryset = queryset.filter(receipt_date__lte=date_to)
        if _true(params.get("unallocated_only")):
            queryset = queryset.filter(unallocated_amount__gt=0)
        if _true(params.get("allocated_only")):
            queryset = queryset.filter(allocated_amount__gt=0)

        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(receipt_number__icontains=search)
                | Q(payer_name__icontains=search)
                | Q(partner_name_snapshot__icontains=search)
                | Q(payment_reference__icontains=search)
                | Q(source_reference_id__icontains=search)
            )

        ordering = params.get("ordering", "-receipt_date")
        order_map = {
            "receipt_number": "receipt_number",
            "receipt_date": "receipt_date",
            "status": "status",
            "receipt_amount": "receipt_amount",
            "allocated_amount": "allocated_amount",
            "unallocated_amount": "unallocated_amount",
            "created_at": "created_at",
        }
        if ordering.startswith("-"):
            key = order_map.get(ordering[1:])
            if key:
                ordering = f"-{key}"
        else:
            key = order_map.get(ordering)
            if key:
                ordering = key
        queryset = queryset.order_by(ordering, "-created_at")

        return Response({"data": _paginate(queryset, request)})

    def post(self, request):
        serializer = ReceiptDraftSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        receipt = serializer.save()
        return Response({"data": ReceiptDetailSerializer(receipt).data}, status=201)


class ReceiptDetailView(APIView):
    """GET retrieve + PATCH update draft at /front-office/receipts/<uuid>/."""

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [MustActionPermission(action="create")]
        return [MustViewReceiptsPermission()]

    def get(self, request, receipt_id):
        receipt = get_receipt_or_404(receipt_id)
        return Response({"data": ReceiptDetailSerializer(receipt).data})

    def patch(self, request, receipt_id):
        receipt = get_receipt_or_404(receipt_id)
        serializer = ReceiptDraftSerializer(receipt, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        receipt = serializer.save()
        return Response({"data": ReceiptDetailSerializer(receipt).data})


class ReceiptOptionsView(APIView):
    permission_classes = [MustViewReceiptsPermission]

    def get(self, request):
        from apps.front_office.receipts.services.parameter_resolver import (
            configured_payment_modes,
            configured_source_modules,
            configured_statuses,
            default_currency,
            payment_mode_label,
        )

        return Response(
            {
                "data": {
                    "statuses": configured_statuses(),
                    "source_modules": configured_source_modules(),
                    "payment_modes": [
                        {"code": code, "name": payment_mode_label(code)} for code in configured_payment_modes()
                    ],
                    "currencies": [default_currency(), "TZS", "USD", "KES"],
                }
            }
        )
