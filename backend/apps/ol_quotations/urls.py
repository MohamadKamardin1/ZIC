from django.urls import path
from rest_framework.routers import DefaultRouter

from .option_views import (
    OLOptionQuickCreateSchemaView,
    OLOptionQuickCreateView,
    OLOptionRegistryView,
)

from .views import (
    OLQuotationBeneficiaryViewSet,
    OLQuotationBenefitViewSet,
    OLQuotationDocumentViewSet,
    OLQuotationEventViewSet,
    OLQuotationFinancialSummaryViewSet,
    OLQuotationFundAllocationViewSet,
    OLQuotationInstallmentConfigurationViewSet,
    OLQuotationInstallmentRateRowViewSet,
    OLQuotationMemberViewSet,
    OLQuotationPaymentDetailViewSet,
    OLQuotationPlanConfigurationViewSet,
    OLQuotationProductViewSet,
    OLQuotationRiderSelectionViewSet,
    OLQuotationUnderwritingViewSet,
    OLQuotationVersionViewSet,
    OLQuotationViewSet,
    OLPlanSearchView,
)

router = DefaultRouter()
router.register("quotations", OLQuotationViewSet, basename="ol-quotation")
router.register("products", OLQuotationProductViewSet, basename="ol-quotation-product")
router.register("plan-configurations", OLQuotationPlanConfigurationViewSet, basename="ol-quotation-plan-configuration")
router.register("members", OLQuotationMemberViewSet, basename="ol-quotation-member")
router.register("installments", OLQuotationInstallmentConfigurationViewSet, basename="ol-quotation-installment")
router.register("installment-rate-rows", OLQuotationInstallmentRateRowViewSet, basename="ol-quotation-installment-rate-row")
router.register("fund-allocations", OLQuotationFundAllocationViewSet, basename="ol-quotation-fund-allocation")
router.register("riders", OLQuotationRiderSelectionViewSet, basename="ol-quotation-rider")
router.register("payment-details", OLQuotationPaymentDetailViewSet, basename="ol-quotation-payment-detail")
router.register("underwriting", OLQuotationUnderwritingViewSet, basename="ol-quotation-underwriting")
router.register("beneficiaries", OLQuotationBeneficiaryViewSet, basename="ol-quotation-beneficiary")
router.register("benefits", OLQuotationBenefitViewSet, basename="ol-quotation-benefit")
router.register("documents", OLQuotationDocumentViewSet, basename="ol-quotation-document")
router.register("versions", OLQuotationVersionViewSet, basename="ol-quotation-version")
router.register("financial-summaries", OLQuotationFinancialSummaryViewSet, basename="ol-quotation-financial-summary")
router.register("events", OLQuotationEventViewSet, basename="ol-quotation-event")

urlpatterns = [
    path("plans/search/", OLPlanSearchView.as_view(), name="ol-plan-search"),
    path("options/<str:entity>/", OLOptionRegistryView.as_view(), name="ol-option-registry"),
    path("options/<str:entity>/quick-create-schema/", OLOptionQuickCreateSchemaView.as_view(), name="ol-option-quick-create-schema"),
    path("options/<str:entity>/quick-create/", OLOptionQuickCreateView.as_view(), name="ol-option-quick-create"),
    *router.urls,
]
