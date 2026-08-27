from uuid import UUID

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ol_policies.models import Policy

from .models import OLLoan
from .permissions import has_ol_loan_permission
from .serializers import OLLoanPortalRequestSerializer
from .services.request_service import _resolve_product, request_policy_loan


def _portal_error(message, status_code=404):
    return Response(
        {
            "success": False,
            "status_code": status_code,
            "error_code": "PORTAL_RESOURCE_NOT_FOUND",
            "code": "PORTAL_RESOURCE_NOT_FOUND",
            "message": message,
            "resolution_steps": ["Confirm that the loan belongs to your linked partner profile."],
        },
        status=status_code,
    )


def _schedule_payload(loan):
    return [
        {
            "installment_number": row.installment_number,
            "due_date": row.due_date,
            "principal_due": str(row.principal_due),
            "interest_due": str(row.interest_due),
            "penalty_due": str(row.penalty_due),
            "amount_paid": str(row.amount_paid),
            "balance": str(row.balance),
            "status": row.get_status_display(),
        }
        for row in loan.schedules.all()
    ]


def _portal_payload(loan, *, detail=False):
    policy = loan.policy_ref
    snapshot = policy.contract_snapshot if isinstance(policy.contract_snapshot, dict) else {}
    product = _resolve_product(policy)
    payload = {
        "loan_number": loan.loan_number,
        "policy_number": getattr(policy, "policy_number", "Not recorded"),
        "policyholder": getattr(loan.partner, "legal_name", "") or getattr(loan.partner, "partner_number", "Policyholder"),
        "status": loan.get_status_display(),
        "currency": loan.currency,
        "principal_amount": str(loan.principal_amount),
        "disbursed_amount": str(loan.disbursed_amount),
        "outstanding_balance": str(loan.outstanding_balance),
        "interest_rate": str(loan.interest_rate),
        "term_months": loan.term_months,
        "repayment_mode": loan.repayment_mode,
        "disbursement_date": loan.disbursement_date,
        "maturity_date": loan.maturity_date,
        "product": snapshot.get("product_name") or snapshot.get("plan_name") or policy.product_plan_ref or "Not recorded",
        "request_allowed": bool(
            product.allow_loans
            if product is not None
            else snapshot.get("loan_request_allowed", snapshot.get("allow_loans", snapshot.get("allows_loans", False)))
        ),
    }
    if detail:
        payload.update(
            {
                "total_repaid": str(loan.total_repaid),
                "compounding_frequency": loan.compounding_frequency,
                "schedule": _schedule_payload(loan),
            }
        )
    return payload


class OLLoanPortalListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        partners = request.user.visible_partners()
        loans = (
            OLLoan.objects.filter(partner__in=partners)
            .select_related("partner", "policy_ref")
            .prefetch_related("schedules")
            .order_by("-created_at", "loan_number")
        )
        return Response(
            {
                "success": True,
                "data": {
                    "count": loans.count(),
                    "results": [_portal_payload(loan) for loan in loans],
                },
            }
        )


class MustRequestPortalLoanPermission(IsAuthenticated):
    def has_permission(self, request, view):
        return bool(super().has_permission(request, view) and has_ol_loan_permission(request.user, "request"))


class OLLoanPortalRequestView(APIView):
    permission_classes = [MustRequestPortalLoanPermission]

    def post(self, request):
        serializer = OLLoanPortalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        policy = (
            Policy.objects.filter(
                policy_number__iexact=data["policy_number"],
                partner__in=request.user.visible_partners(),
            )
            .select_related("partner")
            .first()
        )
        if policy is None:
            return _portal_error("The selected policy is not available in your partner portal.")
        result = request_policy_loan(
            policy.pk,
            requested_amount=data["requested_amount"],
            term_months=data["term_months"],
            repayment_mode=data["repayment_mode"],
            reason=data["reason"],
            idempotency_key=request.headers.get("X-Idempotency-Key", ""),
            as_of=data.get("as_of"),
            actor=request.user,
            request=request,
            source_channel="PORTAL",
        )
        return Response(
            {
                "success": True,
                "data": _portal_payload(result.loan),
                "meta": {"created": result.created, "idempotent_replay": not result.created},
            },
            status=201 if result.created else 200,
        )


class OLLoanPortalDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, loan_id):
        scoped_loans = (
            OLLoan.objects.filter(partner__in=request.user.visible_partners())
            .select_related("partner", "policy_ref")
            .prefetch_related("schedules")
        )
        loan = scoped_loans.filter(loan_number=str(loan_id)).first()
        if loan is None:
            try:
                loan_uuid = UUID(str(loan_id))
            except (TypeError, ValueError, AttributeError):
                loan_uuid = None
            if loan_uuid is not None:
                loan = scoped_loans.filter(pk=loan_uuid).first()
        if loan is None:
            return _portal_error("The requested loan is not available in your partner portal.")
        return Response({"success": True, "data": _portal_payload(loan, detail=True)})
