from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import HasOLClaimPermission
from .serializers import OLClaimRequisitionSerializer
from .services.requisition import normalize_source_channel, raise_requisition


class ClaimRaiseRequisitionView(APIView):
    permission_classes = [HasOLClaimPermission]
    action = "requisition"

    def post(self, request, claim_id):
        requisition = raise_requisition(
            claim_id,
            bank_details=request.data.get("bank_details"),
            narration=request.data.get("narration"),
            actor=request.user,
            request=request,
            source_channel=normalize_source_channel(request.headers.get("X-Source-Channel", "API")),
        )
        return Response({"data": OLClaimRequisitionSerializer(requisition).data}, status=201)
