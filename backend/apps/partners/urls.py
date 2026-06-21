from django.urls import include
from rest_framework.routers import DefaultRouter

from .views import PartnerViewSet

router = DefaultRouter()
router.register(r"", PartnerViewSet, basename="partners")

urlpatterns = router.urls
