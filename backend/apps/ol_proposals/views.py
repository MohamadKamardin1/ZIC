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

PROPOSAL_BANK_OPTIONS = [
    ("NMB", "NMB Bank Plc"),
    ("CRDB", "CRDB Bank Plc"),
    ("TPB", "Tanzania Postal Bank (TPB)"),
    ("BOA", "Bank of Africa Tanzania"),
    ("EXIM", "Exim Bank Tanzania"),
    ("NBC", "NBC Bank"),
    ("STANBIC", "Stanbic Bank Tanzania"),
    ("KCB", "KCB Bank Tanzania"),
    ("DTB", "Diamond Trust Bank Tanzania"),
    ("CITIBANK", "Citibank Tanzania"),
    ("AZANIA", "Azania Bank"),
    ("ADVANS", "Advans Bank Tanzania"),
]

PROPOSAL_BANK_OPTIONS = tuple(PROPOSAL_BANK_OPTIONS)


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


class MustUploadDocumentsPermission(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return has_ol_proposal_permission(request.user, "upload_documents")


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

    KIND_LABELS = {
        "statuses": "Proposal status",
        "employers": "Corporate partner (employer)",
        "intermediaries": "Intermediary/agent partner",
        "beneficial-types": "Beneficial type",
        "document-types": "Proposal document type",
        "banks": "Bank",
        "channels": "Distribution channel",
    }

    def get(self, request, kind):
        query = request.query_params.get("q", "")
        results = self._options(kind, query)
        return Response(
            {
                "data": {
                    "kind": kind,
                    "label": self.KIND_LABELS.get(kind, kind),
                    "results": results,
                    "count": len(results),
                }
            }
        )

    def _options(self, kind, query):
        if kind == "statuses":
            from apps.ol_parameters.models import OLProposalStatus

            rows = OLProposalStatus.objects.filter(is_active=True, applies_to__iexact="PROPOSAL").order_by("display_order", "code")
            return [
                {"id": item.code, "label": item.name or item.code, "value": item.code}
                for item in rows
                if not query or query.lower() in f"{item.name} {item.code}".lower()
            ]
        if kind in ("employers", "intermediaries"):
            from apps.partners.models import Partner

            partners = Partner.objects.filter(is_active=True, status="ACTIVE")
            if kind == "employers":
                partners = partners.filter(party_type__iexact="CORPORATE")
            return [
                {"id": str(p.pk), "label": _partner_label(p), "reference": p.partner_number}
                for p in partners.order_by("partner_number")[:200]
                if not query or query.lower() in _partner_label(p).lower()
            ]
        if kind == "beneficial-types":
            from apps.ol_parameters.models import OLBeneficialType

            return [
                {"id": str(item.pk), "label": item.name or item.code, "code": item.code}
                for item in OLBeneficialType.objects.filter(is_active=True).order_by("name", "code")[:200]
                if not query or query.lower() in f"{item.name} {item.code}".lower()
            ]
        if kind == "document-types":
            from apps.ol_parameters.models import OLProposalDocumentRequirement

            return [
                {"id": item.code, "label": item.name or item.document_type, "value": item.document_type}
                for item in OLProposalDocumentRequirement.objects.filter(is_active=True).order_by("name", "document_type")
                if not query or query.lower() in f"{item.name} {item.document_type}".lower()
            ]
        if kind == "banks":
            return [
                {"id": code, "label": label, "value": label}
                for code, label in PROPOSAL_BANK_OPTIONS
                if not query or query.lower() in label.lower()
            ]
        if kind == "channels":
            return [{"value": channel, "label": channel} for channel in ("AGENT", "BROKER", "BANCA", "OTHER")]
        from apps.ol_proposals.errors import ProposalError

        raise ProposalError(
            f"Unknown options kind '{kind}'.",
            error_code="PROPOSAL_NOT_FOUND",
            status_code=404,
            resolution_steps=["Use one of: statuses, employers, intermediaries, beneficial-types, document-types, banks, channels."],
        )


class ProposalDocumentCollectionView(APIView):
    """GET/POST /api/v1/ol-proposals/{id}/documents/"""

    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method in ("GET",) else [MustUploadDocumentsPermission()]

    def get(self, request, proposal_id):
        from apps.ol_proposals.models import ProposalDocumentStatus
        from apps.ol_proposals.serializers import OLProposalDocumentSerializer

        proposal = _get_proposal(proposal_id)
        rows = list(proposal.documents.order_by("document_type"))
        return Response(
            {
                "data": {
                    "results": OLProposalDocumentSerializer(rows, many=True).data,
                    "mandatory": proposal.documents.filter(mandatory=True).count(),
                    "uploaded": proposal.documents.filter(status__in=(ProposalDocumentStatus.UPLOADED, ProposalDocumentStatus.VERIFIED)).count(),
                }
            }
        )

    def post(self, request, proposal_id):
        from apps.ol_proposals.services.document_service import upload_document

        proposal = _get_proposal(proposal_id)
        document, created = upload_document(
            proposal=proposal,
            document_type=request.data.get("document_type"),
            file_reference=request.data.get("file_reference"),
            actor=request.user,
            source_channel="API",
        )
        return Response(
            {"data": {"document_type": document.document_type, "file_reference": document.file_reference, "mandatory": document.mandatory, "status": document.status}},
            status=201 if created else 200,
        )


class ProposalHealthQuestionsView(APIView):
    """GET /api/v1/ol-proposals/{id}/health-questions/"""

    permission_classes = [MustViewProposalsPermission]

    def get(self, request, proposal_id):
        from apps.ol_proposals.serializers import OLHealthQuestionnaireItemSerializer
        from apps.ol_proposals.services.health_service import applicable_questionnaire, questionnaire_items

        proposal = _get_proposal(proposal_id)
        questionnaire = applicable_questionnaire(proposal)
        return Response(
            {
                "data": {
                    "questionnaire": questionnaire.code if questionnaire else None,
                    "results": OLHealthQuestionnaireItemSerializer(questionnaire_items(proposal), many=True).data,
                }
            }
        )


class ProposalHealthAnswersView(APIView):
    """POST /api/v1/ol-proposals/{id}/health-answers/"""

    permission_classes = [MustEnrichProposalPermission]

    def post(self, request, proposal_id):
        from apps.ol_proposals.services.health_service import record_answers

        proposal = _get_proposal(proposal_id)
        answers = request.data.get("answers") if isinstance(request.data, dict) else request.data
        result = record_answers(proposal=proposal, answers=answers, actor=request.user, source_channel="API", reason=request.data.get("reason") or "")
        proposal.refresh_from_db()
        payload = OLProposalDetailSerializer(proposal).data
        payload["health_result"] = result
        return Response({"data": payload})


class ProposalUnderwritingDecisionView(APIView):
    """POST /api/v1/ol-proposals/{id}/underwriting-decision/"""

    permission_classes = [MustEnrichProposalPermission]

    def post(self, request, proposal_id):
        from apps.ol_proposals.services.underwriting_service import decide

        proposal = _get_proposal(proposal_id)
        proposal = decide(
            proposal=proposal,
            decision=request.data.get("decision"),
            actor=request.user,
            request=request,
            reason=request.data.get("reason") or "",
            source_channel="API",
        )
        proposal.refresh_from_db()
        return Response({"data": OLProposalDetailSerializer(proposal).data})


class MustMarkPaymentReadyPermission(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return has_ol_proposal_permission(request.user, "mark_payment_ready")


class ProposalPaymentReadinessView(APIView):
    """GET /api/v1/ol-proposals/proposals/{id}/payment-readiness/ — read-only checklist."""

    permission_classes = [MustViewProposalsPermission]

    def get(self, request, proposal_id):
        from apps.ol_proposals.services.payment_readiness_service import evaluate_payment_ready

        proposal = _get_proposal(proposal_id)
        return Response({"data": evaluate_payment_ready(proposal)})


class ProposalMarkPaymentReadyView(APIView):
    """POST /api/v1/ol-proposals/proposals/{id}/mark-payment-ready/"""

    permission_classes = [MustMarkPaymentReadyPermission]

    def post(self, request, proposal_id):
        from apps.ol_proposals.services.payment_readiness_service import mark_payment_ready

        proposal = _get_proposal(proposal_id)
        result = mark_payment_ready(
            proposal=proposal,
            actor=request.user,
            request=request,
            source_channel="API",
            reason=request.data.get("reason") or "",
        )
        proposal.refresh_from_db()
        payload = OLProposalBaseSerializer(proposal).data
        payload["payment_readiness"] = result
        return Response({"data": payload})


class ProposalFirstPremiumStatusView(APIView):
    """GET /api/v1/ol-proposals/proposals/{id}/first-premium/ — read-only payment status."""

    permission_classes = [MustViewProposalsPermission]

    def get(self, request, proposal_id):
        from apps.ol_proposals.services.first_premium_service import first_premium_status

        proposal = _get_proposal(proposal_id)
        return Response({"data": first_premium_status(proposal)})


class ProposalListView(APIView):
    """GET /api/v1/ol-proposals/proposals/ — table-first paginated proposal list.

    Columns and filters documented in Prompt 8; names, never UUIDs.
    """

    permission_classes = [MustViewProposalsPermission]

    def get(self, request):
        from apps.ol_proposals.serializers import OLProposalListSerializer
        from apps.ol_proposals.services.listing_service import (
            apply_list_filters,
            base_list_queryset,
            order_queryset,
        )

        queryset = apply_list_filters(base_list_queryset(), request.query_params)
        queryset = order_queryset(queryset, request.query_params.get("ordering"))

        page = max(1, int(request.query_params.get("page", 1)))
        page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
        total = queryset.count()
        start = (page - 1) * page_size
        rows = queryset[start:start + page_size]

        return Response(
            {
                "data": {
                    "results": OLProposalListSerializer(rows, many=True, context={"request": request}).data,
                    "count": total,
                    "page": page,
                    "page_size": page_size,
                    "next": page * page_size < total,
                    "previous": page > 1,
                }
            }
        )


class ProposalKpisView(APIView):
    """GET /api/v1/ol-proposals/proposals/kpis/ — register KPIs (role-filtered)."""

    permission_classes = [MustViewProposalsPermission]

    def get(self, request):
        from apps.ol_proposals.services.listing_service import proposal_kpis

        return Response(
            {
                "data": proposal_kpis(
                    user=request.user,
                    period_from=request.query_params.get("period_from"),
                    period_to=request.query_params.get("period_to"),
                    expiring_soon_days=request.query_params.get("expiring_soon_days"),
                )
            }
        )


class ProposalDashboardKpisView(APIView):
    """GET /api/v1/ol-proposals/proposals/dashboard-kpis/ — dashboard hook (role-filtered)."""

    permission_classes = [MustViewProposalsPermission]

    def get(self, request):
        from apps.ol_proposals.services.dashboard_kpi_service import proposal_dashboard_kpis

        return Response({"data": proposal_dashboard_kpis(user=request.user)})


class ProposalReportingDatasetView(APIView):
    """GET /api/v1/ol-proposals/proposals/reporting/dataset/ — reporting module contract."""

    permission_classes = [MustViewProposalsPermission]

    def get(self, request):
        from apps.ol_proposals.services.reporting_service import register

        return Response({"data": register()})


def _portal_proposal_queryset(partner):
    from django.db.models import Prefetch

    from apps.ol_proposals.models import OLProposalPlanConfig

    selected = Prefetch(
        "plan_configs",
        queryset=OLProposalPlanConfig.objects.filter(is_selected=True).select_related("plan", "product_version__product"),
    )
    return OLProposal.objects.filter(partner=partner).select_related(
        "quotation", "partner", "agent_partner", "employer_partner", "first_premium_commitment"
    ).prefetch_related(selected, "beneficiaries")


class PartnerPortalProposalListView(APIView):
    """GET /api/v1/ol-proposals/proposals/portal/ — read-only proposals for the linked partner."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.ol_proposals.serializers import PartnerPortalProposalListSerializer

        partner = request.user.current_partner() if hasattr(request.user, "current_partner") else None
        if partner is None:
            return Response({"data": {"results": [], "count": 0}})
        queryset = _portal_proposal_queryset(partner).order_by("-created_at")
        return Response(
            {
                "data": {
                    "results": PartnerPortalProposalListSerializer(
                        queryset[:200], many=True, context={"request": request}
                    ).data,
                    "count": queryset.count(),
                }
            }
        )


class PartnerPortalProposalDetailView(APIView):
    """GET /api/v1/ol-proposals/proposals/portal/{id}/ — scoped read-only detail."""

    permission_classes = [IsAuthenticated]

    def get(self, request, proposal_id):
        from apps.ol_proposals.serializers import PartnerPortalProposalDetailSerializer

        partner = request.user.current_partner() if hasattr(request.user, "current_partner") else None
        proposal = None
        if partner is not None:
            proposal = _portal_proposal_queryset(partner).filter(pk=proposal_id).first()
        if proposal is None:
            raise ProposalError(
                "The proposal could not be found.",
                error_code="PROPOSAL_NOT_FOUND",
                status_code=404,
                resolution_steps=["Verify the proposal number."],
            )
        return Response({"data": PartnerPortalProposalDetailSerializer(proposal, context={"request": request}).data})


class ProposalExportView(APIView):
    """GET /api/v1/ol-proposals/proposals/export/ — CSV export respecting list filters."""

    permission_classes = [MustViewProposalsPermission]

    def get(self, request):
        import csv

        from django.http import HttpResponse

        from apps.ol_proposals.serializers import OLProposalListSerializer
        from apps.ol_proposals.services.listing_service import (
            apply_list_filters,
            base_list_queryset,
            iter_csv_rows,
            order_queryset,
        )

        queryset = apply_list_filters(base_list_queryset(), request.query_params)
        queryset = order_queryset(queryset, request.query_params.get("ordering"))
        rows = OLProposalListSerializer(queryset[:5000], many=True, context={"request": request}).data

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="ol-proposals.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "proposal_number",
                "policyholder",
                "agent",
                "employer",
                "product",
                "plan",
                "total_premium",
                "currency",
                "status",
                "payment_ready",
                "first_premium_posted",
                "expiry_date",
                "created_at",
            ]
        )
        writer.writerows(iter_csv_rows(rows))
        return response


class MustCancelProposalPermission(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return has_ol_proposal_permission(request.user, "cancel")


class ProposalCancelView(APIView):
    """POST /api/v1/ol-proposals/proposals/{id}/cancel/ — reason mandatory, audited."""

    permission_classes = [MustCancelProposalPermission]

    def post(self, request, proposal_id):
        from apps.ol_proposals.services.lifecycle_service import cancel_proposal

        proposal = _get_proposal(proposal_id)
        cancel_proposal(
            proposal=proposal,
            actor=request.user,
            request=request,
            reason=request.data.get("reason") or "",
            source_channel="API",
        )
        proposal.refresh_from_db()
        return Response({"data": OLProposalDetailSerializer(proposal).data})


class ProposalReactivateView(APIView):
    """POST /api/v1/ol-proposals/proposals/{id}/reactivate/ — parameter-gated from expiry."""

    permission_classes = [MustEnrichProposalPermission]

    def post(self, request, proposal_id):
        from apps.ol_proposals.services.lifecycle_service import reactivate_proposal

        proposal = _get_proposal(proposal_id)
        reactivate_proposal(
            proposal=proposal,
            actor=request.user,
            request=request,
            reason=request.data.get("reason") or "",
            source_channel="API",
        )
        proposal.refresh_from_db()
        return Response({"data": OLProposalDetailSerializer(proposal).data})


class MustPrintProposalPermission(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return has_ol_proposal_permission(request.user, "print")


class MustConvertProposalPermission(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return has_ol_proposal_permission(request.user, "convert")


class ProposalConvertToPolicyView(APIView):
    """POST /api/v1/ol-proposals/proposals/{id}/convert/ — BR-03-gated policy conversion."""

    permission_classes = [MustConvertProposalPermission]

    def post(self, request, proposal_id):
        from apps.ol_proposals.services.policy_conversion_service import convert_proposal_to_policy

        proposal = _get_proposal(proposal_id)
        policy, created = convert_proposal_to_policy(
            proposal=proposal,
            actor=request.user,
            request=request,
            source_channel="API",
        )
        proposal.refresh_from_db()
        return Response(
            {
                "data": {
                    "proposal_number": proposal.proposal_number,
                    "status": proposal.status,
                    "policy_number": policy.policy_number,
                    "converted_policy": str(policy.pk),
                    "created": created,
                }
            },
            status=201 if created else 200,
        )


class ProposalPrintView(APIView):
    """POST /api/v1/ol-proposals/proposals/{id}/print/ — render a summary printout."""

    permission_classes = [MustPrintProposalPermission]

    def post(self, request, proposal_id):
        from apps.ol_proposals.services.print_service import ProposalPrintService

        proposal = _get_proposal(proposal_id)
        document = ProposalPrintService.generate(
            proposal=proposal,
            actor=request.user,
            request=request,
            template_code=request.data.get("template_code"),
            preview=bool(request.data.get("preview")),
        )
        return Response(
            {
                "data": {
                    "proposal_number": proposal.proposal_number,
                    "document_type": document.document_type,
                    "status": document.status,
                    "file_reference": document.file_reference,
                    "template_code": document.template.code if document.template_id else None,
                    "template_version": document.template_version,
                    "source_version": (document.metadata or {}).get("source_version_number"),
                    "urls": ProposalPrintService.document_urls(document),
                }
            },
            status=201,
        )


class ProposalHistoryView(APIView):
    """GET /api/v1/ol-proposals/proposals/{id}/history/ — status timeline.

    Reads the durable ``DomainEvent`` outbox rows emitted by the lifecycle
    (created, enriched, payment-ready, converted, cancelled, expired) so the
    detail page can render an auditable timeline with actor, previous/new
    state, reason, and source channel.
    """

    permission_classes = [MustViewProposalsPermission]

    def get(self, request, proposal_id):
        from apps.common.models import DomainEvent
        from django.contrib.auth import get_user_model

        proposal = _get_proposal(proposal_id)
        events = DomainEvent.objects.filter(aggregate_type="OLProposal", aggregate_id=str(proposal.pk)).order_by("occurred_at", "id")
        user_model = get_user_model()
        actor_ids = {
            str((event.payload or {}).get("actor_id") or "")
            for event in events
            if (event.payload or {}).get("actor_id")
        }
        actor_names = {}
        if actor_ids:
            for user in user_model.objects.filter(pk__in=actor_ids):
                actor_names[str(user.pk)] = user.full_name or user.get_username()
        items = []
        for event in events:
            payload = event.payload or {}
            items.append(
                {
                    "id": str(event.pk),
                    "event_type": event.event_type,
                    "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
                    "actor": actor_names.get(str(payload.get("actor_id") or ""), ""),
                    "from_status": payload.get("from_status") or "",
                    "to_status": payload.get("to_status") or "",
                    "reason": payload.get("reason") or "",
                    "source_channel": payload.get("source_channel") or "",
                }
            )
        return Response(
            {
                "data": {
                    "proposal_id": str(proposal.pk),
                    "proposal_number": proposal.proposal_number,
                    "events": items,
                }
            }
        )


class ProposalDetailView(APIView):
    """GET /api/v1/ol-proposals/{id}/ — proposal detail with carried children."""

    permission_classes = [MustViewProposalsPermission]

    def get(self, request, proposal_id):
        from apps.ol_proposals.services.lifecycle_service import allowed_actions
        from apps.ol_proposals.services.payment_readiness_service import evaluate_payment_ready

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
            raise ProposalError(
                "The proposal could not be found.",
                error_code="PROPOSAL_NOT_FOUND",
                status_code=404,
                resolution_steps=["Verify the proposal number.", "Check the proposal register filters."],
            )
        payload = OLProposalDetailSerializer(proposal).data
        payload["completeness"] = missing_sections_for(proposal)
        payload["checklist"] = evaluate_payment_ready(proposal)
        payload["quotation_versions"] = [
            {
                "version_number": item.version_number,
                "status": item.status,
                "change_reason": item.change_reason,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in proposal.quotation.versions.order_by("-version_number")
        ]
        payload["allowed_actions"] = allowed_actions(proposal, actor=request.user)
        return Response({"data": payload})