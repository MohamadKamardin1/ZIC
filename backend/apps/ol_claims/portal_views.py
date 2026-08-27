from datetime import date
from uuid import UUID

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ol_policies.models import Policy

from .errors import registry_error
from .models import OLClaim
from .serializers import OLClaimDetailSerializer, OLClaimListSerializer
from .services.registration import ClaimRegistrationService
from .views import _apply_claim_filters, _base_queryset, _paginate


PORTAL_REGISTRATION_FIELDS = {
    "policy_number",
    "claim_type",
    "claim_date",
    "cause_of_claim",
    "description",
    "member_id",
    "claimant_details",
    "benefit_type",
}


def _portal_error():
    return registry_error(
        "PORTAL_RESOURCE_NOT_FOUND",
        message="The requested claim or policy is not available in your partner portal.",
        resolution_steps=[
            "Confirm that the policy belongs to your linked partner profile.",
            "Use the policy or claim number shown in your portal records.",
        ],
    )


def _current_partner(request):
    return request.user.current_partner() if hasattr(request.user, "current_partner") else None


def _portal_claim_queryset(request):
    partner = _current_partner(request)
    if partner is None:
        return _base_queryset().none()
    return _base_queryset().filter(policy_ref__partner=partner)


class ClaimPortalListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = _apply_claim_filters(_portal_claim_queryset(request), request.query_params)
        page = _paginate(queryset, request)
        page["results"] = OLClaimListSerializer(
            page.pop("results"), many=True, context={"request": request}
        ).data
        return Response({"success": True, "data": page})


class ClaimPortalDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, claim_id):
        queryset = _portal_claim_queryset(request)
        claim = queryset.filter(claim_number__iexact=str(claim_id)).first()
        if claim is None:
            try:
                claim_uuid = UUID(str(claim_id))
            except (TypeError, ValueError, AttributeError):
                claim_uuid = None
            if claim_uuid is not None:
                claim = queryset.filter(pk=claim_uuid).first()
        if claim is None:
            raise _portal_error()
        return Response({"success": True, "data": OLClaimDetailSerializer(claim, context={"request": request}).data})


class ClaimPortalRegistrationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        partner = _current_partner(request)
        if partner is None:
            raise _portal_error()
        unknown = set(request.data.keys()) - PORTAL_REGISTRATION_FIELDS
        if unknown:
            raise registry_error(
                "CLAIM_INVALID_REGISTRATION",
                field_errors={field: ["This field is not accepted through the partner portal."] for field in sorted(unknown)},
                resolution_steps=[
                    "Remove staff-only fields from the portal submission.",
                    "Submit policy number, claim type, claim date, claimant details, and the claim narrative.",
                ],
            )
        policy_number = str(request.data.get("policy_number") or "").strip()
        policy = Policy.objects.filter(
            policy_number__iexact=policy_number,
            partner=partner,
            status__in={"ACTIVE", "PAID_UP"},
        ).first()
        if policy is None:
            raise _portal_error()
        try:
            claim_date = date.fromisoformat(str(request.data.get("claim_date") or ""))
        except (TypeError, ValueError):
            raise registry_error(
                "CLAIM_INVALID_REGISTRATION",
                field_errors={"claim_date": ["Enter the claim date using YYYY-MM-DD format."]},
                resolution_steps=["Correct the claim date and submit the portal form again."],
            )
        claim, created = ClaimRegistrationService.register(
            policy_id=policy.pk,
            claim_type=request.data.get("claim_type"),
            claim_date=claim_date,
            cause_of_claim=request.data.get("cause_of_claim", ""),
            description=request.data.get("description", ""),
            member_id=request.data.get("member_id"),
            claimant_details=request.data.get("claimant_details"),
            benefit_type=request.data.get("benefit_type", ""),
            idempotency_key=request.headers.get("X-Idempotency-Key", ""),
            actor=request.user,
            source_channel="PORTAL",
            request=request,
        )
        return Response(
            {
                "success": True,
                "data": OLClaimDetailSerializer(claim, context={"request": request}).data,
                "meta": {"created": created, "idempotent_replay": not created},
            },
            status=201 if created else 200,
        )
