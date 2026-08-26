from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import registry_error
from .permissions import HasOLPolicyPermission
from .serializers import PolicyDetailSerializer
from .services.issuance_service import issue_policy_from_proposal


class PolicyIssueView(APIView):
    """POST /api/v1/ol/policies/issue/ — atomically issue a policy from a proposal."""

    action = "create"
    permission_classes = [HasOLPolicyPermission]

    def post(self, request):
        proposal_id = request.data.get("proposal_id")
        if not proposal_id:
            raise registry_error(
                "POLICY_ISSUANCE_INVALID",
                message="A proposal_id is required to issue a policy.",
                field_errors={"proposal_id": ["Provide the proposal identifier to issue."]},
                resolution_steps=[
                    "Select an eligible proposal.",
                    "Submit its proposal_id in the request body.",
                ],
            )

        policy, created = issue_policy_from_proposal(
            proposal_id,
            actor=request.user,
            request=request,
            source_channel="API",
        )
        return Response(
            {
                "data": {
                    "policy": PolicyDetailSerializer(policy).data,
                    "created": created,
                    "idempotent": not created,
                }
            },
            status=201 if created else 200,
        )
