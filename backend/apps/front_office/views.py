from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from .models import (
    FOReceipt,
    FOCommission,
    FOCommissionStatement,
    FORequisition,
    FOPayment,
    FOParameter,
)
from .serializers import (
    FOReceiptSerializer,
    FOCommissionSerializer,
    FOCommissionStatementSerializer,
    FORequisitionSerializer,
    FOPaymentSerializer,
    FOParameterSerializer,
)

class FOReceiptViewSet(viewsets.ModelViewSet):
    queryset = FOReceipt.objects.all()
    serializer_class = FOReceiptSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["receipt_number", "reference", "payment_method"]
    filterset_fields = ["status", "payment_method"]
    ordering_fields = ["created_at", "payment_date", "amount"]

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
