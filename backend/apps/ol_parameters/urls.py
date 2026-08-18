from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    OLComputationApproachViewSet,
    OLDefaultSystemParameterViewSet,
    OLMaturityClaimSetupViewSet,
    OLOverrideCommissionSetupViewSet,
    OLParameterHealthView,
    OLParameterTableRegistryViewSet,
)


router = DefaultRouter()
router.register("tables", OLParameterTableRegistryViewSet, basename="ol-parameter-table")
router.register("default-system-parameters", OLDefaultSystemParameterViewSet, basename="ol-default-system-parameter")
router.register("override-commission-setups", OLOverrideCommissionSetupViewSet, basename="ol-override-commission-setup")
router.register("computation-approaches", OLComputationApproachViewSet, basename="ol-computation-approach")
router.register("maturity-claim-setups", OLMaturityClaimSetupViewSet, basename="ol-maturity-claim-setup")

urlpatterns = [
    path("health/", OLParameterHealthView.as_view(), name="ol-parameters-health"),
    path("", include(router.urls)),
]
