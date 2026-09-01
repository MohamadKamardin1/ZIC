from rest_framework.response import Response
from rest_framework.views import APIView

from .models import InstallmentSourceChannel
from .permissions import HasOLMaturityInstallmentPermission
from .services.reconciliation import validate_plan_reconciliation


def _source_channel(request):
    requested = str(request.META.get("HTTP_X_SOURCE_CHANNEL", "API")).strip().upper()
    return requested if requested in InstallmentSourceChannel.values else InstallmentSourceChannel.API


class InstallmentPlanReconciliationView(APIView):
    permission_classes = [HasOLMaturityInstallmentPermission]
    action = "view"

    def get(self, request, plan_id):
        report = validate_plan_reconciliation(
            plan_id=plan_id,
            tolerance=request.query_params.get("tolerance"),
            actor=request.user,
            request=request,
            source_channel=_source_channel(request),
        )
        return Response(
            {
                "success": True,
                "status_code": 200,
                "message": "Plan reconciliation completed."
                if report.status == "PASS"
                else "Plan reconciliation found discrepancies.",
                "data": report.to_dict(),
            },
            status=200,
        )
