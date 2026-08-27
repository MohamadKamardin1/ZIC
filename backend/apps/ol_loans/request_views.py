from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import has_ol_loan_permission
from .serializers import OLLoanListSerializer, OLLoanRequestSerializer
from .services.request_service import get_policy_loan_eligibility, request_policy_loan


class MustRequestOLLoanPermission(IsAuthenticated):
    def has_permission(self, request, view):
        return bool(super().has_permission(request, view) and has_ol_loan_permission(request.user, "request"))


class PolicyLoanEligibilityView(APIView):
    """GET /api/v1/ol/policies/{policy_id}/loans/eligibility/."""

    permission_classes = [MustRequestOLLoanPermission]

    def get(self, request, policy_id):
        eligibility = get_policy_loan_eligibility(
            policy_id,
            as_of=request.query_params.get("as_of"),
            actor=request.user,
            request=request,
            source_channel="API",
        )
        return Response({"data": eligibility})


class PolicyLoanRequestView(APIView):
    """POST /api/v1/ol/policies/{policy_id}/loans/request/."""

    permission_classes = [MustRequestOLLoanPermission]

    def post(self, request, policy_id):
        serializer = OLLoanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = request_policy_loan(
            policy_id,
            requested_amount=serializer.validated_data["requested_amount"],
            term_months=serializer.validated_data["term_months"],
            repayment_mode=serializer.validated_data["repayment_mode"],
            reason=serializer.validated_data["reason"],
            idempotency_key=request.headers.get("X-Idempotency-Key", ""),
            as_of=serializer.validated_data.get("as_of"),
            actor=request.user,
            request=request,
            source_channel="API",
        )
        status_code = 201 if result.created else 200
        return Response(
            {
                "data": OLLoanListSerializer(result.loan).data,
                "meta": {
                    "created": result.created,
                    "idempotent_replay": not result.created,
                    "idempotency_key": result.loan.idempotency_key,
                },
            },
            status=status_code,
        )
