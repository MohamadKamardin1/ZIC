"""
Group Life — REST API Views

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

from apps.group_life.models import (
    # Layer 1 — Parameters
    GLSchemeType, GLSchemeStatus, GLSchemeMemberStatus, GLSchemeRenewalStatus,
    GLSchemePremiumRate, GLHealthQuestion, GLHealthQuestionnaire,
    # Layer 2 — Products & Riders
    GLSubProduct, GLProduct, GLRider, GLRiderRate,
    # Layer 3 — Quotations
    GLQuotation, GLQuotationCategory, GLQuotationRider,
    # Layer 4 — Schemes & Members
    GLScheme, GLSchemeCategory, GLSchemeRider, GLSchemeMember,
    GLSchemeMemberDependent,
    # Layer 5 — Medical UW
    GLMedicalCode, GLMedicalLimit, GLUnderwritingDecision,
    GLPersonalHabit, GLMedicalHistory, GLMedicalFacility,
    GLMedicalPractitioner, GLMedicalCase,
    # Layer 6 — Claims
    GLClaimType, GLClaimReason, GLClaimStatus, GLDischargeType,
    GLCorrespondentType, GLClaim, GLClaimInstallment, GLMedicalInvoice,
    # Layer 7 — Renewals
    GLSchemeRenewal,
)
from apps.group_life.serializers import (
    # Layer 1
    GLSchemeTypeSerializer, GLSchemeStatusSerializer,
    GLSchemeMemberStatusSerializer, GLSchemeRenewalStatusSerializer,
    GLSchemePremiumRateSerializer, GLHealthQuestionSerializer,
    GLHealthQuestionnaireSerializer,
    # Layer 2
    GLSubProductSerializer, GLProductListSerializer, GLProductDetailSerializer,
    GLRiderSerializer, GLRiderRateSerializer,
    # Layer 3
    GLQuotationListSerializer, GLQuotationDetailSerializer,
    GLQuotationCreateSerializer,
    GLQuotationCategorySerializer, GLQuotationRiderSerializer,
    # Layer 4
    GLSchemeListSerializer, GLSchemeDetailSerializer, GLSchemeCreateSerializer,
    GLSchemeCategorySerializer, GLSchemeRiderSerializer,
    GLSchemeMemberListSerializer, GLSchemeMemberDetailSerializer,
    GLSchemeMemberCreateSerializer, GLSchemeMemberDependentSerializer,
    # Layer 5
    GLMedicalCodeSerializer, GLMedicalLimitSerializer,
    GLUnderwritingDecisionSerializer, GLPersonalHabitSerializer,
    GLMedicalHistorySerializer, GLMedicalFacilitySerializer,
    GLMedicalPractitionerSerializer,
    GLMedicalCaseListSerializer, GLMedicalCaseDetailSerializer,
    GLMedicalCaseCreateSerializer,
    # Layer 6
    GLClaimTypeSerializer, GLClaimReasonSerializer, GLClaimStatusSerializer,
    GLDischargeTypeSerializer, GLCorrespondentTypeSerializer,
    GLClaimListSerializer, GLClaimDetailSerializer, GLClaimCreateSerializer,
    GLClaimInstallmentSerializer, GLMedicalInvoiceSerializer,
    # Layer 7
    GLSchemeRenewalListSerializer, GLSchemeRenewalDetailSerializer,
    GLSchemeRenewalCreateSerializer,
)
from apps.group_life.filters import (
    GLQuotationFilter, GLSchemeFilter, GLSchemeMemberFilter,
    GLClaimFilter, GLMedicalCaseFilter,
)
from apps.group_life.services import GLNumberingService

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
# LAYER 1 — PARAMETER / SETUP VIEWSETS
# =============================================================================


class GLSchemeTypeViewSet(viewsets.ModelViewSet):
    queryset = GLSchemeType.objects.all()
    serializer_class = GLSchemeTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]


class GLSchemeStatusViewSet(viewsets.ModelViewSet):
    queryset = GLSchemeStatus.objects.all()
    serializer_class = GLSchemeStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    ordering_fields = ["sort_order", "name"]
    ordering = ["sort_order"]


class GLSchemeMemberStatusViewSet(viewsets.ModelViewSet):
    queryset = GLSchemeMemberStatus.objects.all()
    serializer_class = GLSchemeMemberStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    ordering = ["name"]


class GLSchemeRenewalStatusViewSet(viewsets.ModelViewSet):
    queryset = GLSchemeRenewalStatus.objects.all()
    serializer_class = GLSchemeRenewalStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    ordering = ["name"]


class GLSchemePremiumRateViewSet(viewsets.ModelViewSet):
    queryset = GLSchemePremiumRate.objects.all()
    serializer_class = GLSchemePremiumRateSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["name"]
    filterset_fields = ["rate_type", "gender", "is_active"]
    ordering = ["rate_type", "age_band_start"]


class GLHealthQuestionViewSet(viewsets.ModelViewSet):
    queryset = GLHealthQuestion.objects.all()
    serializer_class = GLHealthQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "question_text"]
    filterset_fields = ["question_type", "category", "is_active"]
    ordering = ["category", "sort_order"]


class GLHealthQuestionnaireViewSet(viewsets.ModelViewSet):
    queryset = GLHealthQuestionnaire.objects.prefetch_related("questions").all()
    serializer_class = GLHealthQuestionnaireSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    filterset_fields = ["is_active"]
    ordering = ["-effective_date"]


# =============================================================================
# LAYER 2 — PRODUCT & RIDER VIEWSETS
# =============================================================================


class GLSubProductViewSet(viewsets.ModelViewSet):
    queryset = GLSubProduct.objects.all()
    serializer_class = GLSubProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    ordering = ["name"]


class GLProductViewSet(viewsets.ModelViewSet):
    queryset = GLProduct.objects.select_related("sub_product").all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    filterset_fields = ["sub_product", "is_active", "currency"]
    ordering = ["sub_product", "name"]

    def get_serializer_class(self):
        if self.action == "list":
            return GLProductListSerializer
        return GLProductDetailSerializer


class GLRiderViewSet(viewsets.ModelViewSet):
    queryset = GLRider.objects.prefetch_related("rates").all()
    serializer_class = GLRiderSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    filterset_fields = ["rider_type", "is_mandatory", "is_active"]
    ordering = ["rider_type", "name"]


class GLRiderRateViewSet(viewsets.ModelViewSet):
    queryset = GLRiderRate.objects.select_related("rider").all()
    serializer_class = GLRiderRateSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filterset_fields = ["rider", "gender", "is_active"]
    ordering = ["rider", "age_band_start"]


# =============================================================================
# LAYER 3 — QUOTATION VIEWSETS
# =============================================================================


class GLQuotationViewSet(viewsets.ModelViewSet):
    queryset = GLQuotation.objects.select_related(
        "partner", "product", "scheme_type", "prepared_by", "approved_by",
    ).prefetch_related("categories", "riders").all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filterset_class = GLQuotationFilter
    search_fields = ["quotation_number", "partner__company_name"]
    ordering_fields = ["created_at", "quotation_date", "total_annual_premium", "status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return GLQuotationListSerializer
        if self.action == "create":
            return GLQuotationCreateSerializer
        return GLQuotationDetailSerializer

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
            data=GLQuotationDetailSerializer(quotation).data,
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
            data=GLQuotationDetailSerializer(quotation).data,
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
            data=GLQuotationDetailSerializer(quotation).data,
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

        # Check if already converted
        if hasattr(quotation, 'converted_scheme') and quotation.converted_scheme:
            return _response(
                message=f"Quotation already converted to scheme {quotation.converted_scheme.scheme_number}.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Get ACTIVE status
        active_status = GLSchemeStatus.objects.filter(code="ACTIVE").first()
        if not active_status:
            active_status = GLSchemeStatus.objects.first()

        # Create scheme from quotation
        scheme = GLScheme.objects.create(
            scheme_number=GLNumberingService.generate_scheme_number(),
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
            total_sum_assured=quotation.total_sum_assured,
            total_annual_premium=quotation.total_annual_premium,
            created_by=request.user,
        )

        # Copy categories
        for cat in quotation.categories.all():
            GLSchemeCategory.objects.create(
                scheme=scheme,
                category_name=cat.category_name,
                description=cat.description,
                salary_multiple=cat.salary_multiple,
                flat_sum_assured=cat.flat_sum_assured,
                premium_rate_per_mille=cat.premium_rate_per_mille,
                sort_order=cat.sort_order,
            )

        # Copy riders
        for qr in quotation.riders.all():
            GLSchemeRider.objects.create(
                scheme=scheme,
                rider=qr.rider,
                rate_per_mille=qr.rate_per_mille,
            )

        # Mark quotation as converted
        quotation.status = "CONVERTED"
        quotation.save(update_fields=["status", "updated_at"])

        return _response(
            data=GLSchemeDetailSerializer(scheme).data,
            message=f"Quotation converted to scheme {scheme.scheme_number}.",
            status_code=status.HTTP_201_CREATED,
        )


class GLQuotationCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = GLQuotationCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        quotation_pk = self.kwargs.get("quotation_pk")
        return GLQuotationCategory.objects.filter(quotation_id=quotation_pk)

    def perform_create(self, serializer):
        serializer.save(quotation_id=self.kwargs.get("quotation_pk"))


class GLQuotationRiderViewSet(viewsets.ModelViewSet):
    serializer_class = GLQuotationRiderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        quotation_pk = self.kwargs.get("quotation_pk")
        return GLQuotationRider.objects.filter(
            quotation_id=quotation_pk
        ).select_related("rider")

    def perform_create(self, serializer):
        serializer.save(quotation_id=self.kwargs.get("quotation_pk"))


# =============================================================================
# LAYER 4 — SCHEME & MEMBER VIEWSETS
# =============================================================================


class GLSchemeViewSet(viewsets.ModelViewSet):
    queryset = GLScheme.objects.select_related(
        "partner", "product", "scheme_type", "status",
        "converted_from_quotation", "created_by",
    ).prefetch_related("categories", "riders").all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filterset_class = GLSchemeFilter
    search_fields = ["scheme_number", "partner__company_name"]
    ordering_fields = ["created_at", "inception_date", "expiry_date", "total_annual_premium"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return GLSchemeListSerializer
        if self.action == "create":
            return GLSchemeCreateSerializer
        return GLSchemeDetailSerializer

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
            data=GLSchemeDetailSerializer(scheme).data,
            message="Scheme created successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="dashboard-summary")
    def dashboard_summary(self, request):
        from django.db.models import Count, Sum
        qs = GLScheme.objects.all()
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


class GLSchemeCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = GLSchemeCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        scheme_pk = self.kwargs.get("scheme_pk")
        return GLSchemeCategory.objects.filter(scheme_id=scheme_pk)

    def perform_create(self, serializer):
        serializer.save(scheme_id=self.kwargs.get("scheme_pk"))


class GLSchemeRiderViewSet(viewsets.ModelViewSet):
    serializer_class = GLSchemeRiderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        scheme_pk = self.kwargs.get("scheme_pk")
        return GLSchemeRider.objects.filter(
            scheme_id=scheme_pk
        ).select_related("rider")

    def perform_create(self, serializer):
        serializer.save(scheme_id=self.kwargs.get("scheme_pk"))


class GLSchemeMemberViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filterset_class = GLSchemeMemberFilter
    search_fields = ["member_number", "first_name", "surname", "employee_number"]
    ordering_fields = ["created_at", "surname", "sum_assured"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = GLSchemeMember.objects.select_related(
            "scheme", "category", "status",
        ).prefetch_related("dependents")
        scheme_pk = self.kwargs.get("scheme_pk")
        if scheme_pk:
            qs = qs.filter(scheme_id=scheme_pk)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return GLSchemeMemberListSerializer
        if self.action == "create":
            return GLSchemeMemberCreateSerializer
        return GLSchemeMemberDetailSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        scheme_pk = self.kwargs.get("scheme_pk")
        if scheme_pk:
            data["scheme"] = scheme_pk
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        member = serializer.save()
        return _response(
            data=GLSchemeMemberDetailSerializer(member).data,
            message="Member enrolled successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return _response(data=serializer.data, message="Member retrieved successfully.")


class GLSchemeMemberDependentViewSet(viewsets.ModelViewSet):
    serializer_class = GLSchemeMemberDependentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        member_pk = self.kwargs.get("member_pk")
        return GLSchemeMemberDependent.objects.filter(member_id=member_pk)

    def perform_create(self, serializer):
        serializer.save(member_id=self.kwargs.get("member_pk"))


# =============================================================================
# LAYER 5 — MEDICAL UNDERWRITING VIEWSETS
# =============================================================================


class GLMedicalCodeViewSet(viewsets.ModelViewSet):
    queryset = GLMedicalCode.objects.all()
    serializer_class = GLMedicalCodeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name", "icd10_code"]
    filterset_fields = ["category", "is_active"]
    ordering = ["code"]


class GLMedicalLimitViewSet(viewsets.ModelViewSet):
    queryset = GLMedicalLimit.objects.select_related("product").all()
    serializer_class = GLMedicalLimitSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filterset_fields = ["product", "is_active"]
    ordering = ["age_from", "sum_assured_from"]


class GLUnderwritingDecisionViewSet(viewsets.ModelViewSet):
    queryset = GLUnderwritingDecision.objects.all()
    serializer_class = GLUnderwritingDecisionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    ordering = ["sort_order"]


class GLPersonalHabitViewSet(viewsets.ModelViewSet):
    queryset = GLPersonalHabit.objects.all()
    serializer_class = GLPersonalHabitSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    filterset_fields = ["category", "risk_level", "is_active"]
    ordering = ["category", "name"]


class GLMedicalHistoryViewSet(viewsets.ModelViewSet):
    queryset = GLMedicalHistory.objects.all()
    serializer_class = GLMedicalHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    filterset_fields = ["category", "risk_impact", "is_active"]
    ordering = ["category", "name"]


class GLMedicalFacilityViewSet(viewsets.ModelViewSet):
    queryset = GLMedicalFacility.objects.all()
    serializer_class = GLMedicalFacilitySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name", "city"]
    filterset_fields = ["facility_type", "is_approved", "is_active", "region"]
    ordering = ["name"]


class GLMedicalPractitionerViewSet(viewsets.ModelViewSet):
    queryset = GLMedicalPractitioner.objects.select_related("facility").all()
    serializer_class = GLMedicalPractitionerSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name", "specialization"]
    filterset_fields = ["is_approved", "is_active"]
    ordering = ["name"]


class GLMedicalCaseViewSet(viewsets.ModelViewSet):
    queryset = GLMedicalCase.objects.select_related(
        "member", "facility", "practitioner", "decision",
        "questionnaire", "decided_by",
    ).prefetch_related(
        "diagnosis_codes", "personal_habits", "medical_history",
    ).all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filterset_class = GLMedicalCaseFilter
    search_fields = ["case_number", "member__surname"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return GLMedicalCaseListSerializer
        if self.action == "create":
            return GLMedicalCaseCreateSerializer
        return GLMedicalCaseDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case = serializer.save()
        return _response(
            data=GLMedicalCaseDetailSerializer(case).data,
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
            decision = GLUnderwritingDecision.objects.get(id=decision_id)
        except GLUnderwritingDecision.DoesNotExist:
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
            data=GLMedicalCaseDetailSerializer(case).data,
            message=f"Underwriting decision recorded: {decision.name}",
        )


# =============================================================================
# LAYER 6 — CLAIMS VIEWSETS
# =============================================================================


class GLClaimTypeViewSet(viewsets.ModelViewSet):
    queryset = GLClaimType.objects.all()
    serializer_class = GLClaimTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    ordering = ["name"]


class GLClaimReasonViewSet(viewsets.ModelViewSet):
    queryset = GLClaimReason.objects.select_related("claim_type").all()
    serializer_class = GLClaimReasonSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    filterset_fields = ["claim_type", "is_active"]
    ordering = ["claim_type", "name"]


class GLClaimStatusViewSet(viewsets.ModelViewSet):
    queryset = GLClaimStatus.objects.all()
    serializer_class = GLClaimStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    ordering = ["sort_order"]


class GLDischargeTypeViewSet(viewsets.ModelViewSet):
    queryset = GLDischargeType.objects.all()
    serializer_class = GLDischargeTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    ordering = ["name"]


class GLCorrespondentTypeViewSet(viewsets.ModelViewSet):
    queryset = GLCorrespondentType.objects.all()
    serializer_class = GLCorrespondentTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    ordering = ["name"]


class GLClaimViewSet(viewsets.ModelViewSet):
    queryset = GLClaim.objects.select_related(
        "scheme", "member", "claim_type", "claim_reason", "status",
        "discharge_type", "registered_by", "assessed_by", "approved_by", "paid_by",
    ).prefetch_related("installments").all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filterset_class = GLClaimFilter
    search_fields = ["claim_number", "member__surname", "claimant_name"]
    ordering_fields = ["created_at", "incident_date", "claim_amount"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return GLClaimListSerializer
        if self.action == "create":
            return GLClaimCreateSerializer
        return GLClaimDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = serializer.save()
        return _response(
            data=GLClaimDetailSerializer(claim).data,
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
        # Move to assessed status if available
        assessed_status = GLClaimStatus.objects.filter(code="ASSESSED").first()
        if assessed_status:
            claim.status = assessed_status
        claim.save()
        return _response(
            data=GLClaimDetailSerializer(claim).data,
            message="Claim assessed successfully.",
        )

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        claim = self.get_object()
        claim.approved_by = request.user
        claim.approved_at = timezone.now()
        claim.approved_amount = request.data.get("approved_amount", claim.claim_amount)
        approved_status = GLClaimStatus.objects.filter(code="APPROVED").first()
        if approved_status:
            claim.status = approved_status
        claim.save()
        return _response(
            data=GLClaimDetailSerializer(claim).data,
            message="Claim approved successfully.",
        )

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        claim = self.get_object()
        claim.rejection_reason = request.data.get("rejection_reason", "")
        rejected_status = GLClaimStatus.objects.filter(code="REJECTED").first()
        if rejected_status:
            claim.status = rejected_status
        claim.save()
        return _response(
            data=GLClaimDetailSerializer(claim).data,
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
            paid_status = GLClaimStatus.objects.filter(code="PAID").first()
            if paid_status:
                claim.status = paid_status
        claim.save()
        return _response(
            data=GLClaimDetailSerializer(claim).data,
            message=f"Payment of {amount} recorded.",
        )


class GLClaimInstallmentViewSet(viewsets.ModelViewSet):
    serializer_class = GLClaimInstallmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        claim_pk = self.kwargs.get("claim_pk")
        return GLClaimInstallment.objects.filter(claim_id=claim_pk)

    def perform_create(self, serializer):
        serializer.save(claim_id=self.kwargs.get("claim_pk"))


class GLMedicalInvoiceViewSet(viewsets.ModelViewSet):
    queryset = GLMedicalInvoice.objects.select_related(
        "claim", "member", "facility",
    ).all()
    serializer_class = GLMedicalInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["invoice_number", "facility__name"]
    filterset_fields = ["status", "facility"]
    ordering = ["-invoice_date"]


# =============================================================================
# LAYER 7 — RENEWAL VIEWSETS
# =============================================================================


class GLSchemeRenewalViewSet(viewsets.ModelViewSet):
    queryset = GLSchemeRenewal.objects.select_related(
        "scheme", "renewal_status", "initiated_by", "approved_by",
    ).all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["renewal_number", "scheme__scheme_number"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return GLSchemeRenewalListSerializer
        if self.action == "create":
            return GLSchemeRenewalCreateSerializer
        return GLSchemeRenewalDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        renewal = serializer.save()
        return _response(
            data=GLSchemeRenewalDetailSerializer(renewal).data,
            message="Renewal initiated successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="approve")
    def approve_renewal(self, request, pk=None):
        renewal = self.get_object()
        renewal.approved_by = request.user
        renewal.approved_at = timezone.now()
        # Update renewal status
        renewed_status = GLSchemeRenewalStatus.objects.filter(code="RENEWED").first()
        if renewed_status:
            renewal.renewal_status = renewed_status
        renewal.save()

        # Update scheme dates
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
            data=GLSchemeRenewalDetailSerializer(renewal).data,
            message="Renewal approved and scheme updated.",
        )
