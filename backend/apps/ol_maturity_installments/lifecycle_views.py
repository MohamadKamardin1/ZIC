from rest_framework.response import Response
from rest_framework.views import APIView

from .models import InstallmentSourceChannel
from .permissions import HasOLMaturityInstallmentPermission
from .serializers import OLInstallmentItemSerializer, OLMaturityInstallmentPlanDetailSerializer
from .services.lifecycle import cancel_installment_plan, reverse_item_payment


def _source_channel(request):
    requested = str(request.META.get("HTTP_X_SOURCE_CHANNEL", "API")).strip().upper()
    return requested if requested in InstallmentSourceChannel.values else InstallmentSourceChannel.API


class InstallmentItemReversePaymentView(APIView):
    permission_classes = [HasOLMaturityInstallmentPermission]
    action = "process_payment"

    def post(self, request, item_id):
        item, requisition = reverse_item_payment(
            item_id=item_id,
            reason=request.data.get("reason", ""),
            actor=request.user,
            request=request,
            source_channel=_source_channel(request),
        )
        return Response(
            {
                "success": True,
                "status_code": 200,
                "message": "Installment payment reversed successfully.",
                "data": {
                    "item": OLInstallmentItemSerializer(item, context={"request": request}).data,
                    "requisition": {
                        "requisition_number": requisition.requisition_number if requisition else None,
                        "status": requisition.status if requisition else None,
                    },
                },
            },
            status=200,
        )


class InstallmentPlanCancelView(APIView):
    permission_classes = [HasOLMaturityInstallmentPermission]
    action = "cancel"

    def post(self, request, plan_id):
        plan = cancel_installment_plan(
            plan_id=plan_id,
            reason=request.data.get("reason", ""),
            actor=request.user,
            request=request,
            source_channel=_source_channel(request),
        )
        return Response(
            {
                "success": True,
                "status_code": 200,
                "message": "Maturity installment plan cancelled successfully.",
                "data": {
                    "plan": OLMaturityInstallmentPlanDetailSerializer(plan, context={"request": request}).data,
                },
            },
            status=200,
        )
