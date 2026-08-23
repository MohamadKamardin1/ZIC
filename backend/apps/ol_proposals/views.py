from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ol_proposals.models import OLProposal
from apps.ol_proposals.permissions import has_ol_proposal_permission
from apps.ol_proposals.serializers import OLProposalBaseSerializer, OLProposalDetailSerializer


class MustViewProposalsPermission(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return has_ol_proposal_permission(request.user, "view")


class ProposalListView(APIView):
    """GET /api/v1/ol-proposals/ — paginated proposal list (names, never UUIDs)."""

    permission_classes = [MustViewProposalsPermission]

    def get(self, request):
        queryset = OLProposal.objects.select_related("quotation", "partner", "agent_partner", "employer_partner")
        status = request.query_params.get("status")
        if status:
            queryset = queryset.filter(status__iexact=status)
        search = request.query_params.get("search")
        if search:
            from django.db.models import Q

            queryset = queryset.filter(
                Q(proposal_number__icontains=search)
                | Q(partner_name_snapshot__icontains=search)
                | Q(agent_name_snapshot__icontains=search)
                | Q(quotation__quote_number__icontains=search)
            )
        ordering = request.query_params.get("ordering", "-created_at")
        queryset = queryset.order_by(ordering, "-created_at")

        page = max(1, int(request.query_params.get("page", 1)))
        page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
        total = queryset.count()
        start = (page - 1) * page_size
        rows = queryset[start:start + page_size]

        return Response(
            {
                "data": {
                    "results": OLProposalBaseSerializer(rows, many=True).data,
                    "count": total,
                    "page": page,
                    "page_size": page_size,
                    "next": page * page_size < total,
                    "previous": page > 1,
                }
            }
        )


class ProposalDetailView(APIView):
    """GET /api/v1/ol-proposals/{id}/ — proposal detail with carried children."""

    permission_classes = [MustViewProposalsPermission]

    def get(self, request, proposal_id):
        proposal = (
            OLProposal.objects.select_related("quotation", "partner", "agent_partner", "employer_partner", "converted_policy")
            .prefetch_related(
                "plan_configs",
                "members",
                "installment_configs__rate_rows",
                "fund_allocations",
                "riders",
                "benefits",
                "beneficiaries",
                "documents",
                "health_answers",
            )
            .filter(pk=proposal_id)
            .first()
        )
        if not proposal:
            from apps.ol_proposals.errors import ProposalError

            raise ProposalError(
                "The proposal could not be found.",
                error_code="PROPOSAL_NOT_FOUND",
                status_code=404,
                resolution_steps=["Verify the proposal number.", "Check the proposal register filters."],
            )
        return Response({"data": OLProposalDetailSerializer(proposal).data})