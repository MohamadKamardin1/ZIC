from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.documents.models import DocumentInstance
from apps.documents.services.engine import DocumentEngine, DocumentEngineError

from .models import (
    FOCommission,
    FOCommissionStatement,
    FOParameter,
    FOPayment,
    FOReceipt,
    FORequisition,
)
from .serializers import (
    FOCommissionSerializer,
    FOCommissionStatementSerializer,
    FOParameterSerializer,
    FOPaymentSerializer,
    FOReceiptSerializer,
    FORequisitionSerializer,
)


class FOReceiptViewSet(viewsets.ModelViewSet):
    queryset = FOReceipt.objects.all()
    serializer_class = FOReceiptSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["receipt_number", "reference", "payment_method"]
    filterset_fields = ["status", "payment_method"]
    ordering_fields = ["created_at", "payment_date", "amount"]

    @action(detail=True, methods=["post"], url_path="print")
    def print_document(self, request, pk=None):
        receipt = self.get_object()
        try:
            instance = DocumentEngine.render(
                document_type="RECEIPT",
                object_id=receipt.pk,
                actor=request.user,
                request=request,
            )
        except DocumentEngineError as exc:
            return Response(
                {
                    "success": False,
                    "status_code": exc.status_code,
                    "code": exc.code,
                    "message": str(exc),
                    "resolution_steps": exc.resolution_steps,
                },
                status=exc.status_code,
            )
        document = DocumentEngine.payload(instance, request=request, actor=request.user, signed=True)
        return Response(
            {
                "success": True,
                "status_code": status.HTTP_201_CREATED,
                "message": "Receipt document rendered successfully.",
                "data": {"receipt": FOReceiptSerializer(receipt).data, "document": document},
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="documents")
    def documents(self, request, pk=None):
        receipt = self.get_object()
        rows = DocumentInstance.objects.select_related("template", "generated_by").filter(
            document_type="RECEIPT",
            source_app_label="front_office",
            source_model="foreceipt",
            source_object_id=str(receipt.pk),
        ).order_by("-generated_at", "-created_at")
        results = [DocumentEngine.payload(row, request=request, actor=request.user, signed=True) for row in rows]
        return Response(
            {
                "success": True,
                "status_code": status.HTTP_200_OK,
                "message": "Receipt documents retrieved.",
                "data": {"count": len(results), "page": 1, "page_size": len(results), "results": results},
            }
        )

class FOCommissionViewSet(viewsets.ModelViewSet):
    queryset = FOCommission.objects.all()
    serializer_class = FOCommissionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["agent_id", "policy_reference"]
    filterset_fields = ["status", "agent_id"]
    ordering_fields = ["created_at", "amount"]

class FOCommissionStatementViewSet(viewsets.ModelViewSet):
    queryset = FOCommissionStatement.objects.all()
    serializer_class = FOCommissionStatementSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["agent_id"]
    filterset_fields = ["status", "agent_id"]
    ordering_fields = ["created_at", "period_start", "total_amount"]

class FORequisitionViewSet(viewsets.ModelViewSet):
    queryset = FORequisition.objects.all()
    serializer_class = FORequisitionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["requisition_number", "department", "reason"]
    filterset_fields = ["status", "department"]
    ordering_fields = ["created_at", "amount"]

class FOPaymentViewSet(viewsets.ModelViewSet):
    queryset = FOPayment.objects.all()
    serializer_class = FOPaymentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["payment_number", "recipient", "payment_method"]
    filterset_fields = ["status", "payment_method"]
    ordering_fields = ["created_at", "payment_date", "amount"]

class FOParameterViewSet(viewsets.ModelViewSet):
    queryset = FOParameter.objects.all()
    serializer_class = FOParameterSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["key", "value", "description"]
    ordering_fields = ["key", "created_at"]
