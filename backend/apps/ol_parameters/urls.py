from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import OLParameterHealthView, OLParameterTableRegistryViewSet


router = DefaultRouter()
router.register("tables", OLParameterTableRegistryViewSet, basename="ol-parameter-table")

urlpatterns = [
    path("health/", OLParameterHealthView.as_view(), name="ol-parameters-health"),
    path("", include(router.urls)),
]
