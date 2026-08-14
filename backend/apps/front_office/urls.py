from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    FOReceiptViewSet,
    FOCommissionViewSet,
    FOCommissionStatementViewSet,
    FORequisitionViewSet,
    FOPaymentViewSet,
    FOParameterViewSet,
)

router = DefaultRouter()
router.register(r"receipts", FOReceiptViewSet, basename="fo-receipt")
router.register(r"commissions", FOCommissionViewSet, basename="fo-commission")
router.register(r"commission-statements", FOCommissionStatementViewSet, basename="fo-commission-statement")
router.register(r"requisitions", FORequisitionViewSet, basename="fo-requisition")
router.register(r"payments", FOPaymentViewSet, basename="fo-payment")
router.register(r"parameters", FOParameterViewSet, basename="fo-parameter")

urlpatterns = [
    path("", include(router.urls)),
]
