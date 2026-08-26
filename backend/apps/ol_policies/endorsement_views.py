from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import not_found, registry_error
from .models import Policy, PolicyEndorsement
from .permissions import HasOLPolicyPermission
from .serializers import PolicyEndorsementSerializer
from .services.endorsement_service import create_policy_endorsement


class PolicyEndorsementListCreateView(APIView):
    permission_classes = [HasOLPolicyPermission]

    def get_permissions(self):
        self.action = "endorse" if self.request.method == "POST" else "retrieve"
        return super().get_permissions()

    def get(self, request, policy_id):
        if not Policy.objects.filter(pk=policy_id).exists():
            raise not_found(policy_id)
        endorsements = PolicyEndorsement.objects.filter(policy_id=policy_id).order_by("-effective_date", "-created_at")
        return Response({"data": PolicyEndorsementSerializer(endorsements, many=True).data})

    def post(self, request, policy_id):
        payload = request.data
        endorsement_type = payload.get("endorsement_type") or payload.get("type")
        changes = payload.get("changes")
        if changes is None:
            changes = {
                key: value
                for key, value in payload.items()
                if key not in {"endorsement_type", "type", "effective_date", "description", "reason"}
            }
        if not endorsement_type:
            raise registry_error(
                "POLICY_ENDORSEMENT_INVALID",
                message="An endorsement_type is required.",
                field_errors={"endorsement_type": ["Choose the type of policy change to apply."]},
            )
        endorsement, commitment = create_policy_endorsement(
            policy_id,
            endorsement_type=endorsement_type,
            changes=changes,
            effective_date=payload.get("effective_date"),
            description=payload.get("description") or payload.get("reason") or "",
            actor=request.user,
            request=request,
            source_channel="API",
        )
        return Response(
            {
                "data": {
                    "endorsement": PolicyEndorsementSerializer(endorsement).data,
                    "commitment": {
                        "commitment_number": commitment.commitment_number,
                        "amount": commitment.premium_amount,
                        "status": commitment.status,
                    }
                    if commitment
                    else None,
                }
            },
            status=201,
        )


class PolicyEndorsementDetailView(APIView):
    action = "retrieve"
    permission_classes = [HasOLPolicyPermission]

    def get(self, request, policy_id, endorsement_id):
        endorsement = (
            PolicyEndorsement.objects.filter(policy_id=policy_id, pk=endorsement_id)
            .select_related("policy")
            .first()
        )
        if not endorsement:
            raise registry_error(
                "POLICY_ENDORSEMENT_INVALID",
                message="The requested policy endorsement was not found.",
                details={"policy_id": str(policy_id), "endorsement_id": str(endorsement_id)},
                resolution_steps=["Refresh the policy history and select an existing endorsement."],
            )
        return Response({"data": PolicyEndorsementSerializer(endorsement).data})
