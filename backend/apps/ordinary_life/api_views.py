from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.governance.models import ApprovalRequest, AuditLog
from apps.ordinary_life.models import (
    OLApplication,
    OLBeneficiaryAllocation,
    OLClaim,
    OLClient,
    OLCommitment,
    OLDocumentRecord,
    OLEndorsement,
    OLHealthDeclaration,
    OLHealthResponse,
    OLLoan,
    OLMedicalRequirement,
    OLNote,
    OLPaymentAllocation,
    OLPaymentObligation,
    OLPolicy,
    OLPolicyParty,
    OLPolicyRenewal,
    OLPolicyStatusHistory,
    OLPolicyTransaction,
    OLPremiumInstallment,
    OLPremiumSchedule,
    OLProduct,
    OLProposal,
    OLQuotation,
    OLQuotationVersion,
    OLReinstatementRequest,
    OLUnderwritingCase,
    OLUnderwritingDecisionEvent,
    OLWithdrawal,
    OLWorkflowEvent,
)
from apps.ordinary_life.serializers import (
    OLApplicationCreateSerializer,
    OLApplicationSerializer,
    OLBeneficiaryAllocationSerializer,
    OLClaimSerializer,
    OLClientSerializer,
    OLCommitmentSerializer,
    OLDocumentCreateSerializer,
    OLDocumentRecordSerializer,
    OLEndorsementCreateSerializer,
    OLEndorsementSerializer,
    OLHealthDeclarationCreateSerializer,
    OLHealthDeclarationSerializer,
    OLHealthResponseSerializer,
    OLLoanSerializer,
    OLMedicalRequirementSerializer,
    OLMedicalResultCreateSerializer,
    OLMedicalResultSerializer,
    OLNoteCreateSerializer,
    OLNoteSerializer,
    OLPaymentAllocationCreateSerializer,
    OLPaymentAllocationSerializer,
    OLPaymentObligationSerializer,
    OLPolicyIssueSerializer,
    OLPolicyPartySerializer,
    OLPolicyRenewalCreateSerializer,
    OLPolicyRenewalSerializer,
    OLPolicySerializer,
    OLPolicyStatusHistorySerializer,
    OLPolicyTransactionSerializer,
    OLPremiumInstallmentSerializer,
    OLPremiumScheduleSerializer,
    OLProductSerializer,
    OLProposalConvertSerializer,
    OLProposalSerializer,
    OLQuotationCreateSerializer,
    OLQuotationSerializer,
    OLQuotationVersionSerializer,
    OLReasonSerializer,
    OLReinstatementCreateSerializer,
    OLReinstatementRequestSerializer,
    OLUnderwritingCaseSerializer,
    OLUnderwritingDecisionEventSerializer,
    OLUnderwritingDecisionSerializer,
    OLWithdrawalSerializer,
    OLWorkflowEventReadSerializer,
)
from apps.ordinary_life.services.application_service import OrdinaryLifeApplicationService
from apps.ordinary_life.services.operations_service import OrdinaryLifeOperationsService
from apps.ordinary_life.services.policy_service import OrdinaryLifePolicyService
from apps.partners.models import Partner

MODULE_CODE = "ordinary_life"


def _meta(request):
    return {
        "timestamp": __import__("datetime").datetime.now().isoformat() + "Z",
        "request_id": getattr(request, "request_id", None),
        "version": "v1",
    }


def _response(request, data, message="Data retrieved successfully", status_code=status.HTTP_200_OK):
    return Response(
        {
            "success": True,
            "status_code": status_code,
            "message": message,
            "data": data,
            "meta": _meta(request),
        },
        status=status_code,
    )


def _error(request, detail, message="Request validation failed", status_code=status.HTTP_400_BAD_REQUEST):
    return Response(
        {
            "success": False,
            "status_code": status_code,
            "message": message,
            "errors": detail,
            "meta": _meta(request),
        },
        status=status_code,
    )


def _approval_data(approval):
    return {
        "id": str(approval.pk),
        "module": approval.module,
        "entity_type": approval.entity_type,
        "entity_id": str(approval.entity_id),
        "entity_repr": approval.entity_repr,
        "action": approval.action,
        "requested_data": approval.requested_data,
        "current_data": approval.current_data,
        "status": approval.status,
        "submitted_by": str(approval.submitted_by_id) if approval.submitted_by_id else None,
        "reviewed_by": str(approval.reviewed_by_id) if approval.reviewed_by_id else None,
        "submitted_at": approval.submitted_at,
        "reviewed_at": approval.reviewed_at,
        "comments": approval.comments,
    }


def _run(request, operation: Callable[[], Any], serializer_class=None, message="Operation completed successfully", status_code=status.HTTP_200_OK):
    try:
        value = operation()
    except DjangoValidationError as exc:
        detail = getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc)
        return _error(request, detail)
    except ObjectDoesNotExist as exc:
        return _error(request, str(exc), "Resource not found", status.HTTP_404_NOT_FOUND)
    except (PermissionError, ValueError) as exc:
        return _error(request, str(exc), "Operation rejected")
    if isinstance(value, ApprovalRequest):
        value = _approval_data(value)
    data = serializer_class(value).data if serializer_class else value
    return _response(request, data, message, status_code)


class OrdinaryLifePermission(permissions.BasePermission):
    message = "You do not have the required Ordinary Life permission."

    ACTIONS = {
        "create": "CREATE",
        "issue": "CREATE",
        "allocate": "CREATE",
        "create_document": "CREATE",
        "add_note": "CREATE",
        "request_endorsement": "CREATE",
        "request_renewal": "CREATE",
        "request_reinstatement": "CREATE",
        "submit": "UPDATE",
        "start_underwriting": "UPDATE",
        "health_declaration": "UPDATE",
        "submit_approval": "UPDATE",
        "assess": "ASSESS",
        "record_result": "UPDATE",
        "upload": "UPDATE",
        "apply": "UPDATE",
        "lapse": "UPDATE",
        "grace": "UPDATE",
        "reactivate": "UPDATE",
        "cancel": "UPDATE",
        "mature": "UPDATE",
        "reopen": "UPDATE",
        "approve": "APPROVE",
        "verify": "REVIEW",
        "submit_verification": "REVIEW",
        "complete_verification": "APPROVE",
        "reject_verification": "REJECT",
        "complete": "APPROVE",
    }

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not getattr(user, "is_active", False):
            return False
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return True
        action = self.ACTIONS.get(getattr(view, "action", ""), "READ")
        return user.has_module_permission(MODULE_CODE, action)


class OrdinaryLifeScopedMixin:
    partner_scope_lookups: tuple[str, ...] = ()
    search_fields: tuple[str, ...] = ()

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if not self.partner_scope_lookups or user.is_superuser or user.is_staff:
            return queryset
        partners = user.visible_partners()
        scope = Q()
        for lookup in self.partner_scope_lookups:
            scope |= Q(**{f"{lookup}__in": partners})
        return queryset.filter(scope).distinct()

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        params = self.request.query_params
        if params.get("status") and hasattr(queryset.model, "status"):
            queryset = queryset.filter(status=params["status"].upper())
        if params.get("from") and hasattr(queryset.model, "created_at"):
            queryset = queryset.filter(created_at__date__gte=params["from"])
        if params.get("to") and hasattr(queryset.model, "created_at"):
            queryset = queryset.filter(created_at__date__lte=params["to"])
        term = params.get("search")
        if term and self.search_fields:
            query = Q()
            for field in self.search_fields:
                query |= Q(**{f"{field}__icontains": term})
            queryset = queryset.filter(query)
        return queryset

    def get_permissions(self):
        return [OrdinaryLifePermission()]


class OrdinaryLifeReadOnlyViewSet(OrdinaryLifeScopedMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    filter_backends = []

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return _response(request, self.get_serializer(queryset, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        return _response(request, self.get_serializer(self.get_object()).data)


class OLProductApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLProduct.objects.all()
    serializer_class = OLProductSerializer
    search_fields = ("code", "name")


class OLClientApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLClient.objects.all()
    serializer_class = OLClientSerializer
    search_fields = ("first_name", "last_name", "id_number", "phone", "email")


class OLApplicationApiViewSet(OrdinaryLifeScopedMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = OLApplication.objects.select_related("partner", "policyholder", "life_assured", "payer", "proposal")
    serializer_class = OLApplicationSerializer
    partner_scope_lookups = ("partner",)
    search_fields = ("application_number", "partner__display_name", "policyholder__display_name")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return _response(request, self.get_serializer(queryset, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        return _response(request, self.get_serializer(self.get_object()).data)

    def create(self, request, *args, **kwargs):
        serializer = OLApplicationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(request, serializer.errors)
        data = serializer.validated_data
        return _run(
            request,
            lambda: OrdinaryLifeApplicationService.create_application(
                partner=Partner.objects.get(pk=data["partner"]),
                policyholder=Partner.objects.get(pk=data["policyholder"]),
                life_assured=Partner.objects.get(pk=data["life_assured"]),
                payer=Partner.objects.get(pk=data["payer"]) if data.get("payer") else None,
                declarations=data.get("declarations") or {},
                actor=request.user,
            ),
            OLApplicationSerializer,
            "Application created successfully",
            status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        serializer = OLReasonSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(request, serializer.errors)
        return _run(request, lambda: OrdinaryLifeApplicationService.submit_application(self.get_object(), actor=request.user, reason=serializer.validated_data.get("reason", "")), OLApplicationSerializer, "Application submitted successfully")


class OLQuotationApiViewSet(OrdinaryLifeScopedMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = OLQuotation.objects.select_related("application__partner", "application__policyholder", "product_version", "plan", "current_version")
    serializer_class = OLQuotationSerializer
    partner_scope_lookups = ("application__partner",)
    search_fields = ("quotation_number", "application__application_number")

    def list(self, request, *args, **kwargs):
        return _response(request, self.get_serializer(self.filter_queryset(self.get_queryset()), many=True).data)

    def retrieve(self, request, *args, **kwargs):
        return _response(request, self.get_serializer(self.get_object()).data)

    def create(self, request, *args, **kwargs):
        serializer = OLQuotationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(request, serializer.errors)
        data = serializer.validated_data
        from apps.ordinary_life.models import OLPlan, OLProductVersion
        return _run(request, lambda: OrdinaryLifeApplicationService.create_quotation(application=OLApplication.objects.get(pk=data["application"]), product_version=OLProductVersion.objects.get(pk=data["product_version"]), sum_assured=data["sum_assured"], term_years=data["term_years"], payment_frequency=data["payment_frequency"], plan=OLPlan.objects.get(pk=data["plan"]) if data.get("plan") else None, rider_codes=data.get("rider_codes") or [], actor=request.user), OLQuotationSerializer, "Quotation created successfully", status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        serializer = OLReasonSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(request, serializer.errors)
        return _run(request, lambda: OrdinaryLifeApplicationService.submit_quotation(self.get_object(), actor=request.user, reason=serializer.validated_data.get("reason", "")), OLQuotationSerializer, "Quotation submitted successfully")

    @action(detail=True, methods=["post"], url_path="convert-to-proposal")
    def convert_to_proposal(self, request, pk=None):
        serializer = OLProposalConvertSerializer(data={**request.data, "quotation": str(pk)})
        if not serializer.is_valid():
            return _error(request, serializer.errors)
        data = serializer.validated_data
        return _run(request, lambda: OrdinaryLifeApplicationService.convert_quotation_to_proposal(self.get_object(), application=OLApplication.objects.get(pk=data["application"]) if data.get("application") else None, actor=request.user, reason=data.get("reason", "")), OLProposalSerializer, "Proposal created successfully", status.HTTP_201_CREATED)


class OLProposalApiViewSet(OrdinaryLifeScopedMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = OLProposal.objects.select_related("application__partner", "quotation", "quotation_version", "underwriting_case")
    serializer_class = OLProposalSerializer
    partner_scope_lookups = ("application__partner",)
    search_fields = ("proposal_number", "quotation__quotation_number")

    def list(self, request, *args, **kwargs):
        return _response(request, self.get_serializer(self.filter_queryset(self.get_queryset()), many=True).data)

    def retrieve(self, request, *args, **kwargs):
        return _response(request, self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=["post"])
    def start_underwriting(self, request, pk=None):
        serializer = OLReasonSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(request, serializer.errors)
        return _run(request, lambda: OrdinaryLifeApplicationService.start_underwriting(self.get_object(), actor=request.user, reason=serializer.validated_data.get("reason", "")), OLUnderwritingCaseSerializer, "Underwriting case started successfully", status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def health_declaration(self, request, pk=None):
        serializer = OLHealthDeclarationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(request, serializer.errors)
        data = serializer.validated_data
        from apps.ordinary_life.models import OLHealthQuestionnaire
        return _run(request, lambda: OrdinaryLifeApplicationService.record_health_declaration(self.get_object(), questionnaire=OLHealthQuestionnaire.objects.get(pk=data["questionnaire"]) if data.get("questionnaire") else None, responses=data.get("responses") or [], actor=request.user, reason=data.get("reason", "")), OLHealthDeclarationSerializer, "Health declaration recorded successfully", status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def submit_approval(self, request, pk=None):
        return _run(request, lambda: OrdinaryLifeApplicationService.submit_proposal_for_approval(self.get_object(), actor=request.user, comments=request.data.get("comments", "")), None, "Proposal submitted for approval successfully")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        serializer = OLReasonSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(request, serializer.errors)
        return _run(request, lambda: OrdinaryLifeApplicationService.approve_proposal(self.get_object(), actor=request.user, reason=serializer.validated_data.get("reason", "")), OLProposalSerializer, "Proposal approved successfully")


class OLUnderwritingCaseApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLUnderwritingCase.objects.select_related("proposal__application__partner")
    serializer_class = OLUnderwritingCaseSerializer
    partner_scope_lookups = ("proposal__application__partner",)

    @action(detail=True, methods=["post"])
    def assess(self, request, pk=None):
        serializer = OLUnderwritingDecisionSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(request, serializer.errors)
        data = serializer.validated_data
        return _run(request, lambda: OrdinaryLifeApplicationService.assess_risk(self.get_object(), decision=data["decision"], risk_class=data.get("risk_class", "STANDARD"), actor=request.user, reason=data["reason"]), OLUnderwritingCaseSerializer, "Underwriting decision recorded successfully")

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        return _run(request, lambda: OrdinaryLifeApplicationService.reopen_underwriting(self.get_object(), actor=request.user, reason=request.data.get("reason", "")), OLUnderwritingCaseSerializer, "Underwriting case reopened successfully")


class OLMedicalRequirementApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLMedicalRequirement.objects.select_related("underwriting_case__proposal__application__partner", "result")
    serializer_class = OLMedicalRequirementSerializer
    partner_scope_lookups = ("underwriting_case__proposal__application__partner",)

    @action(detail=True, methods=["post"], url_path="record-result")
    def record_result(self, request, pk=None):
        serializer = OLMedicalResultCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(request, serializer.errors)
        data = serializer.validated_data
        return _run(request, lambda: OrdinaryLifeApplicationService.record_medical_result(self.get_object(), result=data["result"], evidence_reference=data.get("evidence_reference", ""), result_data=data.get("result_data") or {}, actor=request.user, reason=data.get("reason", "")), OLMedicalResultSerializer, "Medical result recorded successfully", status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        return _run(request, lambda: OrdinaryLifeApplicationService.verify_medical_requirement(self.get_object(), actor=request.user, reason=request.data.get("reason", "")), OLMedicalRequirementSerializer, "Medical requirement verified successfully")


class OLHealthDeclarationApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLHealthDeclaration.objects.select_related("proposal__application__partner", "questionnaire")
    serializer_class = OLHealthDeclarationSerializer
    partner_scope_lookups = ("proposal__application__partner",)


class OLHealthResponseApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLHealthResponse.objects.select_related("declaration__proposal__application__partner", "question")
    serializer_class = OLHealthResponseSerializer
    partner_scope_lookups = ("declaration__proposal__application__partner",)


class OLQuotationVersionApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLQuotationVersion.objects.select_related("quotation__application__partner", "product_version", "plan")
    serializer_class = OLQuotationVersionSerializer
    partner_scope_lookups = ("quotation__application__partner",)


class OLUnderwritingDecisionEventApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLUnderwritingDecisionEvent.objects.select_related("underwriting_case__proposal__application__partner", "actor")
    serializer_class = OLUnderwritingDecisionEventSerializer
    partner_scope_lookups = ("underwriting_case__proposal__application__partner",)


class OLPaymentObligationApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLPaymentObligation.objects.select_related("proposal__application__partner", "policy__policyholder_partner", "installment")
    serializer_class = OLPaymentObligationSerializer
    partner_scope_lookups = ("proposal__application__partner", "policy__policyholder_partner")

    @action(detail=True, methods=["post"])
    def allocate(self, request, pk=None):
        serializer = OLPaymentAllocationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(request, serializer.errors)
        data = serializer.validated_data
        return _run(request, lambda: OrdinaryLifePolicyService.allocate_payment(self.get_object(), amount=data["amount"], external_receipt_reference=data["external_receipt_reference"], actor=request.user, reason=data.get("reason", ""), metadata=data.get("metadata") or {}), OLPaymentAllocationSerializer, "Payment allocated successfully", status.HTTP_201_CREATED)


class OLPaymentAllocationApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLPaymentAllocation.objects.select_related("obligation__proposal__application__partner", "obligation__policy__policyholder_partner")
    serializer_class = OLPaymentAllocationSerializer
    partner_scope_lookups = ("obligation__proposal__application__partner", "obligation__policy__policyholder_partner")


class OLPolicyApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLPolicy.objects.select_related("proposal__application__partner", "policyholder_partner", "life_assured_partner", "agent")
    serializer_class = OLPolicySerializer
    partner_scope_lookups = ("policyholder_partner", "life_assured_partner", "agent")
    search_fields = ("policy_number", "proposal__proposal_number")

    @action(detail=False, methods=["post"])
    def issue(self, request):
        serializer = OLPolicyIssueSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(request, serializer.errors)
        data = serializer.validated_data
        return _run(request, lambda: OrdinaryLifePolicyService.issue_policy(OLProposal.objects.get(pk=data["proposal"]), actor=request.user, start_date=data.get("effective_date"), beneficiary_allocations=data["beneficiary_allocations"], reason=data.get("reason", ""), idempotency_key=data.get("idempotency_key") or None), OLPolicySerializer, "Policy issued successfully", status.HTTP_201_CREATED)

    def _transition(self, request, operation):
        return _run(request, operation, OLPolicySerializer, "Policy transition completed successfully")

    @action(detail=True, methods=["post"])
    def lapse(self, request, pk=None):
        return self._transition(request, lambda: OrdinaryLifePolicyService.lapse_policy(self.get_object(), actor=request.user, as_of=request.data.get("as_of"), reason=request.data.get("reason", ""), idempotency_key=request.data.get("idempotency_key")))

    @action(detail=True, methods=["post"])
    def grace(self, request, pk=None):
        return self._transition(request, lambda: OrdinaryLifePolicyService.grace_policy(self.get_object(), actor=request.user, reason=request.data.get("reason", ""), idempotency_key=request.data.get("idempotency_key")))

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        return self._transition(request, lambda: OrdinaryLifePolicyService.reactivate_policy(self.get_object(), actor=request.user, reason=request.data.get("reason", ""), idempotency_key=request.data.get("idempotency_key")))

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._transition(request, lambda: OrdinaryLifePolicyService.cancel_policy(self.get_object(), actor=request.user, effective_date=request.data.get("effective_date"), reason=request.data.get("reason", ""), idempotency_key=request.data.get("idempotency_key")))

    @action(detail=True, methods=["post"])
    def mature(self, request, pk=None):
        return self._transition(request, lambda: OrdinaryLifePolicyService.mature_policy(self.get_object(), actor=request.user, as_of=request.data.get("as_of"), reason=request.data.get("reason", ""), idempotency_key=request.data.get("idempotency_key")))

    @action(detail=True, methods=["post"], url_path="request-endorsement")
    def request_endorsement(self, request, pk=None):
        serializer = OLEndorsementCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(request, serializer.errors)
        data = serializer.validated_data
        return _run(request, lambda: OrdinaryLifePolicyService.request_endorsement(self.get_object(), endorsement_type=data["endorsement_type"], requested_changes=data["requested_changes"], requested_effective_date=data["requested_effective_date"], actor=request.user, reason=data.get("reason", "")), OLEndorsementSerializer, "Endorsement requested successfully", status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="request-renewal")
    def request_renewal(self, request, pk=None):
        serializer = OLPolicyRenewalCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(request, serializer.errors)
        data = serializer.validated_data
        return _run(request, lambda: OrdinaryLifePolicyService.request_renewal(self.get_object(), requested_effective_date=data["requested_effective_date"], new_end_date=data["new_end_date"], actor=request.user, reason=data.get("reason", "")), OLPolicyRenewalSerializer, "Renewal requested successfully", status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="request-reinstatement")
    def request_reinstatement(self, request, pk=None):
        serializer = OLReinstatementCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(request, serializer.errors)
        data = serializer.validated_data
        return _run(request, lambda: OrdinaryLifePolicyService.request_reinstatement(self.get_object(), requested_effective_date=data["requested_effective_date"], actor=request.user, reason=data.get("reason", "")), OLReinstatementRequestSerializer, "Reinstatement requested successfully", status.HTTP_201_CREATED)


class OLEndorsementApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLEndorsement.objects.select_related("policy__policyholder_partner", "created_by", "approved_by", "applied_transaction")
    serializer_class = OLEndorsementSerializer
    partner_scope_lookups = ("policy__policyholder_partner", "policy__life_assured_partner", "policy__agent")

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        return _run(request, lambda: OrdinaryLifePolicyService.submit_endorsement(self.get_object(), actor=request.user, reason=request.data.get("reason", "")), OLEndorsementSerializer, "Endorsement submitted successfully")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return _run(request, lambda: OrdinaryLifePolicyService.approve_endorsement(self.get_object(), actor=request.user, reason=request.data.get("reason", "")), OLEndorsementSerializer, "Endorsement approved successfully")

    @action(detail=True, methods=["post"])
    def apply(self, request, pk=None):
        return _run(request, lambda: OrdinaryLifePolicyService.apply_endorsement(self.get_object(), actor=request.user, reason=request.data.get("reason", ""), idempotency_key=request.data.get("idempotency_key")), OLEndorsementSerializer, "Endorsement applied successfully")


class OLPolicyRenewalApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLPolicyRenewal.objects.select_related("policy__policyholder_partner", "created_by", "approved_by", "payment_obligation")
    serializer_class = OLPolicyRenewalSerializer
    partner_scope_lookups = ("policy__policyholder_partner", "policy__life_assured_partner", "policy__agent")

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        return _run(request, lambda: OrdinaryLifePolicyService.submit_renewal(self.get_object(), actor=request.user, reason=request.data.get("reason", "")), OLPolicyRenewalSerializer, "Renewal submitted successfully")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return _run(request, lambda: OrdinaryLifePolicyService.approve_renewal(self.get_object(), actor=request.user, reason=request.data.get("reason", "")), OLPolicyRenewalSerializer, "Renewal approved successfully")

    @action(detail=True, methods=["post"])
    def apply(self, request, pk=None):
        return _run(request, lambda: OrdinaryLifePolicyService.apply_renewal(self.get_object(), actor=request.user, reason=request.data.get("reason", ""), idempotency_key=request.data.get("idempotency_key")), OLPolicyRenewalSerializer, "Renewal applied successfully")


class OLReinstatementRequestApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLReinstatementRequest.objects.select_related("policy__policyholder_partner", "created_by", "approved_by", "payment_obligation")
    serializer_class = OLReinstatementRequestSerializer
    partner_scope_lookups = ("policy__policyholder_partner", "policy__life_assured_partner", "policy__agent")

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        return _run(request, lambda: OrdinaryLifePolicyService.submit_reinstatement(self.get_object(), actor=request.user, reason=request.data.get("reason", "")), OLReinstatementRequestSerializer, "Reinstatement submitted successfully")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return _run(request, lambda: OrdinaryLifePolicyService.approve_reinstatement(self.get_object(), actor=request.user, reason=request.data.get("reason", "")), OLReinstatementRequestSerializer, "Reinstatement approved successfully")

    @action(detail=True, methods=["post"])
    def apply(self, request, pk=None):
        return _run(request, lambda: OrdinaryLifePolicyService.apply_reinstatement(self.get_object(), actor=request.user, reason=request.data.get("reason", ""), idempotency_key=request.data.get("idempotency_key")), OLReinstatementRequestSerializer, "Reinstatement applied successfully")


class OLDocumentApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLDocumentRecord.objects.select_related("proposal__application__partner", "policy__policyholder_partner", "uploaded_by", "verified_by", "rejected_by")
    serializer_class = OLDocumentRecordSerializer
    partner_scope_lookups = ("proposal__application__partner", "policy__policyholder_partner", "policy__life_assured_partner", "policy__agent")

    @action(detail=False, methods=["post"], url_path="create-document")
    def create_document(self, request):
        serializer = OLDocumentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(request, serializer.errors)
        data = serializer.validated_data
        return _run(request, lambda: OrdinaryLifeOperationsService.create_document(proposal=OLProposal.objects.get(pk=data["proposal"]) if data.get("proposal") else None, policy=OLPolicy.objects.get(pk=data["policy"]) if data.get("policy") else None, document_type=data["document_type"], file_reference=data.get("file_reference", ""), metadata=data.get("metadata") or {}, idempotency_key=data.get("idempotency_key") or None, actor=request.user), OLDocumentRecordSerializer, "Document created successfully", status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def upload(self, request, pk=None):
        return _run(request, lambda: OrdinaryLifeOperationsService.upload_document(self.get_object(), file_reference=request.data.get("file_reference", ""), actor=request.user, metadata=request.data.get("metadata"), reason=request.data.get("reason", "")), OLDocumentRecordSerializer, "Document uploaded successfully")

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        return _run(request, lambda: OrdinaryLifeOperationsService.verify_document(self.get_object(), actor=request.user, reason=request.data.get("reason", "")), OLDocumentRecordSerializer, "Document verified successfully")

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return _run(request, lambda: OrdinaryLifeOperationsService.reject_document(self.get_object(), actor=request.user, reason=request.data.get("reason", "")), OLDocumentRecordSerializer, "Document rejected successfully")

    @action(detail=True, methods=["post"], url_path="submit-verification")
    def submit_verification(self, request, pk=None):
        return _run(request, lambda: OrdinaryLifeOperationsService.submit_document_verification(self.get_object(), actor=request.user, comments=request.data.get("comments", "")), None, "Document verification submitted successfully", status.HTTP_201_CREATED)


class OLNoteApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLNote.objects.select_related("proposal__application__partner", "policy__policyholder_partner", "created_by")
    serializer_class = OLNoteSerializer
    partner_scope_lookups = ("proposal__application__partner", "policy__policyholder_partner", "policy__life_assured_partner", "policy__agent")

    @action(detail=False, methods=["post"], url_path="add-note")
    def add_note(self, request):
        serializer = OLNoteCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(request, serializer.errors)
        data = serializer.validated_data
        return _run(request, lambda: OrdinaryLifeOperationsService.add_note(proposal=OLProposal.objects.get(pk=data["proposal"]) if data.get("proposal") else None, policy=OLPolicy.objects.get(pk=data["policy"]) if data.get("policy") else None, content=data["content"], is_internal=data.get("is_internal", True), idempotency_key=data.get("idempotency_key") or None, actor=request.user), OLNoteSerializer, "Note added successfully", status.HTTP_201_CREATED)


class OLWorkflowEventApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLWorkflowEvent.objects.select_related("actor")
    serializer_class = OLWorkflowEventReadSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("entity_type"):
            queryset = queryset.filter(entity_type=self.request.query_params["entity_type"])
        if self.request.query_params.get("entity_id"):
            queryset = queryset.filter(entity_id=self.request.query_params["entity_id"])
        return queryset


class OLPolicyTransactionApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLPolicyTransaction.objects.select_related("policy__policyholder_partner", "created_by")
    serializer_class = OLPolicyTransactionSerializer
    partner_scope_lookups = ("policy__policyholder_partner", "policy__life_assured_partner", "policy__agent")


class OLPolicyStatusHistoryApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLPolicyStatusHistory.objects.select_related("policy__policyholder_partner", "actor")
    serializer_class = OLPolicyStatusHistorySerializer
    partner_scope_lookups = ("policy__policyholder_partner", "policy__life_assured_partner", "policy__agent")


class OLPremiumScheduleApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLPremiumSchedule.objects.select_related("policy__policyholder_partner")
    serializer_class = OLPremiumScheduleSerializer
    partner_scope_lookups = ("policy__policyholder_partner", "policy__life_assured_partner", "policy__agent")


class OLPremiumInstallmentApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLPremiumInstallment.objects.select_related("schedule__policy__policyholder_partner")
    serializer_class = OLPremiumInstallmentSerializer
    partner_scope_lookups = ("schedule__policy__policyholder_partner", "schedule__policy__life_assured_partner", "schedule__policy__agent")


class OLPolicyPartyApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLPolicyParty.objects.select_related("policy__policyholder_partner", "partner", "legacy_client")
    serializer_class = OLPolicyPartySerializer
    partner_scope_lookups = ("policy__policyholder_partner", "policy__life_assured_partner", "policy__agent")


class OLBeneficiaryAllocationApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLBeneficiaryAllocation.objects.select_related("policy__policyholder_partner", "beneficiary")
    serializer_class = OLBeneficiaryAllocationSerializer
    partner_scope_lookups = ("policy__policyholder_partner", "policy__life_assured_partner", "policy__agent")


class OLApprovalApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = ApprovalRequest.objects.filter(module=MODULE_CODE).select_related("submitted_by", "reviewed_by")
    serializer_class = None

    def list(self, request, *args, **kwargs):
        return _response(request, [_approval_data(item) for item in self.get_queryset().order_by("-submitted_at")])

    def retrieve(self, request, *args, **kwargs):
        return _response(request, _approval_data(self.get_object()))

    @action(detail=False, methods=["post"])
    def complete(self, request):
        approval_id = request.data.get("approval_id")
        if not approval_id:
            return _error(request, {"approval_id": ["This field is required."]})
        return _run(request, lambda: OrdinaryLifeOperationsService.complete_policy_approval(approval_id, reviewer=request.user, comments=request.data.get("comments", "")), None, "Approval completed successfully")


class OLAuditHistoryApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = AuditLog.objects.filter(app_label=MODULE_CODE).select_related("user")
    serializer_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("model_name"):
            queryset = queryset.filter(model_name=self.request.query_params["model_name"].lower())
        if self.request.query_params.get("object_id"):
            queryset = queryset.filter(object_id=str(self.request.query_params["object_id"]))
        if self.request.query_params.get("action"):
            queryset = queryset.filter(action=self.request.query_params["action"].upper())
        return queryset

    def _data(self, event):
        return {
            "id": str(event.pk),
            "action": event.action,
            "app_label": event.app_label,
            "model_name": event.model_name,
            "object_id": event.object_id,
            "object_repr": event.object_repr,
            "before_state": event.before_state,
            "after_state": event.after_state,
            "changed_fields": event.changed_fields,
            "reason": event.reason,
            "source_channel": event.source_channel,
            "correlation_id": event.correlation_id,
            "user_id": str(event.user_id) if event.user_id else None,
            "created_at": event.created_at,
        }

    def list(self, request, *args, **kwargs):
        return _response(request, [self._data(event) for event in self.get_queryset()])

    def retrieve(self, request, *args, **kwargs):
        return _response(request, self._data(self.get_object()))


class OLLoanApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLLoan.objects.select_related("policy")
    serializer_class = OLLoanSerializer


class OLWithdrawalApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLWithdrawal.objects.select_related("policy")
    serializer_class = OLWithdrawalSerializer


class OLClaimApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLClaim.objects.select_related("policy")
    serializer_class = OLClaimSerializer


class OLCommitmentApiViewSet(OrdinaryLifeReadOnlyViewSet):
    queryset = OLCommitment.objects.select_related("proposal")
    serializer_class = OLCommitmentSerializer
