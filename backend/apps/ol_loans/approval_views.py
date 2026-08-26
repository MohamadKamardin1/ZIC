from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import has_ol_loan_permission
from .serializers import (
    OLLoanApprovalSerializer,
    OLLoanBulkActionSerializer,
    OLLoanListSerializer,
    OLLoanRejectionSerializer,
)
from .services.approval_service import approve_loan, bulk_approve, bulk_reject, reject_loan


class MustApproveOLLoanPermission(IsAuthenticated):
    def has_permission(self, request, view):
        return bool(super().has_permission(request, view) and has_ol_loan_permission(request.user, "approve"))


class OLLoanApproveView(APIView):
    permission_classes = [MustApproveOLLoanPermission]

    def post(self, request, loan_id):
        serializer = OLLoanApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = approve_loan(
            loan_id,
            actor=request.user,
            request=request,
            reason=serializer.validated_data.get("reason", ""),
            source_channel="API",
        )
        return Response({"data": OLLoanListSerializer(result.loan).data, "meta": {"changed": result.changed}})


class OLLoanRejectView(APIView):
    permission_classes = [MustApproveOLLoanPermission]

    def post(self, request, loan_id):
        serializer = OLLoanRejectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = reject_loan(
            loan_id,
            reason=serializer.validated_data.get("reason", ""),
            actor=request.user,
            request=request,
            source_channel="API",
        )
        return Response({"data": OLLoanListSerializer(result.loan).data, "meta": {"changed": result.changed}})


class OLLoanBulkApproveView(APIView):
    permission_classes = [MustApproveOLLoanPermission]

    def post(self, request):
        serializer = OLLoanBulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        results, errors = bulk_approve(
            serializer.validated_data["loan_ids"], actor=request.user, request=request, source_channel="API"
        )
        return Response({"data": {"results": results, "errors": errors, "count": len(results), "error_count": len(errors)}})


class OLLoanBulkRejectView(APIView):
    permission_classes = [MustApproveOLLoanPermission]

    def post(self, request):
        serializer = OLLoanBulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        results, errors = bulk_reject(
            serializer.validated_data["loan_ids"],
            reason=serializer.validated_data.get("reason", ""),
            actor=request.user,
            request=request,
            source_channel="API",
        )
        return Response({"data": {"results": results, "errors": errors, "count": len(results), "error_count": len(errors)}})
