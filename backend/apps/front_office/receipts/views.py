from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.front_office.receipts.models import Receipt, ReceiptAllocation
from apps.front_office.receipts.permissions import has_receipt_permission
from apps.front_office.receipts.serializers import (
    ReceiptAllocationRequestSerializer,
    ReceiptAllocationSerializer,
    ReceiptBaseSerializer,
    ReceiptDetailSerializer,
    ReceiptDraftSerializer,
    ReceiptReasonSerializer,
    ReceiptReversalSerializer,
)
from apps.front_office.receipts.services.receipt_service import get_receipt_or_404, post_receipt


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
        # Idempotent create: the X-Idempotency-Key header maps to the receipt's
        # idempotency_key; a duplicate submission returns the same receipt.
        data = request.data
        header_key = (request.headers.get("X-Idempotency-Key") or "").strip()
        if header_key and not (data or {}).get("idempotency_key"):
            data = {**request.data, "idempotency_key": header_key}
        serializer = ReceiptDraftSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        receipt = serializer.save()
        created = getattr(serializer, "_created", True)
        return Response(
            {"data": ReceiptDetailSerializer(receipt).data},
            status=201 if created else 200,
        )


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


class ReceiptPostView(APIView):
    """POST /front-office/receipts/<uuid>/post/ — post a draft receipt."""

    def get_permissions(self):
        return [MustActionPermission(action="post")]

    def post(self, request, receipt_id):
        receipt = get_receipt_or_404(receipt_id)
        reason = ((request.data or {}).get("reason") or "").strip()
        receipt = post_receipt(receipt, actor=request.user, reason=reason, source_channel="API")
        return Response({"data": ReceiptDetailSerializer(receipt).data})


class ReceiptAllocationOptionsView(APIView):
    """GET /front-office/receipts/<uuid>/allocation-options/ — open commitments."""

    def get_permissions(self):
        return [MustViewReceiptsPermission()]

    def get(self, request, receipt_id):
        from apps.front_office.receipts.services.allocation_service import allocation_options

        receipt = get_receipt_or_404(receipt_id)
        options = allocation_options(receipt)
        return Response(
            {
                "data": {
                    "receipt": ReceiptBaseSerializer(receipt).data,
                    "commitments": options,
                }
            }
        )


class ReceiptAllocateView(APIView):
    """POST /front-office/receipts/<uuid>/allocate/ — manual allocation."""

    def get_permissions(self):
        return [MustActionPermission(action="allocate")]

    def post(self, request, receipt_id):
        from apps.front_office.receipts.services.allocation_service import allocate

        receipt = get_receipt_or_404(receipt_id)
        serializer = ReceiptAllocationRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        allocation, receipt, created, warning = allocate(
            receipt,
            target_type=data["target_type"],
            target_id=data["target_id"],
            amount=data["amount"],
            narration=data.get("narration", ""),
            exchange_rate=data.get("exchange_rate"),
            exchange_rate_source=data.get("exchange_rate_source") or None,
            actor=request.user,
            source_channel="API",
        )
        response_data = {"data": ReceiptDetailSerializer(receipt).data}
        if warning:
            response_data["warning"] = warning
        return Response(
            response_data,
            status=201 if created else 200,
        )


class ReceiptAutoAllocateView(APIView):
    """POST /front-office/receipts/<uuid>/auto-allocate/ — oldest-due-first."""

    def get_permissions(self):
        return [MustActionPermission(action="allocate")]

    def post(self, request, receipt_id):
        from apps.front_office.receipts.services.allocation_service import auto_allocate

        receipt = get_receipt_or_404(receipt_id)
        result = auto_allocate(receipt, actor=request.user, source_channel="API")
        return Response(
            {
                "data": {
                    "receipt": ReceiptDetailSerializer(receipt).data,
                    "allocations": result["allocations"],
                    "total_allocated": result["total_allocated"],
                    "remaining_unallocated": result["remaining_unallocated"],
                    "receipt_status": result["receipt_status"],
                    "commitments_count": result["commitments_count"],
                    "exhausted": result["exhausted"],
                }
            }
        )


class ExchangeRateView(APIView):
    """GET /front-office/exchange-rate/?from=&to=&date= — configured rate lookup."""

    permission_classes = [MustViewReceiptsPermission]

    def get(self, request):
        from apps.front_office.receipts.errors import currency_mismatch
        from apps.front_office.receipts.services.exchange_rate_service import lookup_payload

        from_currency = (request.query_params.get("from") or "").strip().upper()
        to_currency = (request.query_params.get("to") or "").strip().upper()
        date_param = (request.query_params.get("date") or "").strip()

        def _valid(code):
            return len(code) == 3 and code.isalpha()

        if not _valid(from_currency) or not _valid(to_currency):
            raise currency_mismatch(
                message="A valid from and to currency (three-letter codes) is required.",
                field_errors={
                    "from": ["A three-letter from currency is required."]
                    if not _valid(from_currency)
                    else [],
                    "to": ["A three-letter to currency is required."]
                    if not _valid(to_currency)
                    else [],
                },
            )
        effective_date = None
        if date_param:
            try:
                from datetime import date

                effective_date = date.fromisoformat(date_param)
            except ValueError:
                raise currency_mismatch(
                    message="The date must use the ISO format YYYY-MM-DD.",
                    field_errors={"date": ["Enter a date in YYYY-MM-DD format."]},
                )

        payload = lookup_payload(from_currency, to_currency, effective_date)
        if payload is None:
            raise currency_mismatch(
                message=f"No active exchange rate is configured from {from_currency} to {to_currency}.",
                resolution_steps=[
                    "Configure an ExchangeRate for the pair in Front Office parameters.",
                    "Or supply the exchange_rate explicitly on the allocation request.",
                ],
                field_errors={"rate": ["No active rate is on file for the pair and date."]},
            )
        return Response({"data": payload})


class ReceiptReverseView(APIView):
    """POST /front-office/receipts/<uuid>/reverse/ — full receipt reversal."""

    def get_permissions(self):
        return [MustActionPermission(action="reverse")]

    def post(self, request, receipt_id):
        from apps.front_office.receipts.services.reversal_service import reverse_receipt

        receipt = get_receipt_or_404(receipt_id)
        serializer = ReceiptReasonSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        receipt, reversal_record = reverse_receipt(
            receipt,
            reason=serializer.validated_data["reason"],
            actor=request.user,
            source_channel="API",
        )
        return Response(
            {
                "data": ReceiptDetailSerializer(receipt).data,
                "reversal": ReceiptReversalSerializer(reversal_record).data,
            }
        )


class ReceiptAllocationReverseView(APIView):
    """POST /front-office/receipts/<uuid>/allocations/<uuid>/reverse/ — one allocation."""

    def get_permissions(self):
        return [MustActionPermission(action="reverse")]

    def post(self, request, receipt_id, allocation_id):
        from apps.front_office.receipts.errors import allocation_invalid
        from apps.front_office.receipts.services.reversal_service import reverse_allocation

        receipt = get_receipt_or_404(receipt_id)
        allocation = ReceiptAllocation.objects.filter(pk=allocation_id).first()
        if allocation is None or allocation.receipt_id != receipt.pk:
            raise allocation_invalid(
                message="The allocation was not found for this receipt.",
                field_errors={"allocation_id": ["Allocation not found for this receipt."]},
            )
        serializer = ReceiptReasonSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        receipt, reversal_row = reverse_allocation(
            receipt,
            allocation,
            reason=serializer.validated_data["reason"],
            actor=request.user,
            source_channel="API",
        )
        return Response(
            {
                "data": ReceiptDetailSerializer(receipt).data,
                "allocation": ReceiptAllocationSerializer(reversal_row).data,
            }
        )


class ReceiptCancelView(APIView):
    """POST /front-office/receipts/<uuid>/cancel/ — cancel a draft receipt."""

    def get_permissions(self):
        return [MustActionPermission(action="cancel")]

    def post(self, request, receipt_id):
        from apps.front_office.receipts.services.reversal_service import cancel_draft

        receipt = get_receipt_or_404(receipt_id)
        serializer = ReceiptReasonSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        receipt = cancel_draft(
            receipt,
            reason=serializer.validated_data["reason"],
            actor=request.user,
            source_channel="API",
        )
        return Response({"data": ReceiptDetailSerializer(receipt).data})


class ReceiptOptionsView(APIView):
    permission_classes = [MustViewReceiptsPermission]

    def get(self, request):
        from apps.front_office.receipts.config_models import CompanyBankAccount, ReceiptPaymentModeRule
        from apps.front_office.receipts.services.parameter_resolver import (
            configured_currencies,
            configured_payment_modes,
            configured_source_modules,
            configured_statuses,
            option,
            payment_mode_label,
        )
        from apps.partner_onboarding.models import Branch

        branches = [
            option(str(branch.pk), branch.name, code=branch.code)
            for branch in Branch.objects.filter(is_active=True).order_by("name")
        ]

        company_accounts = list(CompanyBankAccount.objects.filter(is_active=True).order_by("code"))
        currency_codes = list(dict.fromkeys(configured_currencies()))
        if company_accounts:
            currency_codes = list(dict.fromkeys([acc.currency for acc in company_accounts] + currency_codes))
        currencies = [option(code, code) for code in currency_codes]

        rules = list(ReceiptPaymentModeRule.objects.filter(is_active=True).order_by("payment_mode"))
        if rules:
            payment_modes = [
                option(
                    rule.payment_mode,
                    payment_mode_label(rule.payment_mode),
                    requires_reference=rule.requires_reference,
                    requires_bank_account=rule.requires_bank_account,
                    allows_cash=rule.allows_cash,
                    allows_card=rule.allows_card,
                    allows_mobile_money=rule.allows_mobile_money,
                    allows_bank_transfer=rule.allows_bank_transfer,
                    allows_cheque=rule.allows_cheque,
                    min_amount=str(rule.min_amount) if rule.min_amount is not None else None,
                    max_amount=str(rule.max_amount) if rule.max_amount is not None else None,
                )
                for rule in rules
            ]
        else:
            payment_modes = [option(code, payment_mode_label(code)) for code in configured_payment_modes()]

        company_bank_accounts = [
            option(
                str(account.pk),
                f"{account.bank_name} - {account.account_name}",
                code=account.code,
                currency=account.currency,
                account_number=account.masked_account_number,
                is_default=account.is_default,
            )
            for account in company_accounts
        ]

        statuses = [option(code, code.replace("_", " ").title()) for code in configured_statuses()]
        source_modules = [option(code, code.replace("_", " ").title()) for code in configured_source_modules()]

        return Response(
            {
                "data": {
                    "branches": branches,
                    "currencies": currencies,
                    "payment_modes": payment_modes,
                    "company_bank_accounts": company_bank_accounts,
                    "receipt_statuses": statuses,
                    "statuses": statuses,
                    "source_modules": source_modules,
                }
            }
        )
