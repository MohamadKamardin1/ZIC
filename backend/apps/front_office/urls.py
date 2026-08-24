from django.urls import include, path
from rest_framework.routers import DefaultRouter

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
    path("receipts/", include("apps.front_office.receipts.urls")),
]
