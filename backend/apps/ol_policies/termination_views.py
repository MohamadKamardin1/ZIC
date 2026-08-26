from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import HasOLPolicyPermission
from .serializers import PolicyDetailSerializer, SurrenderRequestSerializer
from .services.termination_service import cancel_policy, convert_policy_to_paid_up, request_policy_surrender


class PolicySurrenderView(APIView):
    action = "service"
    permission_classes = [HasOLPolicyPermission]

    def post(self, request, policy_id):
        surrender, created = request_policy_surrender(
            policy_id,
            as_of=request.data.get("as_of"),
            actor=request.user,
            request=request,
            source_channel="API",
        )
        surrender.policy.refresh_from_db()
        return Response(
            {
                "data": {
                    "surrender_request": SurrenderRequestSerializer(surrender).data,
                    "policy": PolicyDetailSerializer(surrender.policy).data,
                    "created": created,
                }
            },
            status=201 if created else 200,
        )


class PolicyPaidUpView(APIView):
    action = "service"
    permission_classes = [HasOLPolicyPermission]

    def post(self, request, policy_id):
        policy = convert_policy_to_paid_up(
            policy_id,
            as_of=request.data.get("as_of"),
            actor=request.user,
            request=request,
            source_channel="API",
        )
        return Response({"data": PolicyDetailSerializer(policy).data})


class PolicyCancelView(APIView):
    action = "cancel"
    permission_classes = [HasOLPolicyPermission]

    def post(self, request, policy_id):
        policy, requisition = cancel_policy(
            policy_id,
            reason=request.data.get("reason", ""),
            as_of=request.data.get("as_of"),
            actor=request.user,
            request=request,
            source_channel="API",
        )
        return Response(
            {
                "data": {
                    "policy": PolicyDetailSerializer(policy).data,
                    "refund": {
                        "amount": policy.contract_snapshot.get("cancellation", {}).get("refund_amount", "0.00"),
                        "within_free_look": policy.contract_snapshot.get("cancellation", {}).get("within_free_look", False),
                        "requisition_number": requisition.requisition_number if requisition else None,
                    },
                }
            }
        )
