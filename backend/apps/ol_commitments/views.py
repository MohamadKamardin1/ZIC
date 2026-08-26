from datetime import timedelta

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.models import DomainEvent
from apps.ol_commitments import events as events_service
from apps.ol_commitments.errors import CommitmentError
from apps.ol_commitments.errors import not_found as commitment_not_found
from apps.ol_commitments.events import COMMITMENT_OVERDUE
from apps.ol_commitments.models import OLCommitment, OLCommitmentAllocation
from apps.ol_commitments.permissions import has_ol_commitment_permission
from apps.ol_commitments.serializers import (
    CommitmentBaseSerializer,
    CommitmentDetailSerializer,
    ManualCommitmentSerializer,
)
from apps.ol_commitments.services.allocation_service import allocate_to_commitment
from apps.ol_commitments.services.commitment_actions import allowed_actions, is_allowed_action
from apps.ol_commitments.services.overdue_service import lapse_review_rows, run_overdue_processing
from apps.ol_parameters.models import OLCommitmentStatus

TERMINAL_STATUS_CODES = None
DEFAULT_CURRENCIES = ["TZS", "USD"]
DEFAULT_PAYMENT_MODES = ["CASH", "BANK_TRANSFER", "CHEQUE", "M-PESA", "MOBILE_MONEY", "OTHER"]


def _terminal_codes():
    global TERMINAL_STATUS_CODES
    if TERMINAL_STATUS_CODES is None:
        TERMINAL_STATUS_CODES = list(
            OLCommitmentStatus.objects.filter(is_active=True, is_terminal=True).values_list("code", flat=True)
        )
    return TERMINAL_STATUS_CODES


class MustProcessOverduePermission(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return has_ol_commitment_permission(request.user, "process_overdue")


class MustViewCommitmentsPermission(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return has_ol_commitment_permission(request.user, "view")


class MustActionPermission(IsAuthenticated):
    """Gate a lifecycle action on its matching permission code."""

    action = None

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return has_ol_commitment_permission(request.user, self.action)


def _true(value):
    return value in ("true", "1", "True")


def _paginate(query, request):
    page = max(1, int(request.query_params.get("page", 1)))
    page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
    total = query.count()
    start = (page - 1) * page_size
    rows = query[start: start + page_size]
    return {
        "results": CommitmentBaseSerializer(rows, many=True).data,
        "count": total,
        "page": page,
        "page_size": page_size,
        "next": page * page_size < total,
        "previous": page > 1,
    }


class CommitmentListView(APIView):
    permission_classes = [MustViewCommitmentsPermission]

    def get(self, request):
        params = request.query_params
        queryset = OLCommitment.objects.select_related("partner", "product", "plan").all()

        status = params.get("status")
        if status:
            queryset = queryset.filter(status__iexact=status)
        source_type = params.get("source_type")
        if source_type:
            queryset = queryset.filter(source_type__iexact=source_type)
        currency = params.get("currency")
        if currency:
            queryset = queryset.filter(currency__iexact=currency)
        product = params.get("product")
        if product:
            queryset = queryset.filter(product_name_snapshot__icontains=product)
        due_from = params.get("due_date_from")
        if due_from:
            queryset = queryset.filter(due_date__gte=due_from)
        due_to = params.get("due_date_to")
        if due_to:
            queryset = queryset.filter(due_date__lte=due_to)
        if _true(params.get("balance_only")):
            queryset = queryset.filter(balance__gt=0)
        if _true(params.get("approval_required")):
            queryset = queryset.filter(approval_required=True)
        if _true(params.get("overdue_only")):
            queryset = queryset.filter(
                Q(status__iexact="OVERDUE") | Q(due_date__lt=timezone.localdate(), balance__gt=0),
                balance__gt=0,
            )

        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(commitment_number__icontains=search)
                | Q(source_reference__icontains=search)
                | Q(partner_name_snapshot__icontains=search)
            )

        ordering = params.get("ordering", "-due_date")
        order_map = {
            "commitment_number": "commitment_number",
            "due_date": "due_date",
            "status": "status",
            "premium_amount": "premium_amount",
            "amount_paid": "amount_paid",
            "balance": "balance",
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


class CommitmentDetailView(APIView):
    permission_classes = [MustViewCommitmentsPermission]

    def get(self, request, commitment_id):
        commitment = OLCommitment.objects.select_related("partner", "product", "plan").filter(
            pk=commitment_id
        ).prefetch_related("allocations", "notification_logs").first()
        if not commitment:
            raise commitment_not_found()
        return Response({"data": CommitmentDetailSerializer(commitment).data})


class CommitmentKPIsView(APIView):
    permission_classes = [MustViewCommitmentsPermission]

    def get(self, request):
        today = timezone.localdate()
        queryset = OLCommitment.objects.all()
        kwargs = {"kpis_queryset": queryset, "today": today}
        return Response({"data": _kpis(**kwargs)})


def _kpis(*, kpis_queryset, today):
    active = kpis_queryset.exclude(status__in=_terminal_codes())
    period_start = today - timedelta(days=30)
    return {
        "total_due": str(active.aggregate(total=models_sum_value("premium_amount"))["total"] or 0),
        "total_outstanding": str(active.aggregate(total=models_sum_value("balance"))["total"] or 0),
        "overdue_count": active.filter(Q(status__iexact="OVERDUE") | Q(due_date__lt=today), balance__gt=0).count(),
        "collected_in_period": str(
            active.filter(updated_at__gte=period_start).aggregate(total=models_sum_value("amount_paid"))["total"] or 0
        ),
        "approvals_pending": active.filter(approval_required=True).count(),
    }


def models_sum_value(field):
    return Sum(field, default=0)


class CommitmentOptionsView(APIView):
    permission_classes = [MustViewCommitmentsPermission]

    def get(self, request):
        statuses = [
            {"code": s.code, "name": s.name, "tone": _status_tone(s.code)}
            for s in OLCommitmentStatus.objects.filter(is_active=True).order_by("display_order", "code")
        ]
        currencies = list(OLCommitment.objects.exclude(currency="").values_list("currency", flat=True).distinct()[:20])
        return Response(
            {
                "data": {
                    "statuses": statuses,
                    "currencies": list(dict.fromkeys(currencies + DEFAULT_CURRENCIES)),
                    "payment_modes": DEFAULT_PAYMENT_MODES,
                }
            }
        )


def _status_tone(code):
    upper = (code or "").upper()
    if any(marker in upper for marker in ("COMPLETED", "PAID", "FINAL")):
        return "success"
    if any(marker in upper for marker in ("CANCEL", "LAPSED", "OVERDUE", "FAILED", "REJECTED")):
        return "danger"
    if any(marker in upper for marker in ("SUSPEND", "WAIVED", "PARTIAL", "PENDING", "ACTIVE", "GRACE")):
        return "warning"
    if any(marker in upper for marker in ("REVIEW", "APPROVAL", "PROCESSING")):
        return "info"
    return "neutral"


class CommitmentSourcesView(APIView):
    permission_classes = [MustViewCommitmentsPermission]

    def get(self, request):
        source_type = request.query_params.get("source_type", "").upper()
        if source_type == "PROPOSAL":
            from apps.ol_proposals.models import OLProposal

            rows = [
                {"id": str(p.pk), "label": p.prospect_snapshot.get("name", "") or p.proposal_number, "reference": p.proposal_number}
                for p in OLProposal.objects.order_by("-created_at")[:200]
            ]
        elif source_type == "POLICY":
            from apps.ordinary_life.models import OLPolicy

            rows = [
                {
                    "id": str(p.pk),
                    "label": (p.policyholder_partner.name if p.policyholder_partner_id else "") or p.policy_number,
                    "reference": p.policy_number,
                }
                for p in OLPolicy.objects.order_by("-created_at")[:200]
            ]
        else:
            rows = []
        return Response({"data": {"results": rows}})


class CommitmentReferencesView(APIView):
    permission_classes = [MustViewCommitmentsPermission]

    def get(self, request):
        from apps.ol_parameters.models import OLProduct
        from apps.ordinary_life.models import OLPlan
        from apps.partners.models import Partner

        partners = [
            {"id": str(p.pk), "label": p.name}
            for p in Partner.objects.filter(is_active=True, status="ACTIVE").order_by("name")[:200]
        ]
        products = [
            {"id": str(p.pk), "label": p.name}
            for p in OLProduct.objects.filter(is_active=True).order_by("name")[:200]
        ]
        plans = [
            {"id": str(p.pk), "label": p.name}
            for p in OLPlan.objects.filter(is_active=True).order_by("name")[:200]
        ]
        return Response({"data": {"partners": partners, "products": products, "plans": plans}})


class ManualCommitmentCreateView(APIView):
    permission_classes = [MustActionPermission]
    action = "create"

    def post(self, request):
        serializer = ManualCommitmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        commitment = serializer.save()
        events_service.emit_generated(commitment, actor=request.user, reason="Manual commitment created.", source_channel="MANUAL")
        return Response({"data": CommitmentDetailSerializer(commitment).data}, status=201)


class CommitmentImportsView(APIView):
    permission_classes = [MustViewCommitmentsPermission]

    def get(self, request):
        # Full import-run history lands with the generation/import engine milestone.
        return Response({"data": {"results": []}})


class CommitmentImportDetailView(APIView):
    permission_classes = [MustViewCommitmentsPermission]

    def get(self, request, import_id):
        return Response({"data": {"errors": [], "ok_count": 0, "error_count": 0}})


class CommitmentActionDispatchView(APIView):
    """POST /commitments/<uuid>/<action>/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, commitment_id, action):
        actions = {
            "record_payment": "record_payment",
            "reverse_allocation": "reverse",
            "suspend": "suspend",
            "reactivate": "suspend",
            "waive": "waive",
            "cancel": "cancel",
            "reschedule": "reschedule",
        }
        if action not in actions:
            raise CommitmentError(f"Unknown action '{action}'.", error_code="ACTION_NOT_FOUND", status_code=404)
        if not has_ol_commitment_permission(request.user, actions[action]):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(f"Missing permission: ol_commitments.{actions[action]}")

        commitment = OLCommitment.objects.select_for_update().filter(pk=commitment_id).first()
        if not commitment:
            raise commitment_not_found()

        with transaction.atomic():
            if action == "record_payment":
                return _record_payment(request, commitment)
            if action == "reverse_allocation":
                return _reverse_allocation(request, commitment)
            return _lifecycle_action(request, commitment, action)


def _detail(commitment):
    return Response({"data": CommitmentDetailSerializer(commitment).data})


def _record_payment(request, commitment):
    data = request.data
    if not is_allowed_action(commitment, "record_payment"):
        raise _invalid_transition(commitment, "record_payment")
    try:
        allocate_to_commitment(
            commitment,
            amount=data.get("amount"),
            receipt_reference=(data.get("receipt_reference") or "").strip(),
            payment_mode=data.get("payment_mode") or "",
            currency=data.get("currency") or commitment.currency,
            exchange_rate=data.get("exchange_rate"),
            reason=(data.get("reason") or "").strip(),
            allocated_by=request.user if request.user.is_authenticated else None,
            source_channel=(data.get("source_channel") or "API"),
            from_status=(data.get("from_status") or "").strip(),
        )
    except CommitmentError:
        raise
    return _detail(commitment)


def _reverse_allocation(request, commitment):
    if not is_allowed_action(commitment, "reverse"):
        raise _invalid_transition(commitment, "reverse")
    allocation_id = request.data.get("allocation_id")
    reason = (request.data.get("reason") or "").strip()
    if not reason:
        raise CommitmentError("A reason is required to reverse an allocation.", error_code="VALIDATION_ERROR", field_errors={"reason": ["A reason is required."]})
    allocation = OLCommitmentAllocation.objects.filter(pk=allocation_id, commitment=commitment, reversal_of__isnull=True).first()
    if not allocation:
        raise CommitmentError("The allocation is not reversible.", error_code="COMMITMENT_NOT_FOUND", status_code=404, field_errors={"allocation_id": ["Allocation not found or already reversed."]})
    amount = float(allocation.amount)
    paid = float(commitment.amount_paid or 0)
    if amount > paid + 0.001:
        raise CommitmentError("Reversal amount exceeds the amount paid.", error_code="VALIDATION_ERROR", field_errors={"allocation_id": ["Amount not available to reverse."]})

    commitment.amount_paid = paid - amount
    commitment.recompute_balance()
    commitment.reason_text = reason
    commitment.save()

    OLCommitmentAllocation.objects.create(
        commitment=commitment,
        receipt_reference=f"{allocation.receipt_reference}-R1",
        amount=amount,
        payment_mode=allocation.payment_mode,
        currency=allocation.currency,
        exchange_rate=allocation.exchange_rate,
        reason=reason,
        reversal_of=allocation,
        allocated_by=request.user if request.user.is_authenticated else None,
        source_channel="API",
    )
    events_service.emit_payment_allocated(commitment, allocation=allocation, actor=request.user, reason=reason, source_channel="API")
    if commitment.status in ("COMPLETED",) and commitment.balance > 0:
        commitment.status = _resolve_status("PARTIALLY_PAID") or commitment.status
        commitment.save()
    return _detail(commitment)


def _lifecycle_action(request, commitment, action):
    if not is_allowed_action(commitment, action):
        raise _invalid_transition(commitment, action)
    reason = (request.data.get("reason") or "").strip()
    if not reason:
        raise CommitmentError("A reason is required for this action.", error_code="VALIDATION_ERROR", field_errors={"reason": ["A reason is required."]})

    if action == "suspend":
        commitment.status = _resolve_status("SUSPENDED") or _require_status("SUSPENDED")
    elif action == "reactivate":
        commitment.status = _resolve_status("ACTIVE") or _resolve_status("PENDING") or "PENDING"
    elif action == "waive":
        commitment.status = _resolve_status("WAIVED") or _require_status("WAIVED")
        commitment.amount_waived = commitment.balance
        commitment.approval_required = True
        commitment.recompute_balance()
    elif action == "cancel":
        commitment.status = _resolve_status("CANCELLED") or _require_status("CANCELLED")
    elif action == "reschedule":
        new_due = request.data.get("due_date")
        if not new_due:
            raise CommitmentError("A new due date is required to reschedule.", error_code="VALIDATION_ERROR", field_errors={"due_date": ["Choose a new due date."]})
        commitment.due_date = new_due
        commitment.grace_date = None
        commitment.warning_date = None
        commitment.pre_lapse_date = None
        commitment.lapse_date = None

    commitment.reason_code = action.upper()
    commitment.reason_text = reason
    commitment.save()
    _emit_lifecycle(request, commitment, action)
    return _detail(commitment)


def _emit_lifecycle(request, commitment, action):
    actor = request.user
    emit = {
        "suspend": events_service.emit_suspended,
        "reactivate": events_service.emit_suspended,
        "waive": events_service.emit_waived,
        "cancel": events_service.emit_cancelled,
        "reschedule": None,
    }.get(action)
    if emit:
        emit(commitment, actor=actor, reason=commitment.reason_text, source_channel="API")


def _resolve_status(code_like):
    row = OLCommitmentStatus.objects.filter(is_active=True, code__icontains=code_like).order_by("display_order", "code").first()
    return row.code if row else None


def _require_status(code_like):
    code = _resolve_status(code_like)
    if not code:
        raise CommitmentError(
            f"Configure the '{code_like}' status under OL Parameters > Policy Setup > OL Commitment Statuses.",
            error_code="PARAMETER_MISSING",
            status_code=422,
            resolution_steps=[
                "Open Ordinary Life Parameters > Policy Setup.",
                "Add an active status whose code contains the required value.",
                "Retry the action.",
            ],
        )
    return code


def _invalid_transition(commitment, action):
    allowed = ", ".join(allowed_actions(commitment) or ["view"])
    steps = [f"Choose one of the allowed actions for the current status: {allowed}."]
    return CommitmentError(
        f"'{action}' is not allowed while the commitment is '{commitment.status}'.",
        error_code="COMMITMENT_INVALID_TRANSITION",
        status_code=422,
        resolution_steps=steps,
    )


class ProcessOverdueView(APIView):
    """POST /api/v1/ol-commitments/commitments/process-overdue/"""

    permission_classes = [MustProcessOverduePermission]

    def post(self, request):
        from apps.governance.services.audit_service import AuditContext

        result = run_overdue_processing(
            actor=AuditContext.get_context().get("user"),
            source_channel="BATCH",
        )
        return Response(
            {
                "data": {
                    "processed": result.processed,
                    "overdue": result.overdue,
                    "notified": result.notified,
                    "lapse_reviews": result.lapse_reviews,
                }
            }
        )


class LapseReviewView(APIView):
    """GET /api/v1/ol-commitments/commitments/lapse-review/"""

    permission_classes = [MustViewCommitmentsPermission]

    def get(self, request):
        return Response({"data": {"results": lapse_review_rows()}})


class OverdueNotificationsView(APIView):
    """GET /api/v1/ol-commitments/notifications/overdue/"""

    permission_classes = [MustViewCommitmentsPermission]

    def get(self, request):
        events = DomainEvent.objects.filter(event_type=COMMITMENT_OVERDUE).order_by("-occurred_at")[:30]
        items = []
        for event in events:
            payload = event.payload or {}
            commitment_id = payload.get("commitment_id") or event.aggregate_id
            commitment_number = payload.get("commitment_number") or ""
            items.append(
                {
                    "id": str(event.pk),
                    "title": f"Commitment {commitment_number or commitment_id or ''} is overdue",
                    "message": "A commitment passed its grace date and needs attention.",
                    "deep_link": f"/ordinary-life/commitments/{commitment_id}" if commitment_id else "/ordinary-life/commitments",
                    "created_at": event.occurred_at,
                }
            )
        return Response({"data": {"results": items}})