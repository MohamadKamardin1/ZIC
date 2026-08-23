from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ol_proposals.errors import ProposalError
from apps.ol_proposals.models import OLProposal
from apps.ol_proposals.permissions import has_ol_proposal_permission
from apps.ol_proposals.serializers import (
    OLProposalBaseSerializer,
    OLProposalBeneficiarySerializer,
    OLProposalDetailSerializer,
)


class MustViewProposalsPermission(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return has_ol_proposal_permission(request.user, "view")


class MustCreateProposalPermission(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return has_ol_proposal_permission(request.user, "create")


class ProposalFromQuotationView(APIView):
    """POST /api/v1/ol/proposals/from-quotation/{quotation_id}/ — idempotent BR-01 conversion."""

    permission_classes = [MustCreateProposalPermission]

    def post(self, request, quotation_id):
        from apps.ol_proposals.services.conversion_service import convert_quotation_to_proposal

        version_param = request.query_params.get("version") or request.query_params.get("version_number")
        version_number = None
        if version_param is not None:
            try:
                version_number = int(version_param)
            except (TypeError, ValueError):
                version_number = None

        from apps.ol_proposals.errors import ProposalError
        from apps.ol_quotations.models import OLQuotation

        quotation = OLQuotation.objects.filter(pk=quotation_id).first()
        if not quotation:
            raise ProposalError(
                "The quotation could not be found.",
                error_code="PROPOSAL_NOT_FOUND",
                status_code=404,
                resolution_steps=["Verify the quotation number."],
            )

        result = convert_quotation_to_proposal(
            quotation=quotation,
            actor=request.user,
            request=request,
            version_number=version_number,
            source_channel="API",
            notes=request.data.get("notes") or "",
        )
        payload = OLProposalBaseSerializer(result.proposal).data
        payload.update(
            {
                "created": result.created,
                "duplicate": result.duplicate,
                "already_converted": result.duplicate and result.proposal.status == "CONVERTED",
            }
        )
        return Response({"data": payload}, status=201 if result.created else 200)



class MustEnrichProposalPermission(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return has_ol_proposal_permission(request.user, "enrich")


def _get_proposal(proposal_id):
    proposal = (
        OLProposal.objects.select_related("quotation", "partner", "agent_partner", "employer_partner", "converted_policy")
        .prefetch_related("beneficiaries")
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
    return proposal


def _partner_label(partner):
    values = [
        partner.legal_name or "",
        partner.company_name or "",
        f"{partner.first_name or ''} {partner.surname or ''}".strip(),
    ]
    return next((value for value in values if value), partner.partner_number or "")


def missing_sections_for(proposal):
    from apps.ol_proposals.services.enrichment_service import missing_sections

    return missing_sections(proposal)


class ProposalEnrichView(APIView):
    """PATCH /api/v1/ol-proposals/{id}/enrich/ — apply enrichment sections."""

    permission_classes = [MustEnrichProposalPermission]

    def patch(self, request, proposal_id):
        from apps.ol_proposals.services.enrichment_service import apply_section

        proposal = _get_proposal(proposal_id)
        provided = [key for key in ("employer", "intermediary", "declarations", "bank_details") if key in request.data]
        if not provided:
            raise ProposalError(
                "No enrichment section was provided.",
                error_code="VALIDATION_ERROR",
                status_code=422,
                resolution_steps=["Send one or more sections: employer, intermediary, declarations, bank_details."],
            )
        for section in provided:
            apply_section(proposal=proposal, section=section, data=request.data.get(section) or {}, actor=request.user, request=request, source_channel="API")
        proposal.refresh_from_db()
        payload = OLProposalDetailSerializer(proposal).data
        payload["completeness"] = missing_sections_for(proposal)
        return Response({"data": payload})


class ProposalBeneficiaryCollectionView(APIView):
    """POST/PUT /api/v1/ol-proposals/{id}/beneficiaries/"""

    permission_classes = [MustEnrichProposalPermission]

    def post(self, request, proposal_id):
        from apps.ol_proposals.services.enrichment_service import add_beneficiary

        proposal = _get_proposal(proposal_id)
        beneficiary = add_beneficiary(proposal=proposal, data=request.data, actor=request.user, request=request, source_channel="API")
        return Response({"data": OLProposalBeneficiarySerializer(beneficiary).data}, status=201)

    def put(self, request, proposal_id):
        from apps.ol_proposals.services.enrichment_service import replace_beneficiaries

        proposal = _get_proposal(proposal_id)
        items = request.data.get("beneficiaries") if isinstance(request.data, dict) else request.data
        if not isinstance(items, list):
            raise ProposalError(
                "A beneficiaries array is required.",
                error_code="VALIDATION_ERROR",
                status_code=422,
                field_errors={"beneficiaries": ["Provide a list of beneficiary objects."]},
            )
        created = replace_beneficiaries(proposal=proposal, items=items, actor=request.user, request=request, source_channel="API")
        return Response({"data": {"results": OLProposalBeneficiarySerializer(created, many=True).data}})


class ProposalBeneficiaryItemView(APIView):
    """PATCH/DELETE /api/v1/ol-proposals/{id}/beneficiaries/{beneficiary_id}/"""

    permission_classes = [MustEnrichProposalPermission]

    def patch(self, request, proposal_id, beneficiary_id):
        from apps.ol_proposals.services.enrichment_service import update_beneficiary

        proposal = _get_proposal(proposal_id)
        beneficiary = update_beneficiary(proposal=proposal, beneficiary_id=beneficiary_id, data=request.data, actor=request.user, request=request, source_channel="API")
        return Response({"data": OLProposalBeneficiarySerializer(beneficiary).data})

    def delete(self, request, proposal_id, beneficiary_id):
        from apps.ol_proposals.services.enrichment_service import remove_beneficiary

        proposal = _get_proposal(proposal_id)
        remove_beneficiary(proposal=proposal, beneficiary_id=beneficiary_id, actor=request.user, request=request, source_channel="API")
        return Response({"data": {"deleted": True, "completeness": missing_sections_for(proposal)}})


class ProposalCompletenessView(APIView):
    """GET /api/v1/ol-proposals/{id}/completeness/"""

    permission_classes = [MustViewProposalsPermission]

    def get(self, request, proposal_id):
        proposal = _get_proposal(proposal_id)
        return Response({"data": missing_sections_for(proposal)})


class ProposalEnrichmentOptionsView(APIView):
    """GET /api/v1/ol-proposals/options/{kind}/ — SmartSelect-compatible options."""

    permission_classes = [MustViewProposalsPermission]

    def get(self, request, kind):
        query = request.query_params.get("q", "")
        results = self._options(kind, query)
        return Response({"data": {"results": results, "count": len(results)}})

    def _options(self, kind, query):
        if kind in ("employers", "intermediaries"):
            from apps.partners.models import Partner

            partners = Partner.objects.filter(is_active=True, status="ACTIVE")
            if kind == "employers":
                partners = partners.filter(party_type__iexact="CORPORATE")
            results = [
                {"id": str(p.pk), "label": _partner_label(p), "reference": p.partner_number}
                for p in partners.order_by("partner_number")[:200]
            ]
            return results
        if kind == "beneficial-types":
            from apps.ol_parameters.models import OLBeneficialType

            return [
                {"id": str(item.pk), "label": item.name or item.code, "code": item.code}
                for item in OLBeneficialType.objects.filter(is_active=True).order_by("name", "code")[:200]
            ]
        if kind == "channels":
            return [{"value": channel, "label": channel} for channel in ("AGENT", "BROKER", "BANCA", "OTHER")]
        from apps.ol_proposals.errors import ProposalError

        raise ProposalError(f"Unknown options kind '{kind}'.", error_code="PROPOSAL_NOT_FOUND", status_code=404, resolution_steps=["Use one of: employers, intermediaries, beneficial-types, channels."])


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