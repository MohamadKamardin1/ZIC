from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import HasOLClaimPermission
from .serializers import OLClaimDetailSerializer
from .services.requisition import normalize_source_channel
from .services.settlement import settle_claim


class ClaimSettlementView(APIView):
    permission_classes = [HasOLClaimPermission]
    action = "settle"

    def post(self, request, claim_id):
        claim, changed = settle_claim(
            claim_id,
            payment_reference=request.data.get("payment_reference"),
            payment_status=request.data.get("payment_status", "CONFIRMED"),
            actor=request.user,
            request=request,
            source_channel=normalize_source_channel(request.headers.get("X-Source-Channel", "API")),
        )
        return Response({"data": {"changed": changed, "claim": OLClaimDetailSerializer(claim).data}})
