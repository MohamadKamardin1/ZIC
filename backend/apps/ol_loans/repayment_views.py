from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import has_ol_loan_permission
from .serializers import OLLoanListSerializer, OLLoanRepaymentSerializer, OLLoanRepaymentRequestSerializer
from .services.repayment_service import repay_loan


class MustRepayOLLoanPermission(IsAuthenticated):
    def has_permission(self, request, view):
        return bool(super().has_permission(request, view) and has_ol_loan_permission(request.user, "repay"))


class OLLoanRepayView(APIView):
    permission_classes = [MustRepayOLLoanPermission]

    def post(self, request, loan_id):
        serializer = OLLoanRepaymentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = repay_loan(
            loan_id,
            amount=data["amount"],
            currency=data["currency"],
            payment_mode=data.get("payment_mode", ""),
            exchange_rate=data.get("exchange_rate"),
            receipt_ref=data.get("receipt_ref", ""),
            reason=data.get("reason", ""),
            payment_date=data.get("payment_date"),
            idempotency_key=request.headers.get("X-Idempotency-Key", ""),
            actor=request.user,
            request=request,
            source_channel="API",
        )
        return Response(
            {
                "data": {
                    "loan": OLLoanListSerializer(result.loan, context={"request": request}).data,
                    "repayment": OLLoanRepaymentSerializer(result.repayment).data,
                },
                "meta": {
                    "created": result.created,
                    "idempotent_replay": not result.created,
                    "allocation_breakdown": result.repayment.allocation_breakdown,
                },
            },
            status=201 if result.created else 200,
        )
