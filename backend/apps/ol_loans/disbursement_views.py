from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import has_ol_loan_permission
from .serializers import (
    OLLoanDisbursementRequestSerializer,
    OLLoanDisbursementSerializer,
    OLLoanListSerializer,
    OLLoanScheduleSerializer,
)
from .services.disbursement_service import disburse_loan


class MustDisburseOLLoanPermission(IsAuthenticated):
    def has_permission(self, request, view):
        return bool(super().has_permission(request, view) and has_ol_loan_permission(request.user, "disburse"))


class OLLoanDisburseView(APIView):
    permission_classes = [MustDisburseOLLoanPermission]

    def post(self, request, loan_id):
        serializer = OLLoanDisbursementRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = disburse_loan(
            loan_id,
            payment_mode=serializer.validated_data["payment_mode"],
            bank_account_code=serializer.validated_data.get("bank_account_code", ""),
            as_of=serializer.validated_data.get("as_of"),
            reason=serializer.validated_data.get("reason", ""),
            idempotency_key=request.headers.get("X-Idempotency-Key", ""),
            actor=request.user,
            request=request,
            source_channel="API",
        )
        return Response(
            {
                "data": {
                    "loan": OLLoanListSerializer(result.loan, context={"request": request}).data,
                    "disbursement": OLLoanDisbursementSerializer(result.disbursement).data,
                    "schedules": OLLoanScheduleSerializer(result.schedules, many=True).data,
                },
                "meta": {
                    "changed": result.changed,
                    "idempotent_replay": not result.changed,
                    "schedule_count": len(result.schedules),
                },
            },
            status=201 if result.changed else 200,
        )
