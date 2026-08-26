from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import not_found
from .models import MaturityClaim, Policy
from .permissions import HasOLPolicyPermission
from .serializers import MaturityClaimSerializer, PolicyDetailSerializer
from .services.maturity_service import approve_maturity_claim, create_maturity_claim, pay_maturity_claim


class PolicyMaturityView(APIView):
    permission_classes = [HasOLPolicyPermission]

    def get_permissions(self):
        self.action = "service" if self.request.method == "POST" else "retrieve"
        return super().get_permissions()

    def get(self, request, policy_id):
        if not Policy.objects.filter(pk=policy_id).exists():
            raise not_found(policy_id)
        claims = MaturityClaim.objects.filter(policy_id=policy_id).order_by("-claim_date", "-created_at")
        return Response({"data": MaturityClaimSerializer(claims, many=True).data})

    def post(self, request, policy_id):
        policy = Policy.objects.filter(pk=policy_id).first()
        if not policy:
            raise not_found(policy_id)
        claim, created = create_maturity_claim(
            policy,
            as_of=request.data.get("as_of"),
            actor=request.user,
            request=request,
            source_channel="API",
        )
        if claim is None:
            return Response({"data": {"created": False, "claim": None, "policy": PolicyDetailSerializer(policy).data}})
        return Response(
            {"data": {"created": created, "claim": MaturityClaimSerializer(claim).data, "policy": PolicyDetailSerializer(claim.policy).data}},
            status=201 if created else 200,
        )


class PolicyMaturityApproveView(APIView):
    action = "service"
    permission_classes = [HasOLPolicyPermission]

    def post(self, request, claim_id):
        claim = approve_maturity_claim(
            claim_id,
            documents_verified=request.data.get("documents_verified", False),
            actor=request.user,
            request=request,
            source_channel="API",
        )
        return Response({"data": MaturityClaimSerializer(claim).data})


class PolicyMaturityPayView(APIView):
    action = "service"
    permission_classes = [HasOLPolicyPermission]

    def post(self, request, claim_id):
        claim = pay_maturity_claim(
            claim_id,
            payment_reference=request.data.get("payment_reference", ""),
            actor=request.user,
            request=request,
            source_channel="API",
        )
        return Response({"data": MaturityClaimSerializer(claim).data})
