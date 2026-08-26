from rest_framework import serializers

from .models import (
    FOCommission,
    FOCommissionStatement,
    FOParameter,
    FOPayment,
    FOReceipt,
    FORequisition,
)


class FOReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = FOReceipt
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

class FOCommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FOCommission
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

class FOCommissionStatementSerializer(serializers.ModelSerializer):
    class Meta:
        model = FOCommissionStatement
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

class FORequisitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FORequisition
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

class FOPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FOPayment
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

class FOParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = FOParameter
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
