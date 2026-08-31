from rest_framework.response import Response
from rest_framework.views import APIView

from .models import InstallmentSourceChannel
from .permissions import HasOLMaturityInstallmentPermission
from .serializers import OLInstallmentItemSerializer
from .services.payment import confirm_item_payment, process_item_payment


def _source_channel(request):
    requested = str(request.META.get("HTTP_X_SOURCE_CHANNEL", "API")).strip().upper()
    return requested if requested in InstallmentSourceChannel.values else InstallmentSourceChannel.API


def _requisition_data(requisition):
    return {
        "requisition_number": requisition.requisition_number,
        "status": requisition.status,
        "amount": str(requisition.amount),
        "department": requisition.department,
    }


class InstallmentItemProcessPaymentView(APIView):
    permission_classes = [HasOLMaturityInstallmentPermission]
    action = "process_payment"

    def post(self, request, item_id):
        item, requisition, created = process_item_payment(
            item_id=item_id,
            actor=request.user,
            request=request,
            source_channel=_source_channel(request),
        )
        return Response(
            {
                "success": True,
                "status_code": 201 if created else 200,
                "message": "Front Office payment requisition raised successfully."
                if created
                else "The existing payment requisition was returned safely.",
                "data": {
                    "item": OLInstallmentItemSerializer(item, context={"request": request}).data,
                    "requisition": _requisition_data(requisition),
                },
            },
            status=201 if created else 200,
        )


class InstallmentItemConfirmPaymentView(APIView):
    permission_classes = [HasOLMaturityInstallmentPermission]
    action = "process_payment"

    def post(self, request, item_id):
        item, plan_completed, confirmed = confirm_item_payment(
            item_id=item_id,
            actor=request.user,
            request=request,
            source_channel=_source_channel(request),
        )
        return Response(
            {
                "success": True,
                "status_code": 200,
                "message": "Installment payment confirmed as paid."
                if confirmed
                else "The installment was already confirmed as paid.",
                "data": {
                    "item": OLInstallmentItemSerializer(item, context={"request": request}).data,
                    "plan_completed": plan_completed,
                    "paid_date": str(item.paid_date) if item.paid_date else None,
                },
            },
            status=200,
        )
