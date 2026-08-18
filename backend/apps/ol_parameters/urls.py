from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    OLAnticipatedEndowmentInstallmentRateViewSet,
    OLBeneficialTypeViewSet,
    OLComputationApproachViewSet,
    OLDefaultSystemParameterViewSet,
    OLGracePeriodViewSet,
    OLMaturityClaimSetupViewSet,
    OLMemberCoverConfigurationViewSet,
    OLOverrideCommissionSetupViewSet,
    OLParameterHealthView,
    OLParameterTableRegistryViewSet,
    OLPolicyRenewalStatusViewSet,
    OLPolicyStatusViewSet,
)


router = DefaultRouter()
router.register("tables", OLParameterTableRegistryViewSet, basename="ol-parameter-table")
router.register("default-system-parameters", OLDefaultSystemParameterViewSet, basename="ol-default-system-parameter")
router.register("override-commission-setups", OLOverrideCommissionSetupViewSet, basename="ol-override-commission-setup")
router.register("computation-approaches", OLComputationApproachViewSet, basename="ol-computation-approach")
router.register("maturity-claim-setups", OLMaturityClaimSetupViewSet, basename="ol-maturity-claim-setup")
router.register("anticipated-endowment-rates", OLAnticipatedEndowmentInstallmentRateViewSet, basename="ol-anticipated-endowment-rate")
router.register("grace-periods", OLGracePeriodViewSet, basename="ol-grace-period")
router.register("policy-statuses", OLPolicyStatusViewSet, basename="ol-policy-status")
router.register("policy-renewal-statuses", OLPolicyRenewalStatusViewSet, basename="ol-policy-renewal-status")
router.register("beneficial-types", OLBeneficialTypeViewSet, basename="ol-beneficial-type")
router.register("member-cover-configurations", OLMemberCoverConfigurationViewSet, basename="ol-member-cover-configuration")

urlpatterns = [
    path("health/", OLParameterHealthView.as_view(), name="ol-parameters-health"),
    path("", include(router.urls)),
]
