from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import not_found
from .models import Policy, PolicyStatus, WithdrawalRequest
from .serializers import WithdrawalRequestSerializer
from .services.finance_service import request_policy_withdrawal


def _partner_display(partner):
    if not partner:
        return "Unnamed partner"
    number = getattr(partner, "partner_number", "") or ""
    name = getattr(partner, "legal_name", "") or ""
    if not name:
        name = " ".join(
            value
            for value in (
                getattr(partner, "first_name", ""),
                getattr(partner, "other_name", ""),
                getattr(partner, "surname", ""),
            )
            if value
        )
    return " — ".join(part for part in (number, name) if part) or "Unnamed partner"


def _portal_payload(withdrawal, *, include_sensitive=False):
    policy = withdrawal.policy
    fee_amount = Decimal(withdrawal.amount) - Decimal(withdrawal.net_amount)
    payload = {
        "id": str(withdrawal.pk),
        "request_number": withdrawal.request_number,
        "policy_id": str(policy.pk),
        "policy_number": policy.policy_number,
        "policyholder_display": _partner_display(policy.partner),
        "product_display": policy.product_plan_ref,
        "currency": withdrawal.policy.currency,
        "gross_amount": str(withdrawal.amount),
        "net_payout": str(withdrawal.net_amount),
        "status": withdrawal.status,
        "status_display": withdrawal.get_status_display(),
        "requested_at": withdrawal.request_date,
        "reason": withdrawal.reason,
        "request_allowed": policy.status in {PolicyStatus.ACTIVE, PolicyStatus.PAID_UP},
    }
    if include_sensitive:
        payload.update(
            {
                "fee_amount": str(fee_amount),
                "cash_value_before": str(withdrawal.cash_value_before),
                "loan_balance_before": str(withdrawal.loan_balance_before),
                "cash_value_after": str(Decimal(withdrawal.cash_value_before) - Decimal(withdrawal.amount)),
            }
        )
    return payload


def _include_sensitive(request):
    return bool(
        getattr(request.user, "is_superuser", False)
        or getattr(request.user, "has_permission", lambda _code: False)("ol_withdrawals.portal_sensitive")
    )


def _visible_policy(request, policy_id):
    return Policy.objects.filter(pk=policy_id, partner__in=request.user.visible_partners()).select_related("partner").first()


class PartnerPortalWithdrawalListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = WithdrawalRequest.objects.filter(policy__partner__in=request.user.visible_partners()).select_related("policy", "policy__partner").order_by("-request_date", "-created_at")
        query = str(request.query_params.get("q", "")).strip()
        status = str(request.query_params.get("status", "")).strip()
        if query:
            queryset = queryset.filter(
                Q(request_number__icontains=query)
                | Q(policy__policy_number__icontains=query)
                | Q(policy__partner__legal_name__icontains=query)
            )
        if status:
            queryset = queryset.filter(status=status)
        paginator = Paginator(queryset, max(1, min(int(request.query_params.get("page_size", 20) or 20), 100)))
        page = paginator.get_page(request.query_params.get("page", 1))
        return Response(
            {
                "data": {
                    "count": paginator.count,
                    "page": page.number,
                    "page_size": page.paginator.per_page,
                    "next": page.next_page_number() if page.has_next() else None,
                    "previous": page.previous_page_number() if page.has_previous() else None,
                    "results": [_portal_payload(item, include_sensitive=_include_sensitive(request)) for item in page.object_list],
                }
            }
        )

    def post(self, request):
        policy_id = request.data.get("policy_id")
        policy = _visible_policy(request, policy_id)
        if policy is None:
            raise not_found(policy_id)
        if policy.status not in {PolicyStatus.ACTIVE, PolicyStatus.PAID_UP}:
            return Response({"error": {"code": "WITHDRAWAL_POLICY_INELIGIBLE", "message": "Policy is not eligible for withdrawals.", "resolution_steps": ["Choose an Active or Paid-up policy.", "Contact ZIC Finance if the policy status needs review."]}}, status=400)
        try:
            amount = Decimal(str(request.data.get("amount")))
        except (InvalidOperation, TypeError):
            return Response({"error": {"code": "WITHDRAWAL_AMOUNT_REQUIRED", "message": "Enter a withdrawal amount greater than zero.", "field_errors": {"amount": ["Enter a valid amount greater than zero."]}}}, status=400)
        if amount <= 0:
            return Response({"error": {"code": "WITHDRAWAL_AMOUNT_REQUIRED", "message": "Enter a withdrawal amount greater than zero.", "field_errors": {"amount": ["Enter a valid amount greater than zero."]}}}, status=400)
        withdrawal = request_policy_withdrawal(policy.pk, amount=amount, reason=request.data.get("reason", ""), as_of=request.data.get("as_of"), actor=request.user, request=request, source_channel="PORTAL")
        return Response({"data": WithdrawalRequestSerializer(withdrawal).data}, status=201)


class PartnerPortalWithdrawalDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, withdrawal_id):
        withdrawal = WithdrawalRequest.objects.filter(pk=withdrawal_id, policy__partner__in=request.user.visible_partners()).select_related("policy", "policy__partner").first()
        if withdrawal is None:
            raise not_found(withdrawal_id)
        return Response({"data": _portal_payload(withdrawal, include_sensitive=_include_sensitive(request))})
