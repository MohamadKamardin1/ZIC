import csv
from decimal import Decimal

from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.front_office.receipts.errors import (
    allocation_invalid,
    import_batch_not_found,
    import_row_invalid,
    not_found,
)
from apps.front_office.receipts.models import (
    Receipt,
    ReceiptAllocation,
    ReceiptDocument,
    ReceiptImportBatch,
    ReceiptImportBatchStatus,
    ReceiptImportRowStatus,
    ReceiptReversal,
)
from apps.front_office.receipts.permissions import has_receipt_permission
from apps.front_office.receipts.serializers import (
    PartnerPortalReceiptDetailSerializer,
    PartnerPortalReceiptListSerializer,
    ReceiptAllocationRequestSerializer,
    ReceiptAllocationSerializer,
    ReceiptBaseSerializer,
    ReceiptDetailSerializer,
    ReceiptDocumentSerializer,
    ReceiptDraftSerializer,
    ReceiptImportBatchSerializer,
    ReceiptReasonSerializer,
    ReceiptReversalSerializer,
    _first_premium_proposal_number,
    _is_first_premium_commitment,
)
from apps.front_office.receipts.services.import_service import (
    commit_batch,
    dry_run,
    import_csv_template,
    import_row_payload,
)
from apps.front_office.receipts.services.receipt_service import get_receipt_or_404, post_receipt
from apps.front_office.receipts.services.work_queue import (
    LIST_COLUMNS,
    apply_ordering,
    filter_receipts,
    receipt_kpis,
)


def _paginate(query, request):
    page = max(1, int(request.query_params.get("page", 1)))
    page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
    total = query.count()
    start = (page - 1) * page_size
    rows = query[start : start + page_size]
    return {
        "results": ReceiptBaseSerializer(rows, many=True, context={"request": request}).data,
        "count": total,
        "page": page,
        "page_size": page_size,
        "next": page * page_size < total,
        "previous": page > 1,
    }


def _csv_cell(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return " | ".join(str(item) for item in value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


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


class ReceiptAPIView(APIView):
    """Base for the receipts domain views.

    The global config renders DRF responses through the camelCase JSON renderer,
    but the merged web client (receipts-api.ts and its MSW mocks) reads snake_case
    fields. Pin the receipts views to the plain renderer so the wire format
    matches the frontend contract. The CamelCaseJSONParser stays active — it
    tolerates already-snake_case request bodies.
    """

    renderer_classes = [JSONRenderer]


class ReceiptListView(ReceiptAPIView):
    """GET list + POST create draft at /front-office/receipts/."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [MustActionPermission(action="create")]
        return [MustViewReceiptsPermission()]

    def get(self, request):
        params = request.query_params
        queryset = Receipt.objects.select_related(
            "branch", "partner", "bank_account", "created_by", "posted_by"
        ).all()
        queryset = filter_receipts(queryset, params)
        queryset = apply_ordering(queryset, params)
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
            {"data": ReceiptDetailSerializer(receipt, context={"request": request}).data},
            status=201 if created else 200,
        )


class ReceiptKpisView(ReceiptAPIView):
    """GET /front-office/receipts/kpis/ — work-queue aggregates over the filters."""

    permission_classes = [MustViewReceiptsPermission]

    def get(self, request):
        params = request.query_params
        queryset = Receipt.objects.all()
        queryset = filter_receipts(queryset, params)
        kpis = receipt_kpis(queryset)
        kpis["period"] = {
            "receipt_date_from": params.get("receipt_date_from") or params.get("date_from"),
            "receipt_date_to": params.get("receipt_date_to") or params.get("date_to"),
        }
        return Response({"data": kpis})


class ReceiptExportView(ReceiptAPIView):
    """GET /front-office/receipts/export/ — CSV export respecting the same filters."""

    permission_classes = [MustViewReceiptsPermission]

    def get(self, request):
        queryset = Receipt.objects.select_related(
            "branch", "partner", "bank_account", "created_by", "posted_by"
        ).all()
        queryset = filter_receipts(queryset, request.query_params)
        queryset = apply_ordering(queryset, request.query_params)
        rows = ReceiptBaseSerializer(queryset, many=True, context={"request": request}).data

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="receipts_{timezone.localdate().isoformat()}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(LIST_COLUMNS)
        for row in rows:
            writer.writerow([_csv_cell(row.get(column)) for column in LIST_COLUMNS])
        return response


class ReceiptDetailView(ReceiptAPIView):
    """GET retrieve + PATCH update draft at /front-office/receipts/<uuid>/."""

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [MustActionPermission(action="create")]
        return [MustViewReceiptsPermission()]

    def get(self, request, receipt_id):
        receipt = get_receipt_or_404(receipt_id)
        return Response({"data": ReceiptDetailSerializer(receipt, context={"request": request}).data})

    def patch(self, request, receipt_id):
        receipt = get_receipt_or_404(receipt_id)
        serializer = ReceiptDraftSerializer(receipt, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        receipt = serializer.save()
        return Response({"data": ReceiptDetailSerializer(receipt, context={"request": request}).data})


class ReceiptPostView(ReceiptAPIView):
    """POST /front-office/receipts/<uuid>/post/ — post a draft receipt."""

    def get_permissions(self):
        return [MustActionPermission(action="post")]

    def post(self, request, receipt_id):
        receipt = get_receipt_or_404(receipt_id)
        reason = ((request.data or {}).get("reason") or "").strip()
        receipt = post_receipt(receipt, actor=request.user, reason=reason, source_channel="API")
        return Response({"data": ReceiptDetailSerializer(receipt, context={"request": request}).data})


class ReceiptAllocationsView(ReceiptAPIView):
    """GET /front-office/receipts/<uuid>/allocations/ — paginated allocation rows."""

    permission_classes = [MustViewReceiptsPermission]

    def get(self, request, receipt_id):
        receipt = get_receipt_or_404(receipt_id)
        queryset = ReceiptAllocation.objects.filter(receipt=receipt).order_by("-allocated_at", "-created_at")
        page = max(1, int(request.query_params.get("page", 1)))
        page_size = min(100, max(1, int(request.query_params.get("page_size", 25))))
        total = queryset.count()
        start = (page - 1) * page_size
        rows = queryset[start : start + page_size]
        return Response(
            {
                "data": {
                    "results": ReceiptAllocationSerializer(
                        rows, many=True, context={"request": request}
                    ).data,
                    "count": total,
                    "page": page,
                    "page_size": page_size,
                    "next": page * page_size < total,
                    "previous": page > 1,
                }
            }
        )


class ReceiptReversalsView(ReceiptAPIView):
    """GET /front-office/receipts/<uuid>/reversals/ — paginated reversal history."""

    permission_classes = [MustViewReceiptsPermission]

    def get(self, request, receipt_id):
        receipt = get_receipt_or_404(receipt_id)
        queryset = ReceiptReversal.objects.filter(receipt=receipt).order_by("-reversed_at", "-created_at")
        page = max(1, int(request.query_params.get("page", 1)))
        page_size = min(100, max(1, int(request.query_params.get("page_size", 25))))
        total = queryset.count()
        start = (page - 1) * page_size
        rows = queryset[start : start + page_size]
        return Response(
            {
                "data": {
                    "results": ReceiptReversalSerializer(rows, many=True, context={"request": request}).data,
                    "count": total,
                    "page": page,
                    "page_size": page_size,
                    "next": page * page_size < total,
                    "previous": page > 1,
                }
            }
        )


class ReceiptAuditTimelineView(ReceiptAPIView):
    """GET /front-office/receipts/<uuid>/audit-timeline/ — paginated lifecycle events."""

    permission_classes = [MustViewReceiptsPermission]

    def get(self, request, receipt_id):
        from apps.front_office.receipts.services.work_queue import audit_timeline

        receipt = get_receipt_or_404(receipt_id)
        events = audit_timeline(receipt)
        page = max(1, int(request.query_params.get("page", 1)))
        page_size = min(100, max(1, int(request.query_params.get("page_size", 25))))
        total = len(events)
        start = (page - 1) * page_size
        return Response(
            {
                "data": {
                    "results": events[start : start + page_size],
                    "count": total,
                    "page": page,
                    "page_size": page_size,
                    "next": page * page_size < total,
                    "previous": page > 1,
                }
            }
        )


class ReceiptBankAccountView(ReceiptAPIView):
    """GET /front-office/receipts/<uuid>/bank-account/ — reveal the linked account."""

    permission_classes = [MustViewReceiptsPermission]

    def get(self, request, receipt_id):
        receipt = get_receipt_or_404(receipt_id)
        display = receipt.bank_account_snapshot or (str(receipt.bank_account) if receipt.bank_account_id else None)
        return Response({"data": {"bank_account_display": display}})


class ReceiptAllocationOptionsView(ReceiptAPIView):
    """GET /front-office/receipts/<uuid>/allocation-options/ — open commitments.

    Returns a paginated option list (matching the web allocation modal contract);
    ``?search=`` narrows by commitment number, proposal, or policy reference.
    """

    def get_permissions(self):
        return [MustViewReceiptsPermission()]

    def get(self, request, receipt_id):
        from apps.front_office.receipts.services.allocation_service import allocation_options

        receipt = get_receipt_or_404(receipt_id)
        options = allocation_options(receipt)
        search = (request.query_params.get("search") or "").strip().lower()
        if search:
            options = [
                option
                for option in options
                if search
                in " ".join(
                    str(option.get(key) or "")
                    for key in ("commitment_number", "proposal_number", "policy_number", "source_display")
                ).lower()
            ]
        page = max(1, int(request.query_params.get("page", 1)))
        page_size = min(100, max(1, int(request.query_params.get("page_size", 25))))
        total = len(options)
        start = (page - 1) * page_size
        return Response(
            {
                "data": {
                    "results": options[start : start + page_size],
                    "count": total,
                    "page": page,
                    "page_size": page_size,
                    "next": page * page_size < total,
                    "previous": page > 1,
                    "commitments": options,
                }
            }
        )


def _allocation_item(allocation, receipt_currency):
    """Allocation row in the web ``ReceiptAllocationResult.allocations`` shape."""
    commitment = allocation.commitment
    return {
        "id": str(allocation.pk),
        "target_display": allocation.target_display or allocation.target_id or "",
        "commitment": str(commitment.pk) if commitment else None,
        "commitment_number": commitment.commitment_number if commitment else (allocation.target_id or None),
        "amount": str(allocation.amount),
        "currency": allocation.currency,
        "exchange_rate": (
            str(allocation.exchange_rate)
            if allocation.currency != receipt_currency and allocation.exchange_rate is not None
            else None
        ),
        "status": allocation.allocation_status,
        "balance_before": str(allocation.amount),
        "balance_after": str(commitment.balance) if commitment else None,
        "is_first_premium": _is_first_premium_commitment(commitment.pk) if commitment else False,
        "proposal_number": _first_premium_proposal_number(commitment.pk) if commitment else None,
        "allocation_amount_in_receipt_currency": str(allocation.amount),
        "allocation_amount_in_target_currency": str(allocation.converted_amount),
        "exchange_rate_used": str(allocation.exchange_rate_used),
        "converted_amount": str(allocation.converted_amount),
        "converted_currency": allocation.converted_currency,
    }


class ReceiptAllocateView(ReceiptAPIView):
    """POST /front-office/receipts/<uuid>/allocate/ — manual allocation.

    Accepts the web contract ``{allocations: [{commitment, amount, exchange_rate}]}``
    and the legacy single-allocation contract ``{target_type, target_id, amount}``.
    The response is a superset: the receipt detail at the top level (legacy) plus
    the ``receipt``/``allocations``/``first_premium_*`` envelope (web).
    """

    def get_permissions(self):
        return [MustActionPermission(action="allocate")]

    def post(self, request, receipt_id):
        from apps.front_office.receipts.services.allocation_service import (
            allocate,
            allocate_to_commitment,
        )

        receipt = get_receipt_or_404(receipt_id)
        payload = request.data or {}
        allocations_payload = payload.get("allocations")
        items = []
        created_any = False
        warning = None

        if isinstance(allocations_payload, list):
            from apps.ol_commitments.models import OLCommitment

            for row in allocations_payload:
                commitment_id = str(row.get("commitment") or "").strip()
                if not commitment_id:
                    raise allocation_invalid(
                        message="Each allocation row needs a commitment.",
                        field_errors={"commitment": ["Select a commitment for each allocation."]},
                    )
                commitment = OLCommitment.objects.filter(pk=commitment_id).first()
                if commitment is None:
                    raise allocation_invalid(
                        message="The allocation target commitment was not found.",
                        field_errors={"commitment": ["Commitment not found or not open for allocation."]},
                    )
                amount = row.get("amount")
                allocation, receipt, created, row_warning = allocate_to_commitment(
                    receipt,
                    commitment,
                    amount=amount,
                    exchange_rate=row.get("exchange_rate"),
                    exchange_rate_source="API",
                    actor=request.user,
                    source_channel="API",
                )
                created_any = created_any or created
                warning = warning or row_warning
                items.append(_allocation_item(allocation, receipt.currency))
        else:
            serializer = ReceiptAllocationRequestSerializer(data=payload)
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
            created_any = created
            items.append(_allocation_item(allocation, receipt.currency))

        first_premium = next((item for item in items if item["is_first_premium"]), None)
        response_data = {
            "data": ReceiptDetailSerializer(receipt, context={"request": request}).data,
        }
        response_data["data"].update(
            {
                "receipt": dict(response_data["data"]),
                "allocations": items,
                "total_allocated": str(receipt.allocated_amount),
                "remaining_unallocated": str(receipt.unallocated_amount),
                "remaining_unallocated_amount": str(receipt.unallocated_amount),
                "receipt_status": receipt.status,
                "commitments_count": len(items),
                "exhausted": Decimal(receipt.unallocated_amount) <= 0,
                "first_premium_completed": first_premium is not None,
                "first_premium_proposal_number": first_premium["proposal_number"] if first_premium else None,
            }
        )
        if warning:
            response_data["warning"] = warning
        return Response(
            response_data,
            status=201 if created_any else 200,
        )


class ReceiptAutoAllocateView(ReceiptAPIView):
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
                    "receipt": ReceiptDetailSerializer(receipt, context={"request": request}).data,
                    "allocations": result["allocations"],
                    "total_allocated": result["total_allocated"],
                    "remaining_unallocated": result["remaining_unallocated"],
                    "remaining_unallocated_amount": result.get("remaining_unallocated_amount"),
                    "receipt_status": result["receipt_status"],
                    "commitments_count": result["commitments_count"],
                    "exhausted": result["exhausted"],
                    "first_premium_completed": result.get("first_premium_completed", False),
                    "first_premium_proposal_number": result.get("first_premium_proposal_number"),
                }
            }
        )


class ExchangeRateView(ReceiptAPIView):
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
                ) from None

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


class ReceiptReverseView(ReceiptAPIView):
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
                "data": ReceiptDetailSerializer(receipt, context={"request": request}).data,
                "reversal": ReceiptReversalSerializer(reversal_record).data,
            }
        )


class ReceiptAllocationReverseView(ReceiptAPIView):
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
                "data": ReceiptDetailSerializer(receipt, context={"request": request}).data,
                "allocation": ReceiptAllocationSerializer(reversal_row).data,
            }
        )


class ReceiptCancelView(ReceiptAPIView):
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
        return Response({"data": ReceiptDetailSerializer(receipt, context={"request": request}).data})


class ReceiptOptionsView(ReceiptAPIView):
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


class ReceiptOptionsResourceView(ReceiptAPIView):
    """GET /front-office/options/<resource>/ plus quick-create helpers.

    Serves the web SmartSelect contract: a paginated ``{results, count, next,
    previous, page, page_size}`` list of ``{value, label, meta}`` options per
    resource, with optional ``?q=`` filtering. Branches and payers additionally
    expose ``quick-create-schema/`` (GET) and ``quick-create/`` (POST).
    """

    permission_classes = [MustViewReceiptsPermission]

    def get(self, request, resource):
        if request.path.rstrip("/").endswith("quick-create-schema"):
            return Response({"data": self._quick_create_schema(resource)}, status=200)
        options = self._options_for(resource)
        q = (request.query_params.get("q") or "").strip().lower()
        if q:
            options = [
                opt
                for opt in options
                if q in f"{opt.get('value') or ''} {opt.get('label') or ''} {opt.get('meta') or ''}".lower()
            ]
        page = max(1, int(request.query_params.get("page", 1)))
        page_size = min(100, max(1, int(request.query_params.get("page_size", 25))))
        total = len(options)
        start = (page - 1) * page_size
        return Response(
            {
                "data": {
                    "results": options[start : start + page_size],
                    "count": total,
                    "page": page,
                    "page_size": page_size,
                    "next": page * page_size < total,
                    "previous": page > 1,
                }
            }
        )

    def post(self, request, resource):
        if resource == "branches":
            return self._quick_create_branch(request)
        if resource == "payers":
            return self._quick_create_payer(request)
        raise not_found()

    def _options_for(self, resource):
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

        if resource == "branches":
            return [
                option(str(branch.pk), branch.name, code=branch.code)
                for branch in Branch.objects.filter(is_active=True).order_by("name")
            ]
        if resource == "payers":
            from apps.partners.models import Partner

            return [
                option(
                    str(partner.pk),
                    getattr(partner, "display_name", None) or partner.legal_name or partner.partner_number,
                    partner_number=partner.partner_number,
                )
                for partner in Partner.objects.filter(is_active=True).order_by("legal_name")[:500]
            ]
        if resource == "proposals":
            from apps.ol_proposals.models import OLProposal

            proposals = (
                OLProposal.objects.filter(
                    first_premium_commitment__isnull=False
                )
                .exclude(status__in=["CONVERTED", "CANCELLED", "EXPIRED"])
                .order_by("proposal_number")[:500]
            )
            return [
                option(
                    str(proposal.pk),
                    proposal.proposal_number,
                    status_hint=proposal.status or "AWAITING_FIRST_PREMIUM",
                )
                for proposal in proposals
            ]
        if resource == "source-modules":
            return [option(code, code.replace("_", " ").title()) for code in configured_source_modules()]
        if resource == "currencies":
            return [option(code, code) for code in dict.fromkeys(configured_currencies())]
        if resource == "payment-modes":
            rules = list(ReceiptPaymentModeRule.objects.filter(is_active=True).order_by("payment_mode"))
            if rules:
                return [
                    option(
                        rule.payment_mode,
                        payment_mode_label(rule.payment_mode),
                        requires_reference=rule.requires_reference,
                        requires_bank_account=rule.requires_bank_account,
                    )
                    for rule in rules
                ]
            return [option(code, payment_mode_label(code)) for code in configured_payment_modes()]
        if resource == "bank-accounts":
            return [
                option(
                    str(account.pk),
                    f"{account.bank_name} - {account.account_name}",
                    code=account.code,
                    currency=account.currency,
                    account_number=account.masked_account_number,
                    is_default=account.is_default,
                )
                for account in CompanyBankAccount.objects.filter(is_active=True).order_by("code")
            ]
        if resource == "statuses":
            return [option(code, code.replace("_", " ").title()) for code in configured_statuses()]
        raise not_found()

    def _quick_create_schema(self, resource):
        if resource == "branches":
            return {
                "entity": "branches",
                "permission": "front_office.receipts.create",
                "fields": [
                    {"name": "code", "type": "text", "required": True},
                    {"name": "name", "type": "text", "required": True},
                ],
            }
        if resource == "payers":
            return {
                "entity": "payers",
                "permission": "partners.create",
                "fields": [
                    {"name": "legal_name", "type": "text", "required": True},
                    {"name": "national_id", "type": "text", "required": False},
                    {"name": "phone", "type": "text", "required": False},
                ],
            }
        raise not_found()

    def _quick_create_branch(self, request):
        if not has_receipt_permission(request.user, "create"):
            raise not_found()
        from apps.front_office.receipts.errors import import_row_invalid as invalid_option
        from apps.partner_onboarding.models import Branch

        code = ((request.data or {}).get("code") or "").strip()
        name = ((request.data or {}).get("name") or "").strip()
        if not code or not name:
            raise invalid_option(
                message="Branch code and name are required.",
                field_errors={
                    "code": [] if code else ["Branch code is required."],
                    "name": [] if name else ["Branch name is required."],
                },
            )
        branch = Branch.objects.filter(code__iexact=code).first()
        if branch is None:
            branch = Branch.objects.create(code=code.upper(), name=name, is_active=True)
        return Response({"data": {"option": {"value": str(branch.pk), "label": branch.name, "meta": {"code": branch.code}}}}, status=201)

    def _quick_create_payer(self, request):
        if not has_receipt_permission(request.user, "create"):
            raise not_found()
        from apps.front_office.receipts.errors import import_row_invalid as invalid_option
        from apps.partners.models import Partner

        legal_name = ((request.data or {}).get("legal_name") or "").strip()
        if not legal_name:
            raise invalid_option(
                message="A payer legal name is required.",
                field_errors={"legal_name": ["A payer legal name is required."]},
            )
        partner = Partner.objects.create(legal_name=legal_name, is_active=True)
        return Response(
            {
                "data": {
                    "option": {
                        "value": str(partner.pk),
                        "label": partner.legal_name or partner.partner_number,
                        "meta": {"partner_number": partner.partner_number},
                    }
                }
            },
            status=201,
        )


class ReceiptPrintView(ReceiptAPIView):
    """POST /front-office/receipts/<uuid>/print/ — generate a receipt printout.

    Print rules (Prompt 8): DRAFT prints a preview only; posted states print an
    official receipt; REVERSED/CANCELLED print with the matching watermark. The
    endpoint is gated on the ``front_office.receipts.print`` permission and the
    response carries signed download tickets (never the public media URL).
    """

    def get_permissions(self):
        return [MustActionPermission(action="print")]

    def post(self, request, receipt_id):
        from apps.front_office.receipts.services.print_service import ReceiptPrintService

        receipt = get_receipt_or_404(receipt_id)
        template_code = (request.data or {}).get("template_code")
        preview = bool((request.data or {}).get("preview"))
        document = ReceiptPrintService.generate(
            receipt=receipt,
            actor=request.user,
            request=request,
            template_code=template_code,
            preview=preview,
        )
        document_data = ReceiptDocumentSerializer(document, context={"request": request}).data
        data = {
            "receipt": ReceiptDetailSerializer(receipt, context={"request": request}).data,
            "document": document_data,
        }
        # Legacy compatibility: the document fields used to sit at the top of
        # the payload. Flatten them (plus the metadata watermark) as a superset.
        data.update(document_data)
        data.setdefault("watermark", (document.metadata or {}).get("watermark", ""))
        return Response({"data": data}, status=201)


class ReceiptDocumentsView(ReceiptAPIView):
    """GET /front-office/receipts/<uuid>/documents/ — document register for a receipt."""

    permission_classes = [MustViewReceiptsPermission]

    def get(self, request, receipt_id):
        receipt = get_receipt_or_404(receipt_id)
        documents = ReceiptDocument.objects.filter(receipt=receipt).order_by("-uploaded_at", "-created_at")
        return Response(
            {
                "data": {
                    "receipt_number": receipt.receipt_number,
                    "results": ReceiptDocumentSerializer(
                        documents, many=True, context={"request": request}
                    ).data,
                }
            }
        )


class ReceiptDocumentDownloadView(ReceiptAPIView):
    """GET /front-office/receipts/documents/<uuid>/download/?ticket=... — signed download.

    The ticket is issued by the print pipeline (bound to the requesting user,
    document, and purpose) and validated here; the stream is audited as a
    DOWNLOAD on the source receipt.
    """

    def get_permissions(self):
        return [MustActionPermission(action="print")]

    def get(self, request, document_id):
        from apps.front_office.receipts.errors import document_not_found, file_missing
        from apps.front_office.receipts.services.print_ticket import validate_download_ticket

        validate_download_ticket(
            (request.query_params.get("ticket") or ""),
            document_id=document_id,
            user_id=request.user.pk,
        )
        document = ReceiptDocument.objects.filter(pk=document_id).first()
        if document is None:
            raise document_not_found()
        if not document.file_reference or not default_storage.exists(document.file_reference):
            raise file_missing()
        content = default_storage.open(document.file_reference, "rb").read()

        from apps.governance.services.audit_service import AuditService

        AuditService.log_action(
            action="DOWNLOAD",
            instance=document.receipt,
            actor=request.user,
            request=request,
            after_state={
                "document_id": str(document.pk),
                "document_type": document.document_type,
                "template_code": (document.metadata or {}).get("template_code"),
                "template_version": document.template_version,
                "watermark": (document.metadata or {}).get("watermark", ""),
            },
            reason="Receipt document downloaded.",
            changed_fields=[],
        )
        response = HttpResponse(content, content_type=document.mime_type or "application/pdf")
        filename = document.filename or f"{document.receipt.receipt_number or 'receipt'}.pdf"
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response


def _import_rows(batch):
    return [import_row_payload(row) for row in batch.rows.order_by("row_number")]


def _import_summary(batch):
    duplicates = batch.rows.filter(status=ReceiptImportRowStatus.DUPLICATE).count()
    return {
        "total": batch.total_rows,
        "valid": batch.valid_rows,
        "invalid": batch.invalid_rows,
        "committed": batch.committed_rows,
        "failed": batch.failed_rows,
        "duplicates": duplicates,
    }


def _import_errors(batch):
    error_statuses = (
        ReceiptImportRowStatus.INVALID,
        ReceiptImportRowStatus.FAILED,
        ReceiptImportRowStatus.DUPLICATE,
    )
    return [row for row in _import_rows(batch) if row["status"] in error_statuses]


def _import_result(batch, *, dry_run):
    """Flattened import result matching the web ``ReceiptImportResult`` contract.

    Superset: also carries the legacy ``batch`` envelope, ``partial_failure``
    and ``error_code`` keys the backend import suite asserts on.
    """
    rows = _import_rows(batch)
    errors = _import_errors(batch)
    committed = batch.committed_rows
    batch_data = ReceiptImportBatchSerializer(batch).data
    error_code = None
    if batch.status == ReceiptImportBatchStatus.PARTIAL:
        error_code = "RECEIPT_IMPORT_PARTIAL_FAILURE"
    elif batch.status == ReceiptImportBatchStatus.FAILED:
        error_code = "RECEIPT_IMPORT_BATCH_FAILED"
    return {
        "dry_run": bool(dry_run),
        "imported": committed if not dry_run else batch.total_rows,
        "created": committed,
        "total_rows": batch.total_rows,
        "ok_count": batch.valid_rows,
        "error_count": batch.invalid_rows,
        "batch_id": str(batch.pk),
        "status": batch.status,
        "rows": rows,
        "errors": errors,
        "summary": _import_summary(batch),
        "batch": batch_data,
        "partial_failure": batch.status == ReceiptImportBatchStatus.PARTIAL,
        "error_code": error_code,
    }


class ReceiptImportTemplateView(ReceiptAPIView):
    """GET /front-office/receipts/import/template/ — downloadable CSV template."""

    def get_permissions(self):
        return [MustActionPermission(action="import")]

    def get(self, request):
        response = HttpResponse(import_csv_template(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="receipt_import_template.csv"'
        return response


class ReceiptImportDryRunView(ReceiptAPIView):
    """POST /front-office/receipts/import/dry-run/ — validate a CSV without creating receipts."""

    def get_permissions(self):
        return [MustActionPermission(action="import")]

    def post(self, request):
        file = request.FILES.get("file")
        if file is None:
            raise import_row_invalid(
                message="A CSV file is required.",
                field_errors={"file": ["Select a CSV file to import."]},
            )
        import_mode = ((request.data or {}).get("import_mode") or "DRAFT").strip()
        batch = dry_run(file=file, import_mode=import_mode, actor=request.user)
        return Response({"data": _import_result(batch, dry_run=True)}, status=200)


class ReceiptImportCommitView(ReceiptAPIView):
    """POST /front-office/receipts/import/commit/ — commit an import batch.

    Accepts either the web flow (a ``file`` plus ``mode``, re-validated then
    committed) or the batch flow (an existing ``batch_id``). Idempotent:
    committed rows are skipped and FAILED rows are retried, so re-committing the
    same batch is safe and completes a partial import.
    """

    def get_permissions(self):
        return [MustActionPermission(action="import")]

    def post(self, request):
        batch_id = ((request.data or {}).get("batch_id") or "").strip()
        file = request.FILES.get("file")
        if batch_id:
            batch = ReceiptImportBatch.objects.filter(pk=batch_id).first()
            if batch is None:
                raise import_batch_not_found()
        elif file is not None:
            import_mode = ((request.data or {}).get("mode") or "CREATE_DRAFTS").strip()
            batch = dry_run(file=file, import_mode=import_mode, actor=request.user)
        else:
            raise import_row_invalid(
                message="A batch_id or a CSV file is required.",
                field_errors={
                    "batch_id": ["Select an import batch to commit."],
                    "file": ["Upload the receipt CSV to commit."],
                },
            )
        commit_batch(batch=batch, actor=request.user)
        return Response({"data": _import_result(batch, dry_run=False)}, status=200)


class ReceiptImportBatchListView(ReceiptAPIView):
    """GET /front-office/receipts/imports/ — paginated import batch register."""

    permission_classes = [MustViewReceiptsPermission]

    def get(self, request):
        queryset = ReceiptImportBatch.objects.select_related("created_by").all()
        page = max(1, int(request.query_params.get("page", 1)))
        page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
        total = queryset.count()
        start = (page - 1) * page_size
        rows = queryset[start : start + page_size]
        return Response(
            {
                "data": {
                    "results": ReceiptImportBatchSerializer(rows, many=True).data,
                    "count": total,
                    "page": page,
                    "page_size": page_size,
                    "next": page * page_size < total,
                    "previous": page > 1,
                }
            }
        )


class ReceiptImportBatchDetailView(ReceiptAPIView):
    """GET /front-office/receipts/imports/<uuid>/ — batch header plus error rows.

    Returns the batch fields flattened (matching the web batch-detail contract)
    with an ``errors`` array of the blocked rows.
    """

    permission_classes = [MustViewReceiptsPermission]

    def get(self, request, batch_id):
        batch = ReceiptImportBatch.objects.select_related("created_by").filter(pk=batch_id).first()
        if batch is None:
            raise import_batch_not_found()
        data = ReceiptImportBatchSerializer(batch).data
        data["errors"] = _import_errors(batch)
        data["rows"] = _import_rows(batch)
        data["batch"] = ReceiptImportBatchSerializer(batch).data
        return Response({"data": data})


class ReceiptImportReprocessView(ReceiptAPIView):
    """POST /front-office/receipts/imports/<uuid>/reprocess/ — retry failed rows.

    Re-runs the commit for a batch; committed rows are skipped and FAILED rows
    are retried, so reprocessing completes a partial import.
    """

    def get_permissions(self):
        return [MustActionPermission(action="import")]

    def post(self, request, batch_id):
        batch = ReceiptImportBatch.objects.select_related("created_by").filter(pk=batch_id).first()
        if batch is None:
            raise import_batch_not_found()
        commit_batch(batch=batch, actor=request.user)
        return Response({"data": _import_result(batch, dry_run=False)}, status=200)


class ReceiptReportingDatasetView(ReceiptAPIView):
    """GET /front-office/receipts/reporting/dataset/ — reporting module contract."""

    permission_classes = [MustViewReceiptsPermission]

    def get(self, request):
        from apps.front_office.receipts.services.reporting_service import register

        return Response({"data": register()})


class PartnerPortalReceiptListView(ReceiptAPIView):
    """GET /front-office/receipts/portal/ — read-only receipts for the linked partner.

    Scoped to the partner's own receipts only; no internal audit state is
    exposed (see ``PartnerPortalReceiptListSerializer``).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        partner = request.user.current_partner() if hasattr(request.user, "current_partner") else None
        if partner is None:
            return Response({"data": {"results": [], "count": 0}})
        queryset = (
            Receipt.objects.select_related("branch", "partner").filter(partner=partner).order_by("-receipt_date", "-created_at")
        )
        return Response(
            {
                "data": {
                    "results": PartnerPortalReceiptListSerializer(queryset[:200], many=True).data,
                    "count": queryset.count(),
                }
            }
        )


class PartnerPortalReceiptDetailView(ReceiptAPIView):
    """GET /front-office/receipts/portal/<uuid>/ — scoped read-only receipt detail.

    Only the linked partner's own receipt resolves; another partner's receipt
    (or a nonexistent one) returns the same 404 so no cross-partner probing is
    possible. Allocations shown are the receipt's own.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, receipt_id):
        partner = request.user.current_partner() if hasattr(request.user, "current_partner") else None
        receipt = None
        if partner is not None:
            receipt = (
                Receipt.objects.select_related("branch", "partner")
                .filter(pk=receipt_id, partner=partner)
                .first()
            )
        if receipt is None:
            raise not_found()
        return Response({"data": PartnerPortalReceiptDetailSerializer(receipt).data})
