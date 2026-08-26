from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import not_found
from .models import Policy
from .permissions import HasOLPolicyPermission
from .services.integration_service import (
    apply_claim_settled,
    claim_registration_data,
    policy_dashboard_hooks,
    reinsurance_risk_data,
)


def _portal_payload(policy, *, include_sensitive=False):
    payload = {
        "policy_number": policy.policy_number,
        "status": policy.get_status_display(),
        "product_plan": policy.product_plan_ref,
        "risk_commencement_date": policy.risk_commencement_date,
        "maturity_date": policy.maturity_date,
        "currency": policy.currency,
    }
    if include_sensitive:
        payload.update(
            {
                "sum_assured": str(policy.sum_assured),
                "premium_amount": str(policy.premium_amount),
                "premium_frequency": policy.premium_frequency,
            }
        )
    return payload


class PolicyClaimRegistrationDataView(APIView):
    action = "retrieve"
    permission_classes = [HasOLPolicyPermission]

    def get(self, request, policy_id):
        return Response({"data": claim_registration_data(policy_id, actor=request.user)})


class PolicyReinsuranceRiskView(APIView):
    action = "retrieve"
    permission_classes = [HasOLPolicyPermission]

    def get(self, request, policy_id):
        return Response({"data": reinsurance_risk_data(policy_id, actor=request.user)})


class PolicyClaimSettledWebhookView(APIView):
    action = "service"
    permission_classes = [HasOLPolicyPermission]

    def post(self, request):
        policy, changed = apply_claim_settled(
            policy_id=request.data.get("policy_id"),
            claim_id=request.data.get("claim_id", ""),
            claim_type=request.data.get("claim_type", ""),
            settlement_amount=request.data.get("settlement_amount"),
            exhausted=request.data.get("exhausted", False),
            actor=request.user,
            request=request,
            source_channel="EVENT",
        )
        return Response({"data": {"changed": changed, "policy_id": str(policy.pk), "policy_number": policy.policy_number, "status": policy.status}})


class PolicyPortalListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        partners = request.user.visible_partners()
        policies = Policy.objects.filter(partner__in=partners).select_related("partner").order_by("-created_at")
        return Response({"data": {"count": policies.count(), "results": [_portal_payload(policy) for policy in policies]}})


class PolicyPortalDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, policy_id):
        policy = Policy.objects.filter(pk=policy_id, partner__in=request.user.visible_partners()).first()
        if policy is None:
            raise not_found(policy_id)
        include_sensitive = bool(
            getattr(request.user, "is_superuser", False)
            or getattr(request.user, "has_permission", lambda _code: False)("ol_policies.portal_sensitive")
        )
        return Response({"data": _portal_payload(policy, include_sensitive=include_sensitive)})


class PolicyDashboardHooksView(APIView):
    action = "retrieve"
    permission_classes = [HasOLPolicyPermission]

    def get(self, request):
        return Response({"data": policy_dashboard_hooks()})
