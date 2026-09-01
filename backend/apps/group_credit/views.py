"""
Group Credit — REST API Views

ViewSets organized by architectural layer with workflow actions
for quotation approval, scheme conversion, claim processing, etc.
All responses follow the ZIC standard envelope: {success, status_code, message, data, meta}.
"""

import logging

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from apps.core.pagination import StandardPagination

from apps.group_credit.models import (
    GCLookupValue,
    # Layer 1 — Parameters
    GCSchemeType, GCSchemeStatus, GCSchemeMemberStatus, GCSchemeRenewalStatus,
    GCSchemePremiumRate, GCHealthQuestion, GCHealthQuestionnaire,
    # Layer 2 — Products & Riders
    GCSubProduct, GCProduct, GCRider, GCRiderRate,
    # Layer 3 — Quotations
    GCQuotation, GCQuotationCategory, GCQuotationRider,
    # Layer 4 — Schemes & Members
    GCScheme, GCSchemeCategory, GCSchemeRider, GCSchemeMember,
    GCSchemeMemberDependent,
    # Layer 5 — Medical UW
    GCMedicalCode, GCMedicalLimit, GCUnderwritingDecision,
    GCPersonalHabit, GCMedicalHistory, GCMedicalFacility,
    GCMedicalPractitioner, GCMedicalCase,
    # Layer 6 — Claims
    GCClaimType, GCClaimReason, GCClaimStatus, GCDischargeType,
    GCCorrespondentType, GCClaim, GCClaimInstallment, GCMedicalInvoice,
    # Layer 7 — Renewals
    GCSchemeRenewal,
)
from apps.group_credit.serializers import (
    GCLookupValueSerializer,
    # Layer 1
    GCSchemeTypeSerializer, GCSchemeStatusSerializer,
    GCSchemeMemberStatusSerializer, GCSchemeRenewalStatusSerializer,
    GCSchemePremiumRateSerializer, GCHealthQuestionSerializer,
    GCHealthQuestionnaireSerializer,
    # Layer 2
    GCSubProductSerializer, GCProductListSerializer, GCProductDetailSerializer,
    GCRiderSerializer, GCRiderRateSerializer,
    # Layer 3
    GCQuotationListSerializer, GCQuotationDetailSerializer,
    GCQuotationCreateSerializer,
    GCQuotationCategorySerializer, GCQuotationRiderSerializer,
    # Layer 4
    GCSchemeListSerializer, GCSchemeDetailSerializer, GCSchemeCreateSerializer,
    GCSchemeCategorySerializer, GCSchemeRiderSerializer,
    GCSchemeMemberListSerializer, GCSchemeMemberDetailSerializer,
    GCSchemeMemberCreateSerializer, GCSchemeMemberDependentSerializer,
    # Layer 5
    GCMedicalCodeSerializer, GCMedicalLimitSerializer,
    GCUnderwritingDecisionSerializer, GCPersonalHabitSerializer,
    GCMedicalHistorySerializer, GCMedicalFacilitySerializer,
    GCMedicalPractitionerSerializer,
    GCMedicalCaseListSerializer, GCMedicalCaseDetailSerializer,
    GCMedicalCaseCreateSerializer,
    # Layer 6
    GCClaimTypeSerializer, GCClaimReasonSerializer, GCClaimStatusSerializer,
    GCDischargeTypeSerializer, GCCorrespondentTypeSerializer,
    GCClaimListSerializer, GCClaimDetailSerializer, GCClaimCreateSerializer,
    GCClaimInstallmentSerializer, GCMedicalInvoiceSerializer,
    # Layer 7
    GCSchemeRenewalListSerializer, GCSchemeRenewalDetailSerializer,
    GCSchemeRenewalCreateSerializer,
)
from apps.group_credit.filters import (
    GCQuotationFilter, GCSchemeFilter, GCSchemeMemberFilter,
    GCClaimFilter, GCMedicalCaseFilter,
)
from apps.group_credit.services import GCNumberingService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Standard response wrapper (matches partner_onboarding pattern)
# ---------------------------------------------------------------------------


def _response(data=None, message="", status_code=200):
    return Response({
        "success": status_code < 400,
        "status_code": status_code,
        "message": message,
        "data": data,
        "meta": {"timestamp": timezone.now().isoformat(), "version": "v1"},
    }, status=status_code)


# =============================================================================
# LAYER 1 — SETUP & PARAMETERS
# =============================================================================

class GCLookupValueViewSet(viewsets.ModelViewSet):
    queryset = GCLookupValue.objects.all()
    serializer_class = GCLookupValueSerializer
    filterset_fields = ["category", "is_active"]
    search_fields = ["value", "label", "category"]
    ordering_fields = ["category", "sort_order", "label"]


class GCSchemeTypeViewSet(viewsets.ModelViewSet):
    queryset = GCSchemeType.objects.all()
    serializer_class = GCSchemeTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]


class GCSchemeStatusViewSet(viewsets.ModelViewSet):
    queryset = GCSchemeStatus.objects.all()
    serializer_class = GCSchemeStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    ordering_fields = ["sort_order", "name"]
    ordering = ["sort_order"]


class GCSchemeMemberStatusViewSet(viewsets.ModelViewSet):
    queryset = GCSchemeMemberStatus.objects.all()
    serializer_class = GCSchemeMemberStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    ordering = ["name"]


class GCSchemeRenewalStatusViewSet(viewsets.ModelViewSet):
    queryset = GCSchemeRenewalStatus.objects.all()
    serializer_class = GCSchemeRenewalStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    ordering = ["name"]


class GCSchemePremiumRateViewSet(viewsets.ModelViewSet):
    queryset = GCSchemePremiumRate.objects.all()
    serializer_class = GCSchemePremiumRateSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["name"]
    filterset_fields = ["rate_type", "gender", "is_active"]
    ordering = ["rate_type", "age_band_start"]


class GCHealthQuestionViewSet(viewsets.ModelViewSet):
    queryset = GCHealthQuestion.objects.all()
    serializer_class = GCHealthQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "question_text"]
    filterset_fields = ["question_type", "category", "is_active"]
    ordering = ["category", "sort_order"]


class GCHealthQuestionnaireViewSet(viewsets.ModelViewSet):
    queryset = GCHealthQuestionnaire.objects.prefetch_related("questions").all()
    serializer_class = GCHealthQuestionnaireSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    filterset_fields = ["is_active"]
    ordering = ["-effective_date"]


# =============================================================================
# LAYER 2 — PRODUCT & RIDER VIEWSETS
# =============================================================================


class GCSubProductViewSet(viewsets.ModelViewSet):
    queryset = GCSubProduct.objects.all()
    serializer_class = GCSubProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    ordering = ["name"]


class GCProductViewSet(viewsets.ModelViewSet):
    queryset = GCProduct.objects.select_related("sub_product", "scheme_type_ref").all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    filterset_fields = ["scheme_type_ref", "sub_product", "is_active", "currency", "premium_basis", "requires_medical"]
    ordering = ["scheme_type_ref", "name"]

    def get_serializer_class(self):
        if self.action == "list":
            return GCProductListSerializer
        return GCProductDetailSerializer


class GCRiderViewSet(viewsets.ModelViewSet):
    queryset = GCRider.objects.prefetch_related("rates").all()
    serializer_class = GCRiderSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    filterset_fields = ["rider_type", "rider_category", "benefit_type", "requires_underwriting", "is_mandatory", "is_active"]
    ordering = ["rider_type", "name"]


class GCRiderRateViewSet(viewsets.ModelViewSet):
    queryset = GCRiderRate.objects.select_related("rider", "product_ref").all()
    serializer_class = GCRiderRateSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filterset_fields = ["rider", "product_ref", "rate_type", "gender", "is_active"]
    ordering = ["rider", "age_band_start"]


# =============================================================================
# LAYER 3 — QUOTATION VIEWSETS
# =============================================================================


class GCQuotationViewSet(viewsets.ModelViewSet):
    queryset = GCQuotation.objects.select_related(
        "partner", "product", "scheme_type", "prepared_by", "approved_by",
    ).prefetch_related("categories", "riders").all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filterset_class = GCQuotationFilter
    search_fields = ["quotation_number", "partner__company_name"]
    ordering_fields = ["created_at", "quotation_date", "total_annual_premium", "status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return GCQuotationListSerializer
        if self.action == "create":
            return GCQuotationCreateSerializer
        return GCQuotationDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return _response(data=serializer.data, message="Quotation retrieved successfully.")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return _response(data=serializer.data, message="Quotations retrieved successfully.")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quotation = serializer.save()
        return _response(
            data=GCQuotationDetailSerializer(quotation).data,
            message="Quotation created successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        quotation = self.get_object()
        if quotation.status not in ("SUBMITTED", "UNDER_REVIEW"):
            return _response(
                message=f"Cannot approve a quotation in '{quotation.get_status_display()}' status.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        quotation.status = "APPROVED"
        quotation.approved_by = request.user
        quotation.approved_at = timezone.now()
        quotation.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        return _response(
            data=GCQuotationDetailSerializer(quotation).data,
            message="Quotation approved successfully.",
        )

    @action(detail=True, methods=["post"], url_path="decline")
    def decline(self, request, pk=None):
        quotation = self.get_object()
        if quotation.status in ("CONVERTED", "EXPIRED"):
            return _response(
                message=f"Cannot decline a quotation in '{quotation.get_status_display()}' status.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        quotation.status = "DECLINED"
        quotation.notes = request.data.get("notes", quotation.notes)
        quotation.save(update_fields=["status", "notes", "updated_at"])
        return _response(
            data=GCQuotationDetailSerializer(quotation).data,
            message="Quotation declined.",
        )

    @action(detail=True, methods=["post"], url_path="convert-to-scheme")
    def convert_to_scheme(self, request, pk=None):
        quotation = self.get_object()
        if quotation.status != "APPROVED":
            return _response(
                message="Only approved quotations can be converted to schemes.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if hasattr(quotation, 'converted_scheme') and quotation.converted_scheme:
            return _response(
                message=f"Quotation already converted to scheme {quotation.converted_scheme.scheme_number}.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        active_status = GCSchemeStatus.objects.filter(code="ACTIVE").first()
        if not active_status:
            active_status = GCSchemeStatus.objects.first()

        scheme = GCScheme.objects.create(
            scheme_number=GCNumberingService.generate_scheme_number(),
            partner=quotation.partner,
            product=quotation.product,
            scheme_type=quotation.scheme_type,
            status=active_status,
            converted_from_quotation=quotation,
            inception_date=request.data.get("inception_date", timezone.now().date()),
            expiry_date=request.data.get("expiry_date"),
            free_cover_limit=quotation.free_cover_limit,
            experience_rating_factor=quotation.experience_rating_factor,
            commission_rate=quotation.commission_rate,
            admin_loading_rate=quotation.admin_loading_rate,
            total_members=quotation.total_members,
            total_sum_assured=quotation.total_loan_amount,
            total_annual_premium=quotation.total_annual_premium,
            created_by=request.user,
        )

        for cat in quotation.categories.all():
            GCSchemeCategory.objects.create(
                scheme=scheme,
                category_name=cat.category_name,
                description=cat.description,
                flat_loan_amount=cat.flat_loan_amount,
                premium_rate_per_mille=cat.premium_rate_per_mille,
                sort_order=cat.sort_order,
            )

        for qr in quotation.riders.all():
            GCSchemeRider.objects.create(
                scheme=scheme,
                rider=qr.rider,
                rate_per_mille=qr.rate_per_mille,
            )

        quotation.status = "CONVERTED"
        quotation.save(update_fields=["status", "updated_at"])

        return _response(
            data=GCSchemeDetailSerializer(scheme).data,
            message=f"Quotation converted to scheme {scheme.scheme_number}.",
            status_code=status.HTTP_201_CREATED,
        )


class GCQuotationCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = GCQuotationCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        quotation_pk = self.kwargs.get("quotation_pk")
        return GCQuotationCategory.objects.filter(quotation_id=quotation_pk)

    def perform_create(self, serializer):
        serializer.save(quotation_id=self.kwargs.get("quotation_pk"))


class GCQuotationRiderViewSet(viewsets.ModelViewSet):
    serializer_class = GCQuotationRiderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        quotation_pk = self.kwargs.get("quotation_pk")
        return GCQuotationRider.objects.filter(
            quotation_id=quotation_pk
        ).select_related("rider")

    def perform_create(self, serializer):
        serializer.save(quotation_id=self.kwargs.get("quotation_pk"))


# =============================================================================
# LAYER 4 — SCHEME & BORROWER VIEWSETS
# =============================================================================


class GCSchemeViewSet(viewsets.ModelViewSet):
    queryset = GCScheme.objects.select_related(
        "partner", "product", "scheme_type", "status",
        "converted_from_quotation", "created_by",
    ).prefetch_related("categories", "riders").all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filterset_class = GCSchemeFilter
    search_fields = ["scheme_number", "partner__company_name"]
    ordering_fields = ["created_at", "inception_date", "expiry_date", "total_annual_premium"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return GCSchemeListSerializer
        if self.action == "create":
            return GCSchemeCreateSerializer
        return GCSchemeDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return _response(data=serializer.data, message="Scheme retrieved successfully.")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return _response(data=serializer.data, message="Schemes retrieved successfully.")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scheme = serializer.save()
        return _response(
            data=GCSchemeDetailSerializer(scheme).data,
            message="Scheme created successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="dashboard-summary")
    def dashboard_summary(self, request):
        from django.db.models import Sum
        qs = GCScheme.objects.all()
        summary = {
            "total_schemes": qs.count(),
            "active_schemes": qs.filter(status__code="ACTIVE").count(),
            "total_members": qs.aggregate(t=Sum("total_members"))["t"] or 0,
            "total_premium": str(qs.aggregate(t=Sum("total_annual_premium"))["t"] or 0),
            "expiring_soon": qs.filter(
                expiry_date__lte=timezone.now().date() + timezone.timedelta(days=30),
                expiry_date__gte=timezone.now().date(),
            ).count(),
        }
        return _response(data=summary, message="Dashboard summary retrieved.")


class GCSchemeCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = GCSchemeCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        scheme_pk = self.kwargs.get("scheme_pk")
        return GCSchemeCategory.objects.filter(scheme_id=scheme_pk)

    def perform_create(self, serializer):
        serializer.save(scheme_id=self.kwargs.get("scheme_pk"))


class GCSchemeRiderViewSet(viewsets.ModelViewSet):
    serializer_class = GCSchemeRiderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        scheme_pk = self.kwargs.get("scheme_pk")
        return GCSchemeRider.objects.filter(
            scheme_id=scheme_pk
        ).select_related("rider")

    def perform_create(self, serializer):
        serializer.save(scheme_id=self.kwargs.get("scheme_pk"))


class GCSchemeMemberViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filterset_class = GCSchemeMemberFilter
    search_fields = ["member_number", "first_name", "surname", "loan_account_number"]
    ordering_fields = ["created_at", "surname", "loan_amount"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = GCSchemeMember.objects.select_related(
            "scheme", "category", "status",
        ).prefetch_related("dependents")
        scheme_pk = self.kwargs.get("scheme_pk")
        if scheme_pk:
            qs = qs.filter(scheme_id=scheme_pk)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return GCSchemeMemberListSerializer
        if self.action == "create":
            return GCSchemeMemberCreateSerializer
        return GCSchemeMemberDetailSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        scheme_pk = self.kwargs.get("scheme_pk")
        if scheme_pk:
            data["scheme"] = scheme_pk
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        member = serializer.save()
        return _response(
            data=GCSchemeMemberDetailSerializer(member).data,
            message="Borrower enrolled successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return _response(data=serializer.data, message="Borrower retrieved successfully.")


class GCSchemeMemberDependentViewSet(viewsets.ModelViewSet):
    serializer_class = GCSchemeMemberDependentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        member_pk = self.kwargs.get("member_pk")
        return GCSchemeMemberDependent.objects.filter(member_id=member_pk)

    def perform_create(self, serializer):
        serializer.save(member_id=self.kwargs.get("member_pk"))


# =============================================================================
# LAYER 5 — MEDICAL UNDERWRITING VIEWSETS
# =============================================================================


class GCMedicalCodeViewSet(viewsets.ModelViewSet):
    queryset = GCMedicalCode.objects.all()
    serializer_class = GCMedicalCodeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name", "icd10_code"]
    filterset_fields = ["category", "is_active"]
    ordering = ["code"]


class GCMedicalLimitViewSet(viewsets.ModelViewSet):
    queryset = GCMedicalLimit.objects.select_related("scheme_type_ref", "medical_code_ref", "product").all()
    serializer_class = GCMedicalLimitSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["scheme_type_ref__code", "scheme_type_ref__name", "medical_code_ref__code", "description"]
    filterset_fields = ["scheme_type_ref", "medical_code_ref", "product", "is_active"]
    ordering = ["age_min", "age_max"]


class GCUnderwritingDecisionViewSet(viewsets.ModelViewSet):
    queryset = GCUnderwritingDecision.objects.all()
    serializer_class = GCUnderwritingDecisionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    filterset_fields = ["requires_review", "is_active"]
    ordering = ["display_order"]


class GCPersonalHabitViewSet(viewsets.ModelViewSet):
    queryset = GCPersonalHabit.objects.all()
    serializer_class = GCPersonalHabitSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    filterset_fields = ["habit_category", "underwriting_impact", "is_active"]
    ordering = ["habit_category", "name"]


class GCMedicalHistoryViewSet(viewsets.ModelViewSet):
    queryset = GCMedicalHistory.objects.all()
    serializer_class = GCMedicalHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    filterset_fields = ["condition_category", "severity", "exclusion_flag", "is_active"]
    ordering = ["condition_category", "name"]


class GCMedicalFacilityViewSet(viewsets.ModelViewSet):
    queryset = GCMedicalFacility.objects.select_related("partner_ref").all()
    serializer_class = GCMedicalFacilitySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name", "city"]
    filterset_fields = ["facility_type", "approval_status", "partner_ref", "is_active", "region"]
    ordering = ["name"]


class GCMedicalPractitionerViewSet(viewsets.ModelViewSet):
    queryset = GCMedicalPractitioner.objects.select_related("facility", "partner_ref").all()
    serializer_class = GCMedicalPractitionerSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name", "first_name", "last_name", "specialization"]
    filterset_fields = ["approval_status", "facility", "partner_ref", "is_active"]
    ordering = ["name"]


class GCMedicalCaseViewSet(viewsets.ModelViewSet):
    queryset = GCMedicalCase.objects.select_related(
        "member", "facility", "practitioner", "decision",
        "questionnaire", "decided_by",
    ).prefetch_related(
        "diagnosis_codes", "personal_habits", "medical_history",
    ).all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filterset_class = GCMedicalCaseFilter
    search_fields = ["case_number", "member__surname"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return GCMedicalCaseListSerializer
        if self.action == "create":
            return GCMedicalCaseCreateSerializer
        return GCMedicalCaseDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case = serializer.save()
        return _response(
            data=GCMedicalCaseDetailSerializer(case).data,
            message="Medical case created successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="make-decision")
    def make_decision(self, request, pk=None):
        case = self.get_object()
        decision_id = request.data.get("decision")
        if not decision_id:
            return _response(message="Decision is required.", status_code=400)

        try:
            decision = GCUnderwritingDecision.objects.get(id=decision_id)
        except GCUnderwritingDecision.DoesNotExist:
            return _response(message="Invalid decision.", status_code=400)

        case.decision = decision
        case.decision_notes = request.data.get("decision_notes", "")
        case.premium_loading_percent = request.data.get("premium_loading_percent", 0)
        case.exclusions = request.data.get("exclusions", [])
        case.decided_by = request.user
        case.decided_at = timezone.now()
        case.status = "COMPLETED"
        case.save()

        # Update member UW status
        member = case.member
        if decision.code == "STANDARD":
            member.uw_status = "STANDARD"
        elif decision.code == "PREMIUM_LOADING":
            member.uw_status = "LOADED"
            member.premium_loading_percent = case.premium_loading_percent
        elif decision.code == "EXCLUSION":
            member.uw_status = "EXCLUDED"
        elif decision.code == "DECLINE":
            member.uw_status = "DECLINED"
        member.save(update_fields=["uw_status", "premium_loading_percent", "updated_at"])

        return _response(
            data=GCMedicalCaseDetailSerializer(case).data,
            message=f"Underwriting decision recorded: {decision.name}",
        )


# =============================================================================
# LAYER 6 — CLAIMS VIEWSETS
# =============================================================================


class GCClaimTypeViewSet(viewsets.ModelViewSet):
    queryset = GCClaimType.objects.all()
    serializer_class = GCClaimTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    filterset_fields = ["category", "calculation_basis", "requires_document_check", "is_active"]
    ordering = ["name"]


class GCClaimReasonViewSet(viewsets.ModelViewSet):
    queryset = GCClaimReason.objects.select_related("claim_type").all()
    serializer_class = GCClaimReasonSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    filterset_fields = ["claim_type", "category", "is_active"]
    ordering = ["claim_type", "name"]


class GCClaimStatusViewSet(viewsets.ModelViewSet):
    queryset = GCClaimStatus.objects.all()
    serializer_class = GCClaimStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    filterset_fields = ["is_terminal", "is_active"]
    ordering = ["display_order"]


class GCDischargeTypeViewSet(viewsets.ModelViewSet):
    queryset = GCDischargeType.objects.all()
    serializer_class = GCDischargeTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name", "template_code"]
    filterset_fields = ["is_active"]
    ordering = ["name"]


class GCCorrespondentTypeViewSet(viewsets.ModelViewSet):
    queryset = GCCorrespondentType.objects.all()
    serializer_class = GCCorrespondentTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    filterset_fields = ["category", "communication_channel", "purpose", "is_active"]
    ordering = ["name"]


class GCClaimViewSet(viewsets.ModelViewSet):
    queryset = GCClaim.objects.select_related(
        "scheme", "member", "claim_type", "claim_reason", "status",
        "discharge_type", "registered_by", "assessed_by", "approved_by", "paid_by",
    ).prefetch_related("installments").all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filterset_class = GCClaimFilter
    search_fields = ["claim_number", "member__surname", "claimant_name"]
    ordering_fields = ["created_at", "incident_date", "claim_amount"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return GCClaimListSerializer
        if self.action == "create":
            return GCClaimCreateSerializer
        return GCClaimDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = serializer.save()
        return _response(
            data=GCClaimDetailSerializer(claim).data,
            message="Claim registered successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return _response(data=serializer.data, message="Claim retrieved successfully.")

    @action(detail=True, methods=["post"], url_path="assess")
    def assess(self, request, pk=None):
        claim = self.get_object()
        claim.assessed_by = request.user
        claim.assessed_at = timezone.now()
        claim.assessment_notes = request.data.get("assessment_notes", "")
        claim.claim_amount = request.data.get("claim_amount", claim.claim_amount)
        assessed_status = GCClaimStatus.objects.filter(code="ASSESSED").first()
        if assessed_status:
            claim.status = assessed_status
        claim.save()
        return _response(
            data=GCClaimDetailSerializer(claim).data,
            message="Claim assessed successfully.",
        )

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        claim = self.get_object()
        claim.approved_by = request.user
        claim.approved_at = timezone.now()
        claim.approved_amount = request.data.get("approved_amount", claim.claim_amount)
        approved_status = GCClaimStatus.objects.filter(code="APPROVED").first()
        if approved_status:
            claim.status = approved_status
        claim.save()
        return _response(
            data=GCClaimDetailSerializer(claim).data,
            message="Claim approved successfully.",
        )

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        claim = self.get_object()
        claim.rejection_reason = request.data.get("rejection_reason", "")
        rejected_status = GCClaimStatus.objects.filter(code="REJECTED").first()
        if rejected_status:
            claim.status = rejected_status
        claim.save()
        return _response(
            data=GCClaimDetailSerializer(claim).data,
            message="Claim rejected.",
        )

    @action(detail=True, methods=["post"], url_path="pay")
    def pay(self, request, pk=None):
        claim = self.get_object()
        amount = request.data.get("amount", claim.approved_amount)
        claim.paid_amount = claim.paid_amount + amount
        claim.paid_by = request.user
        claim.paid_at = timezone.now()
        if claim.paid_amount >= claim.approved_amount:
            paid_status = GCClaimStatus.objects.filter(code="PAID").first()
            if paid_status:
                claim.status = paid_status
        claim.save()
        return _response(
            data=GCClaimDetailSerializer(claim).data,
            message=f"Payment of {amount} recorded.",
        )


class GCClaimInstallmentViewSet(viewsets.ModelViewSet):
    serializer_class = GCClaimInstallmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        claim_pk = self.kwargs.get("claim_pk")
        return GCClaimInstallment.objects.filter(claim_id=claim_pk)

    def perform_create(self, serializer):
        serializer.save(claim_id=self.kwargs.get("claim_pk"))


class GCMedicalInvoiceViewSet(viewsets.ModelViewSet):
    queryset = GCMedicalInvoice.objects.select_related(
        "claim", "member", "facility",
    ).all()
    serializer_class = GCMedicalInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["invoice_number", "facility__name"]
    filterset_fields = ["status", "facility"]
    ordering = ["-invoice_date"]


# =============================================================================
# LAYER 7 — RENEWAL VIEWSETS
# =============================================================================


class GCSchemeRenewalViewSet(viewsets.ModelViewSet):
    queryset = GCSchemeRenewal.objects.select_related(
        "scheme", "renewal_status", "initiated_by", "approved_by",
    ).all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["renewal_number", "scheme__scheme_number"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return GCSchemeRenewalListSerializer
        if self.action == "create":
            return GCSchemeRenewalCreateSerializer
        return GCSchemeRenewalDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        renewal = serializer.save()
        return _response(
            data=GCSchemeRenewalDetailSerializer(renewal).data,
            message="Renewal initiated successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="approve")
    def approve_renewal(self, request, pk=None):
        renewal = self.get_object()
        renewal.approved_by = request.user
        renewal.approved_at = timezone.now()
        renewed_status = GCSchemeRenewalStatus.objects.filter(code="RENEWED").first()
        if renewed_status:
            renewal.renewal_status = renewed_status
        renewal.save()

        scheme = renewal.scheme
        if renewal.proposed_renewal_date:
            scheme.inception_date = renewal.current_expiry_date
            scheme.expiry_date = renewal.proposed_renewal_date
        if renewal.proposed_premium:
            scheme.total_annual_premium = renewal.proposed_premium
        if renewal.proposed_experience_factor:
            scheme.experience_rating_factor = renewal.proposed_experience_factor
        scheme.save()

        return _response(
            data=GCSchemeRenewalDetailSerializer(renewal).data,
            message="Renewal approved and scheme updated.",
        )
