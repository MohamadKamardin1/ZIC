from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from django.db.models import Avg, Q, Sum
from django.utils import timezone
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ol_parameters.models import OLProduct
from apps.partner_onboarding.models import Branch
from apps.partners.models import Partner

from .errors import PolicyError, registry_error
from .models import Policy, PolicyStatus, PolicyAuditLog, WithdrawalPayment, WithdrawalRequest, WithdrawalStatus
from .serializers import WithdrawalPaymentSerializer, WithdrawalRequestSerializer
from .services.finance_service import (
    estimate_policy_withdrawal,
    request_staff_withdrawal,
    transition_policy_withdrawal,
    withdrawal_eligibility,
)


WITHDRAWAL_PERMISSION_FALLBACKS = {
    "view": ("ol_withdrawals.view", "ol_policies.view"),
    "request": ("ol_withdrawals.request", "ol_policies.service"),
    "approve": ("ol_withdrawals.approve", "ol_policies.service"),
    "process_payout": ("ol_withdrawals.process_payout", "ol_policies.service"),
    "cancel": ("ol_withdrawals.cancel", "ol_policies.cancel", "ol_policies.service"),
    "reverse": ("ol_withdrawals.reverse", "ol_policies.service"),
    "print": ("ol_withdrawals.print", "ol_policies.print"),
}


class HasOLWithdrawalPermission(BasePermission):
    message = "You do not have the required Ordinary Life Withdrawals permission for this action. Ask an administrator to grant the appropriate withdrawal entitlement."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, "is_superuser", False):
            return True
        action = getattr(view, "action", None) or ("view" if request.method in {"GET", "HEAD", "OPTIONS"} else "request")
        codes = WITHDRAWAL_PERMISSION_FALLBACKS.get(action, WITHDRAWAL_PERMISSION_FALLBACKS["view"])
        has_permission = getattr(request.user, "has_permission", None)
        if callable(has_permission) and any(has_permission(code) for code in codes):
            return True
        module_permission = getattr(request.user, "has_module_permission", None)
        if callable(module_permission):
            return any(module_permission("ol_withdrawals", action.upper()) or module_permission("ol_policies", code.rsplit(".", 1)[-1].upper()) for code in codes)
        return False


def _as_int(value, default, *, maximum=100):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise registry_error(
            "WITHDRAWAL_INVALID_PAGINATION",
            field_errors={"page": ["Page and page size must be whole numbers."]},
        )
    if parsed < 1:
        raise registry_error(
            "WITHDRAWAL_INVALID_PAGINATION",
            field_errors={"page": ["Page and page size must be at least 1."]},
        )
    return min(parsed, maximum)


def _paginate(queryset, request, serializer_class, *, page_size_default=20, max_page_size=100):
    page_number = _as_int(request.query_params.get("page", 1), 1, maximum=100000)
    page_size = _as_int(request.query_params.get("page_size", page_size_default), page_size_default, maximum=max_page_size)
    paginator = Paginator(queryset, page_size)
    page = paginator.get_page(page_number)
    return {
        "count": paginator.count,
        "page": page.number,
        "page_size": page.paginator.per_page,
        "next": page.next_page_number() if page.has_next() else None,
        "previous": page.previous_page_number() if page.has_previous() else None,
        "results": serializer_class(page.object_list, many=True).data,
    }


def _partner_display(partner):
    if not partner:
        return ""
    name = getattr(partner, "legal_name", "") or " ".join(
        value for value in (getattr(partner, "first_name", ""), getattr(partner, "other_name", ""), getattr(partner, "surname", "")) if value
    )
    return " — ".join(value for value in (getattr(partner, "partner_number", ""), name) if value) or "Unnamed partner"


def _active_date_filter(queryset, field_prefix=""):
    today = timezone.localdate()
    return queryset.filter(
        Q(**{f"{field_prefix}effective_from__isnull": True}) | Q(**{f"{field_prefix}effective_from__lte": today}),
        Q(**{f"{field_prefix}effective_to__isnull": True}) | Q(**{f"{field_prefix}effective_to__gte": today}),
    )


def _policy_queryset(request):
    queryset = WithdrawalRequest.objects.select_related("policy", "policy__partner", "policy__agent", "payment_requisition").all()
    query = str(request.query_params.get("q", request.query_params.get("search", ""))).strip()
    status = str(request.query_params.get("status", "")).strip().upper()
    product = str(request.query_params.get("product", request.query_params.get("product_id", ""))).strip()
    branch = str(request.query_params.get("branch", request.query_params.get("branch_id", "")).strip())
    agent = str(request.query_params.get("agent", request.query_params.get("agent_id", "")).strip())
    if query:
        queryset = queryset.filter(
            Q(request_number__icontains=query)
            | Q(policy__policy_number__icontains=query)
            | Q(policy__partner__legal_name__icontains=query)
            | Q(policy__partner__partner_number__icontains=query)
            | Q(policy__product_plan_ref__icontains=query)
        )
    if status:
        queryset = queryset.filter(status=status)
    if product:
        queryset = queryset.filter(policy__product_plan_ref__icontains=product)
    if agent:
        queryset = queryset.filter(Q(policy__agent_id=agent) | Q(policy__agent__partner_number__icontains=agent))
    if branch:
        queryset = queryset.filter(
            Q(policy__contract_snapshot__branch_code__icontains=branch)
            | Q(policy__contract_snapshot__branch_name__icontains=branch)
            | Q(policy__contract_snapshot__location_code__icontains=branch)
        )
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")
    if date_from:
        queryset = queryset.filter(request_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(request_date__lte=date_to)
    if str(request.query_params.get("pending_approval_only", "")).lower() == "true":
        queryset = queryset.filter(status=WithdrawalStatus.REQUESTED)
    ordering = str(request.query_params.get("ordering", "-request_date")).strip()
    allowed_ordering = {"request_date", "-request_date", "amount", "-amount", "status", "-status", "created_at", "-created_at"}
    return queryset.order_by(ordering if ordering in allowed_ordering else "-request_date", "-created_at")


def _option(value, label, **meta):
    return {"value": str(value), "label": label, "meta": meta}


def _options(kind, request):
    query = str(request.query_params.get("q", "")).strip()
    if kind == "policies":
        queryset = Policy.objects.select_related("partner").filter(status__in=[PolicyStatus.ACTIVE, PolicyStatus.PAID_UP]).order_by("policy_number")
        if query:
            queryset = queryset.filter(Q(policy_number__icontains=query) | Q(partner__legal_name__icontains=query) | Q(partner__partner_number__icontains=query))
        rows = []
        for policy in queryset[:500]:
            _, context, eligible = withdrawal_eligibility(policy.pk)
            rows.append(_option(policy.pk, f"{policy.policy_number} — {_partner_display(policy.partner)}", policy_number=policy.policy_number, policyholder_name=_partner_display(policy.partner), status=policy.status, currency=policy.currency, cash_value=str(context["cash_value"]), loan_balance=str(context["loan_balance"]), available_limit=str(context["available"]), eligible=eligible))
        return rows
    if kind == "products":
        queryset = OLProduct.objects.filter(is_active=True).order_by("code")
        if query:
            queryset = queryset.filter(Q(code__icontains=query) | Q(name__icontains=query))
        return [_option(item.code, f"{item.code} — {item.name}", active=True) for item in queryset[:500]]
    if kind == "branches":
        queryset = Branch.objects.filter(is_active=True).order_by("code")
        if query:
            queryset = queryset.filter(Q(code__icontains=query) | Q(name__icontains=query))
        return [_option(item.code, f"{item.code} — {item.name}", active=True) for item in queryset[:500]]
    if kind == "agents":
        queryset = Partner.objects.filter(is_active=True, partner_type__in=["AGENT", "INTERMEDIARY"]).order_by("partner_number")
        if query:
            queryset = queryset.filter(Q(partner_number__icontains=query) | Q(legal_name__icontains=query) | Q(first_name__icontains=query) | Q(surname__icontains=query))
        return [_option(item.pk, _partner_display(item), active=True, partner_type=item.partner_type) for item in queryset[:500]]
    if kind == "payment-modes":
        modes = (("BANK_TRANSFER", "Bank transfer"), ("MOBILE_MONEY", "Mobile money"), ("CHEQUE", "Cheque"), ("CASH", "Cash"))
        return [_option(value, label, active=True) for value, label in modes if not query or query.lower() in f"{value} {label}".lower()]
    raise registry_error("WITHDRAWAL_OPTIONS_ENTITY_NOT_FOUND", details={"entity": kind})


def _page_rows(rows, request):
    page_number = _as_int(request.query_params.get("page", 1), 1, maximum=100000)
    page_size = _as_int(request.query_params.get("page_size", 20), 20, maximum=100)
    start = (page_number - 1) * page_size
    return {"count": len(rows), "page": page_number, "page_size": page_size, "next": page_number + 1 if start + page_size < len(rows) else None, "previous": page_number - 1 if page_number > 1 else None, "results": rows[start : start + page_size]}


class StaffWithdrawalListView(APIView):
    permission_classes = [HasOLWithdrawalPermission]
    action = "view"

    def get(self, request):
        return Response({"data": _paginate(_policy_queryset(request), request, WithdrawalRequestSerializer)})


class StaffWithdrawalKpiView(APIView):
    permission_classes = [HasOLWithdrawalPermission]
    action = "view"

    def get(self, request):
        queryset = _policy_queryset(request)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        current = queryset.filter(request_date__gte=month_start, request_date__lte=today)
        totals = current.aggregate(total=Sum("amount"), average_fee=Avg("fee_amount"))
        pending = current.filter(status=WithdrawalStatus.REQUESTED).aggregate(count=Sum("amount"))
        pending_queryset = current.filter(status=WithdrawalStatus.REQUESTED)
        processing_count = current.filter(status=WithdrawalStatus.PROCESSING).count()
        by_currency = defaultdict(lambda: {"count": 0, "gross_amount": "0.00", "fee_amount": "0.00"})
        for row in current:
            bucket = by_currency[row.policy.currency]
            bucket["count"] += 1
            bucket["gross_amount"] = str(Decimal(bucket["gross_amount"]) + row.amount)
            bucket["fee_amount"] = str(Decimal(bucket["fee_amount"]) + row.fee_amount)
        currency = request.query_params.get("currency") or (next(iter(by_currency), "TZS"))
        return Response({"data": {
            "total_withdrawn_current_month": str(totals["total"] or Decimal("0.00")),
            "total_withdrawn_current_month_count": current.count(),
            "pending_approvals_count": pending_queryset.count(),
            "pending_approvals_amount": str(pending_queryset.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")),
            "processing_payouts_count": processing_count,
            "average_fee_amount": str(totals["average_fee"] or Decimal("0.00")),
            "currency": currency,
            "amounts_by_currency": dict(by_currency),
            "timestamp": timezone.now(),
        }})


class StaffWithdrawalOptionsView(APIView):
    permission_classes = [HasOLWithdrawalPermission]
    action = "view"

    def get_permissions(self):
        kind = str(self.kwargs.get("kind", ""))
        self.action = "request" if kind == "policies" else "process_payout" if kind == "payment-modes" else "view"
        return super().get_permissions()

    def get(self, request, kind):
        return Response({"data": _page_rows(_options(kind, request), request)})


class StaffWithdrawalDetailView(APIView):
    permission_classes = [HasOLWithdrawalPermission]
    action = "view"

    def get_object(self, withdrawal_id):
        withdrawal = WithdrawalRequest.objects.select_related("policy", "policy__partner", "policy__agent", "payment_requisition").filter(pk=withdrawal_id).first()
        if not withdrawal:
            raise registry_error("WITHDRAWAL_NOT_FOUND")
        return withdrawal

    def get(self, request, withdrawal_id):
        withdrawal = self.get_object(withdrawal_id)
        payload = WithdrawalRequestSerializer(withdrawal).data
        payload["breakdown"] = _breakdown(withdrawal)
        payload["payments"] = WithdrawalPaymentSerializer(withdrawal.payments.all(), many=True).data
        payload["audit_timeline"] = _audit_rows(withdrawal)
        payload["documents"] = []
        payload["policy_context"] = {
            "policy_number": withdrawal.policy.policy_number,
            "policy_status": withdrawal.policy.status,
            "cash_value_before": str(withdrawal.cash_value_before),
            "cash_value_after": str(withdrawal.cash_value_after or withdrawal.cash_value_before - withdrawal.amount),
            "loan_balance_before": str(withdrawal.loan_balance_before),
        }
        return Response({"data": payload})


def _breakdown(withdrawal):
    policy = withdrawal.policy
    snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
    cash_after = withdrawal.cash_value_after if withdrawal.cash_value_after is not None else withdrawal.cash_value_before - withdrawal.amount
    sum_assured_before = snapshot.get("sum_assured")
    sum_assured_after = snapshot.get("sum_assured_after_withdrawal")
    return {
        "withdrawal_id": str(withdrawal.pk),
        "currency": policy.currency,
        "cash_value_before": str(withdrawal.cash_value_before),
        "gross_withdrawal": str(withdrawal.amount),
        "withdrawal_fee": str(withdrawal.fee_amount),
        "fee_rate": str(withdrawal.fee_rate),
        "fee_basis": withdrawal.fee_basis,
        "net_payout": str(withdrawal.net_amount),
        "cash_value_after": str(cash_after),
        "sum_assured_before": str(sum_assured_before) if sum_assured_before not in (None, "") else None,
        "sum_assured_after": str(sum_assured_after) if sum_assured_after not in (None, "") else None,
        "adjustment_ratio": snapshot.get("withdrawal_sum_assured_adjustment_ratio"),
        "audit_trail": [{"action": "CALCULATED", "actor_name": "Backend finance service", "source_channel": "SYSTEM", "created_at": withdrawal.created_at}],
    }


def _audit_rows(withdrawal):
    rows = []
    for entry in PolicyAuditLog.objects.filter(policy=withdrawal.policy, event_type__icontains="Withdrawal").select_related("actor").order_by("created_at"):
        actor = entry.actor
        actor_display = "System" if actor is None else (actor.get_full_name() or getattr(actor, "email", "") or "User")
        rows.append({"id": str(entry.pk), "action": entry.event_type, "actor_display": actor_display, "source_channel": entry.source_channel, "reason": entry.reason, "created_at": entry.created_at})
    return rows


class StaffWithdrawalBreakdownView(StaffWithdrawalDetailView):
    def get(self, request, withdrawal_id):
        withdrawal = self.get_object(withdrawal_id)
        return Response({"data": _breakdown(withdrawal)})


class StaffWithdrawalPaymentsView(StaffWithdrawalDetailView):
    def get(self, request, withdrawal_id):
        withdrawal = self.get_object(withdrawal_id)
        return Response({"data": _paginate(withdrawal.payments.all(), request, WithdrawalPaymentSerializer)})


class StaffWithdrawalAuditView(StaffWithdrawalDetailView):
    def get(self, request, withdrawal_id):
        withdrawal = self.get_object(withdrawal_id)
        rows = _audit_rows(withdrawal)
        return Response({"data": _page_rows(rows, request)})


class StaffWithdrawalEligibilityView(APIView):
    permission_classes = [HasOLWithdrawalPermission]
    action = "request"

    def get(self, request, policy_id):
        policy, context, eligible = withdrawal_eligibility(policy_id, as_of=request.query_params.get("as_of"))
        return Response({"data": {"policy_id": str(policy.pk), "policy_number": policy.policy_number, "policyholder_display": _partner_display(policy.partner), "currency": policy.currency, "policy_status": policy.status, "eligible": eligible, "cash_value": str(context["cash_value"]), "loan_balance": str(context["loan_balance"]), "available_limit": str(context["available"]), "fee_rate": str(context["fee_rate"]), "fee_basis": context["fee_basis"]}})


class StaffWithdrawalEstimateView(APIView):
    permission_classes = [HasOLWithdrawalPermission]
    action = "request"

    def post(self, request):
        policy, context, estimate = estimate_policy_withdrawal(request.data.get("policy_id"), amount=request.data.get("amount"), as_of=request.data.get("as_of"))
        return Response({"data": {"policy_id": str(policy.pk), "currency": policy.currency, "requested_amount": str(estimate["requested_amount"]), "estimated_fee": str(estimate["fee"]), "estimated_net_payout": str(estimate["net"]), "fee_rate": str(context["fee_rate"]), "fee_basis": context["fee_basis"]}})


class StaffWithdrawalRequestView(APIView):
    permission_classes = [HasOLWithdrawalPermission]
    action = "request"

    def post(self, request, policy_id):
        withdrawal = request_staff_withdrawal(policy_id, amount=request.data.get("amount"), reason=request.data.get("reason", ""), as_of=request.data.get("as_of"), actor=request.user, request=request, source_channel="WEB", idempotency_key=request.headers.get("X-Idempotency-Key", ""))
        return Response({"data": {"withdrawal": WithdrawalRequestSerializer(withdrawal).data}}, status=201)


class StaffWithdrawalActionView(APIView):
    permission_classes = [HasOLWithdrawalPermission]

    def get_permissions(self):
        action = str(self.kwargs.get("action", "")).replace("-", "_")
        self.action = action
        return super().get_permissions()

    def post(self, request, withdrawal_id, action):
        withdrawal = transition_policy_withdrawal(withdrawal_id, action=action, reason=request.data.get("reason", ""), payment_mode=request.data.get("payment_mode", ""), receipt_reference=request.data.get("receipt_reference", ""), actor=request.user, request=request, source_channel="WEB")
        return Response({"data": {"withdrawal": WithdrawalRequestSerializer(withdrawal).data}})
