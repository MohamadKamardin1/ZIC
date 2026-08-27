from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import ClaimError
from .models import ClaimMedicalStatus, ClaimSourceChannel
from .permissions import HasOLClaimPermission
from .serializers import OLClaimDetailSerializer
from .services.medical import evaluate_medical_requirements, record_medical_result, require_medical_review
from .views import _base_queryset


def _source_channel(request):
    requested = str(request.META.get("HTTP_X_SOURCE_CHANNEL", "API")).strip().upper()
    return requested if requested in ClaimSourceChannel.values else ClaimSourceChannel.API


def _claim(claim_id):
    claim = _base_queryset().filter(pk=claim_id).first()
    if not claim:
        from .errors import not_found
        raise not_found()
    return claim


class MedicalResultInputSerializer(serializers.Serializer):
    result = serializers.CharField(max_length=30)
    reason = serializers.CharField(required=False, allow_blank=True)
    loading_factor = serializers.DecimalField(max_digits=8, decimal_places=4, required=False, allow_null=True)
    loading_percentage = serializers.DecimalField(max_digits=8, decimal_places=4, required=False, allow_null=True)

    def validate_result(self, value):
        value = value.strip().upper()
        if value not in {ClaimMedicalStatus.CLEARED, ClaimMedicalStatus.REJECTED, ClaimMedicalStatus.LOADING}:
            raise serializers.ValidationError("Choose Cleared, Rejected, or Loading.")
        return value


class ClaimMedicalRequirementView(APIView):
    permission_classes = [HasOLClaimPermission]
    action = "assess"

    def post(self, request, claim_id):
        claim = _claim(claim_id)
        reason = str(request.data.get("reason", "")).strip()
        updated = require_medical_review(
            claim.pk,
            actor=request.user,
            reason=reason,
            source_channel=_source_channel(request),
        )
        return Response({"data": OLClaimDetailSerializer(updated).data})


class ClaimMedicalResultView(APIView):
    permission_classes = [HasOLClaimPermission]
    action = "assess"

    def post(self, request, claim_id):
        serializer = MedicalResultInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise ClaimError(
                message="The medical result needs correction before it can be recorded.",
                error_code="CLAIM_INVALID_MEDICAL_RESULT",
                status_code=400,
                field_errors=serializer.errors,
                resolution_steps=[
                    "Choose Cleared, Rejected, or Loading.",
                    "Provide a rejection reason or valid loading factor where applicable.",
                ],
            )
        _claim(claim_id)
        updated = record_medical_result(
            claim_id,
            actor=request.user,
            source_channel=_source_channel(request),
            **serializer.validated_data,
        )
        return Response({"data": OLClaimDetailSerializer(updated).data})


class ClaimMedicalEvaluationView(APIView):
    permission_classes = [HasOLClaimPermission]
    action = "assess"

    def post(self, request, claim_id):
        claim = _claim(claim_id)
        result = evaluate_medical_requirements(
            claim,
            actor=request.user,
            source_channel=_source_channel(request),
        )
        return Response({"data": {**result, "claim_number": claim.claim_number}})
