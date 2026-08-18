from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.pagination import StandardPagination

from .models import (
    OLQuotation,
    OLQuotationBeneficiary,
    OLQuotationBenefit,
    OLQuotationDocument,
    OLQuotationEvent,
    OLQuotationFinancialSummary,
    OLQuotationFundAllocation,
    OLQuotationInstallmentConfiguration,
    OLQuotationInstallmentRateRow,
    OLQuotationMember,
    OLQuotationPaymentDetail,
    OLQuotationPlanConfiguration,
    OLQuotationProduct,
    OLQuotationRiderSelection,
    OLQuotationUnderwriting,
    OLQuotationVersion,
    QuotationStatus,
)
from .permissions import HasOLQuotationPermission, has_quotation_permission
from .serializers import (
    OLQuotationBeneficiarySerializer,
    OLQuotationEventSerializer,
    OLQuotationFundAllocationSerializer,
    OLQuotationInstallmentConfigurationSerializer,
    OLQuotationInstallmentRateRowSerializer,
    OLQuotationMemberSerializer,
    OLQuotationPaymentDetailSerializer,
    OLQuotationPlanConfigurationSerializer,
    OLQuotationProductSerializer,
    OLQuotationRiderSelectionSerializer,
    OLQuotationSerializer,
    OLQuotationUnderwritingSerializer,
    OLQuotationVersionSerializer,
    OLQuotationBenefitSerializer,
    OLQuotationDocumentSerializer,
    OLQuotationFinancialSummarySerializer,
)
from .services.quotation_service import QuotationService


def _response(data=None, message="Data retrieved successfully", status_code=status.HTTP_200_OK):
    return Response(
        {
            "success": status_code < 400,
            "status_code": status_code,
            "message": message,
            "data": data,
        },
        status=status_code,
    )


class QuotationScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [HasOLQuotationPermission]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering = ["-created_at"]

    def _scope_queryset(self, queryset):
        user = self.request.user
        if getattr(user, "is_superuser", False):
            return queryset
        if hasattr(user, "visible_partners"):
            partner_ids = user.visible_partners().values_list("pk", flat=True)
            if self.model_has_partner_scope:
                return queryset.filter(partner_id__in=partner_ids)
            return queryset.filter(quotation__partner_id__in=partner_ids)
        return queryset.none()

    @property
    def model_has_partner_scope(self):
        return False

    def get_queryset(self):
        queryset = self.queryset
        quotation_id = self.request.query_params.get("quotation_id")
        if quotation_id and hasattr(queryset.model, "quotation_id"):
            queryset = queryset.filter(quotation_id=quotation_id)
        return self._scope_queryset(queryset)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return _response(self.get_serializer(queryset, many=True).data, "Quotations retrieved.")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return _response(self.get_serializer(instance).data, "Quotation retrieved.")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return _response(self.get_serializer(serializer.instance).data, "Quotation child record created.", status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return _response(self.get_serializer(serializer.instance).data, "Quotation child record updated.")

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class OLQuotationViewSet(QuotationScopedViewSet):
    queryset = OLQuotation.objects.select_related("partner", "product", "product_version").prefetch_related(
        "products",
        "plan_configurations",
        "members",
        "installment_configurations__rate_rows",
        "fund_allocations",
        "rider_selections",
        "payment_detail",
        "underwriting_detail",
        "beneficiaries",
        "benefits",
        "documents",
        "versions",
        "financial_summary",
        "events",
    )
    serializer_class = OLQuotationSerializer
    model_has_partner_scope = True
    filterset_fields = ["status", "partner", "product", "product_version", "currency"]
    search_fields = [
        "quote_number",
        "partner__partner_number",
        "partner__legal_name",
        "partner__company_name",
        "partner__first_name",
        "partner__surname",
    ]
    ordering_fields = ["quote_number", "quote_date", "expiry_date", "status", "created_at", "updated_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("include_expired") != "true":
            queryset = queryset.exclude(status=QuotationStatus.EXPIRED)
        return queryset

    def perform_create(self, serializer):
        quotation = QuotationService.create_draft(
            actor=self.request.user,
            validated_data=serializer.validated_data,
            request=self.request,
        )
        serializer.instance = quotation

    def perform_update(self, serializer):
        serializer.instance = QuotationService.update_draft(
            quotation=serializer.instance,
            actor=self.request.user,
            validated_data=serializer.validated_data,
            request=self.request,
        )

    def _lifecycle_response(self, request, instance, target, message):
        quotation = QuotationService.transition(
            quotation=instance,
            target_status=target,
            actor=request.user,
            request=request,
        )
        return _response(self.get_serializer(quotation).data, message)

    @action(detail=True, methods=["post"], url_path="finalize")
    def finalize(self, request, pk=None):
        return self._lifecycle_response(request, self.get_object(), QuotationStatus.FINALIZED, "Quotation finalized.")

    @action(detail=True, methods=["post"], url_path="expire")
    def expire(self, request, pk=None):
        return self._lifecycle_response(request, self.get_object(), QuotationStatus.EXPIRED, "Quotation expired.")

    @action(detail=True, methods=["post"], url_path="convert")
    def convert(self, request, pk=None):
        return self._lifecycle_response(request, self.get_object(), QuotationStatus.CONVERTED, "Quotation converted.")

    @action(detail=True, methods=["get"], url_path="wizard-summary")
    def wizard_summary(self, request, pk=None):
        quotation = self.get_object()
        return _response(
            {
                "quotation_id": quotation.pk,
                "quote_number": quotation.quote_number,
                "steps": {
                    "1_product_plan": quotation.products.filter(is_selected=True).exists() or quotation.plan_configurations.filter(is_selected=True).exists(),
                    "2_members": quotation.members.exists(),
                    "3_installments": quotation.installment_configurations.exists(),
                    "4_funds": quotation.fund_allocations.exists(),
                    "5_riders": quotation.rider_selections.exists(),
                    "6_payment": hasattr(quotation, "payment_detail"),
                    "7_underwriting": hasattr(quotation, "underwriting_detail"),
                },
                "status": quotation.status,
            },
            "Quotation wizard summary retrieved.",
        )


class OLQuotationProductViewSet(QuotationScopedViewSet):
    queryset = OLQuotationProduct.objects.select_related("quotation", "product", "product_version")
    serializer_class = OLQuotationProductSerializer
    filterset_fields = ["quotation", "product", "product_version", "is_selected", "is_primary", "currency"]
    search_fields = ["product_name_snapshot", "product__code", "product__name", "quotation__quote_number"]
    ordering_fields = ["created_at", "product_name_snapshot", "currency", "is_primary"]


class OLQuotationPlanConfigurationViewSet(QuotationScopedViewSet):
    queryset = OLQuotationPlanConfiguration.objects.select_related("quotation", "product_version", "plan")
    serializer_class = OLQuotationPlanConfigurationSerializer
    filterset_fields = ["quotation", "product_version", "plan", "is_selected", "premium_frequency"]
    search_fields = ["sub_product_code", "quotation__quote_number"]
    ordering_fields = ["created_at", "base_sum_assured", "term_years", "premium_amount"]


class OLQuotationMemberViewSet(QuotationScopedViewSet):
    queryset = OLQuotationMember.objects.select_related("quotation", "partner")
    serializer_class = OLQuotationMemberSerializer
    filterset_fields = ["quotation", "member_type", "gender", "smoker_status"]
    search_fields = ["first_name", "last_name", "identity_number", "quotation__quote_number"]
    ordering_fields = ["created_at", "last_name", "date_of_birth", "member_type"]


class OLQuotationInstallmentConfigurationViewSet(QuotationScopedViewSet):
    queryset = OLQuotationInstallmentConfiguration.objects.select_related("quotation", "plan_configuration").prefetch_related("rate_rows")
    serializer_class = OLQuotationInstallmentConfigurationSerializer
    filterset_fields = ["quotation", "plan_configuration", "frequency", "currency", "is_selected"]
    search_fields = ["frequency", "quotation__quote_number"]
    ordering_fields = ["created_at", "frequency", "installment_amount", "first_due_date"]


class OLQuotationInstallmentRateRowViewSet(QuotationScopedViewSet):
    queryset = OLQuotationInstallmentRateRow.objects.select_related("installment_configuration__quotation")
    serializer_class = OLQuotationInstallmentRateRowSerializer
    filterset_fields = ["installment_configuration", "period_from", "period_to"]
    search_fields = ["notes", "installment_configuration__quotation__quote_number"]
    ordering_fields = ["period_from", "period_to", "rate", "charge"]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(installment_configuration__quotation__partner_id__in=self._partner_ids()) if not self.request.user.is_superuser else queryset

    def _partner_ids(self):
        return self.request.user.visible_partners().values_list("pk", flat=True)


class OLQuotationFundAllocationViewSet(QuotationScopedViewSet):
    queryset = OLQuotationFundAllocation.objects.select_related("quotation", "fund")
    serializer_class = OLQuotationFundAllocationSerializer
    filterset_fields = ["quotation", "fund", "is_selected"]
    search_fields = ["fund__code", "fund__name", "quotation__quote_number"]
    ordering_fields = ["created_at", "allocation_percentage", "allocation_amount"]


class OLQuotationRiderSelectionViewSet(QuotationScopedViewSet):
    queryset = OLQuotationRiderSelection.objects.select_related("quotation", "rider", "plan_configuration")
    serializer_class = OLQuotationRiderSelectionSerializer
    filterset_fields = ["quotation", "rider", "plan_configuration", "is_selected"]
    search_fields = ["rider__code", "rider__name", "quotation__quote_number"]
    ordering_fields = ["created_at", "rider_sum_assured", "premium_amount"]


class OLQuotationPaymentDetailViewSet(QuotationScopedViewSet):
    queryset = OLQuotationPaymentDetail.objects.select_related("quotation", "payer")
    serializer_class = OLQuotationPaymentDetailSerializer
    filterset_fields = ["quotation", "payer", "payment_method", "currency"]
    search_fields = ["payment_reference", "account_reference", "quotation__quote_number"]
    ordering_fields = ["created_at", "amount", "payment_method"]


class OLQuotationUnderwritingViewSet(QuotationScopedViewSet):
    queryset = OLQuotationUnderwriting.objects.select_related("quotation")
    serializer_class = OLQuotationUnderwritingSerializer
    filterset_fields = ["quotation", "medical_required", "financial_underwriting_required", "risk_class"]
    search_fields = ["risk_class", "notes", "quotation__quote_number"]
    ordering_fields = ["created_at", "risk_class", "medical_required"]


class OLQuotationBeneficiaryViewSet(QuotationScopedViewSet):
    queryset = OLQuotationBeneficiary.objects.select_related("quotation", "partner")
    serializer_class = OLQuotationBeneficiarySerializer
    filterset_fields = ["quotation", "partner", "relationship"]
    search_fields = ["name", "identity_number", "relationship", "quotation__quote_number"]
    ordering_fields = ["created_at", "name", "percentage"]


class OLQuotationBenefitViewSet(QuotationScopedViewSet):
    queryset = OLQuotationBenefit.objects.select_related("quotation")
    serializer_class = OLQuotationBenefitSerializer
    filterset_fields = ["quotation", "code", "benefit_type", "is_selected"]
    search_fields = ["code", "name", "quotation__quote_number"]
    ordering_fields = ["created_at", "code", "sum_assured", "premium_amount"]


class OLQuotationDocumentViewSet(QuotationScopedViewSet):
    queryset = OLQuotationDocument.objects.select_related("quotation")
    serializer_class = OLQuotationDocumentSerializer
    filterset_fields = ["quotation", "document_type", "status"]
    search_fields = ["document_type", "file_reference", "quotation__quote_number"]
    ordering_fields = ["created_at", "document_type", "status"]


class OLQuotationVersionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OLQuotationVersion.objects.select_related("quotation", "created_by", "updated_by")
    serializer_class = OLQuotationVersionSerializer
    permission_classes = [HasOLQuotationPermission]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["quotation", "version_number", "status"]
    search_fields = ["quotation__quote_number", "change_reason"]
    ordering_fields = ["created_at", "version_number", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if getattr(user, "is_superuser", False):
            return queryset
        return queryset.filter(quotation__partner_id__in=user.visible_partners().values_list("pk", flat=True))


class OLQuotationFinancialSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OLQuotationFinancialSummary.objects.select_related("quotation")
    serializer_class = OLQuotationFinancialSummarySerializer
    permission_classes = [HasOLQuotationPermission]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["quotation", "currency"]
    search_fields = ["quotation__quote_number"]
    ordering_fields = ["created_at", "total_sum_assured", "total_premium"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if getattr(user, "is_superuser", False):
            return queryset
        return queryset.filter(quotation__partner_id__in=user.visible_partners().values_list("pk", flat=True))


class OLQuotationEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OLQuotationEvent.objects.select_related("quotation", "actor")
    serializer_class = OLQuotationEventSerializer
    permission_classes = [HasOLQuotationPermission]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["quotation", "event_type", "from_status", "to_status", "actor"]
    search_fields = ["quotation__quote_number", "event_type", "notes"]
    ordering_fields = ["created_at", "event_type", "from_status", "to_status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if getattr(user, "is_superuser", False):
            return queryset
        partner_ids = user.visible_partners().values_list("pk", flat=True)
        return queryset.filter(quotation__partner_id__in=partner_ids)
