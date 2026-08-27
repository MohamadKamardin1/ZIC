from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import has_ol_loan_permission
from .serializers import OLLoanListSerializer, OLLoanOffsetRequestSerializer, OLLoanOffsetSerializer
from .services.default_service import process_loan_offset


class MustOffsetOLLoanPermission(IsAuthenticated):
    def has_permission(self, request, view):
        return bool(super().has_permission(request, view) and has_ol_loan_permission(request.user, "offset"))


class OLLoanOffsetView(APIView):
    """Apply an unsettled claim, surrender, or maturity payout against a loan."""

    permission_classes = [MustOffsetOLLoanPermission]

    def post(self, request, loan_id):
        serializer = OLLoanOffsetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = process_loan_offset(
            loan_id,
            source_type=data["source_type"],
            source_id=data["source_id"],
            payout_amount=data["payout_amount"],
            reason=data.get("reason", ""),
            actor=request.user,
            request=request,
            source_channel="API",
        )
        return Response(
            {
                "data": {
                    "loan": OLLoanListSerializer(result.loan, context={"request": request}).data,
                    "offset": OLLoanOffsetSerializer(result.offset).data,
                },
                "meta": {
                    "created": result.created,
                    "idempotent_replay": not result.created,
                    "remaining_payout": str(result.offset.remaining_payout),
                },
            },
            status=201 if result.created else 200,
        )
