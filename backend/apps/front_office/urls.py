from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.front_office.receipts.views import ReceiptOptionsResourceView

from .views import (
    FOCommissionStatementViewSet,
    FOCommissionViewSet,
    FOParameterViewSet,
    FOPaymentViewSet,
    FOReceiptViewSet,
    FORequisitionViewSet,
)

router = DefaultRouter()
# The new Front Office Receipts domain owns /receipts/; the legacy minimal
# FOReceipt CRUD is retained for compatibility under /legacy/receipts/.
router.register(r"legacy/receipts", FOReceiptViewSet, basename="fo-legacy-receipt")
router.register(r"commissions", FOCommissionViewSet, basename="fo-commission")
router.register(r"commission-statements", FOCommissionStatementViewSet, basename="fo-commission-statement")
router.register(r"requisitions", FORequisitionViewSet, basename="fo-requisition")
router.register(r"payments", FOPaymentViewSet, basename="fo-payment")
router.register(r"parameters", FOParameterViewSet, basename="fo-parameter")

urlpatterns = [
    path("", include(router.urls)),
    # The web SmartSelect contract mounts the receipts option catalogs at the
    # front-office root (receipts-api.ts RECEIPTS_OPTIONS_BASE), not under
    # /receipts/. The receipts-prefixed routes are kept for compatibility.
    path("options/<str:resource>/quick-create-schema/", ReceiptOptionsResourceView.as_view(), name="fo-options-resource-schema"),
    path("options/<str:resource>/quick-create/", ReceiptOptionsResourceView.as_view(), name="fo-options-resource-create"),
    path("options/<str:resource>/", ReceiptOptionsResourceView.as_view(), name="fo-options-resource"),
    path("receipts/", include("apps.front_office.receipts.urls")),
]
