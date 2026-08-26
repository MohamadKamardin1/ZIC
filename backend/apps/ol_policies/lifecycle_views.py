from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import not_found
from .models import Policy
from .permissions import HasOLPolicyPermission
from .serializers import PolicyDetailSerializer
from .services.lifecycle_service import reinstate_policy


class PolicyReinstateView(APIView):
    action = "reinstate"
    permission_classes = [HasOLPolicyPermission]

    def post(self, request, policy_id):
        if not Policy.objects.filter(pk=policy_id).exists():
            raise not_found(policy_id)
        policy = reinstate_policy(
            policy_id,
            payment_amount=request.data.get("payment_amount", 0),
            medical_clearance=request.data.get("medical_clearance", False),
            actor=request.user,
            request=request,
            as_of=request.data.get("as_of"),
            source_channel="API",
        )
        return Response({"data": PolicyDetailSerializer(policy).data})
