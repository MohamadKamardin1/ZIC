from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import ClaimError
from .models import ClaimSourceChannel
from .permissions import HasOLClaimPermission
from .serializers import OLClaimDetailSerializer
from .services.registration import ClaimRegistrationService


class ClaimRegistrationInputSerializer(serializers.Serializer):
    claim_type = serializers.CharField(max_length=80)
    claim_date = serializers.DateField()
    cause_of_claim = serializers.CharField(required=False, allow_blank=True, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    member_id = serializers.UUIDField(required=False, allow_null=True)
    claimant_details = serializers.JSONField(required=False, allow_null=True)
    benefit_type = serializers.CharField(required=False, allow_blank=True, max_length=100)

    def validate_claim_type(self, value):
        value = value.strip().upper()
        if not value:
            raise serializers.ValidationError("Select a configured claim type.")
        return value

    def validate_claimant_details(self, value):
        if value is not None and not isinstance(value, dict):
            raise serializers.ValidationError("Claimant details must be a JSON object.")
        return value or {}


class ClaimRegistrationView(APIView):
    permission_classes = [HasOLClaimPermission]
    action = "register"

    def post(self, request, policy_id):
        serializer = ClaimRegistrationInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise ClaimError(
                message="The claim registration form needs correction before it can be submitted.",
                error_code="CLAIM_INVALID_REGISTRATION",
                status_code=400,
                field_errors=serializer.errors,
                resolution_steps=[
                    "Correct each highlighted claim field.",
                    "Select a configured claim type and provide claimant information before retrying.",
                ],
            )

        requested_channel = str(request.META.get("HTTP_X_SOURCE_CHANNEL", "API")).strip().upper()
        source_channel = requested_channel if requested_channel in ClaimSourceChannel.values else ClaimSourceChannel.API
        claim, created = ClaimRegistrationService.register(
            policy_id=policy_id,
            actor=request.user,
            request=request,
            source_channel=source_channel,
            idempotency_key=request.META.get("HTTP_X_IDEMPOTENCY_KEY"),
            **serializer.validated_data,
        )
        return Response(
            {
                "success": True,
                "status_code": 201 if created else 200,
                "message": "Claim registered successfully." if created else "The original claim registration was returned safely.",
                "data": OLClaimDetailSerializer(claim).data,
            },
            status=201 if created else 200,
        )
