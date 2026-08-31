from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import MaturityInstallmentError
from .models import InstallmentSourceChannel
from .permissions import HasOLMaturityInstallmentPermission
from .serializers import OLMaturityInstallmentPlanDetailSerializer
from .services.creation import create_installment_plan


class InstallmentPlanCreateInputSerializer(serializers.Serializer):
    policy_id = serializers.UUIDField()
    maturity_claim_id = serializers.UUIDField(required=False, allow_null=True)
    frequency = serializers.CharField()
    term_years = serializers.IntegerField(min_value=1)


class InstallmentPlanCreateView(APIView):
    permission_classes = [HasOLMaturityInstallmentPermission]
    action = "create"

    def post(self, request):
        serializer = InstallmentPlanCreateInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise MaturityInstallmentError(
                message="The maturity installment plan form needs correction before it can be created.",
                error_code="INSTALLMENT_INVALID_CREATION",
                status_code=400,
                field_errors=serializer.errors,
                resolution_steps=[
                    "Correct each highlighted plan field.",
                    "Select a matured policy and a supported frequency and term before retrying.",
                ],
            )

        requested_channel = str(request.META.get("HTTP_X_SOURCE_CHANNEL", "API")).strip().upper()
        source_channel = (
            requested_channel if requested_channel in InstallmentSourceChannel.values else InstallmentSourceChannel.API
        )
        plan, created = create_installment_plan(
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
                "message": "Maturity installment plan created successfully."
                if created
                else "The original maturity installment plan was returned safely.",
                "data": OLMaturityInstallmentPlanDetailSerializer(plan, context={"request": request}).data,
            },
            status=201 if created else 200,
        )
