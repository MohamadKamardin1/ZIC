from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import HasOLClaimPermission
from .services.loan_offset import calculate_net_payout


class ClaimFinancialSummaryView(APIView):
    permission_classes = [HasOLClaimPermission]
    action = "view"

    def get(self, request, claim_id):
        summary = calculate_net_payout(claim_id)
        return Response({"data": summary})
