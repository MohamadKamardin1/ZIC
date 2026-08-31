from django.urls import path

from .creation_views import InstallmentPlanCreateView
from .options import InstallmentFrequencyOptionsView, InstallmentTermOptionsView
from .payment_views import InstallmentItemConfirmPaymentView, InstallmentItemProcessPaymentView
from .views import InstallmentPlanDetailView, InstallmentPlanListView

app_name = "ol_maturity_installments"

urlpatterns = [
    path(
        "maturity-installments/create/",
        InstallmentPlanCreateView.as_view(),
        name="installment-plan-create",
    ),
    path(
        "maturity-installments/options/frequencies/",
        InstallmentFrequencyOptionsView.as_view(),
        name="installment-options-frequencies",
    ),
    path(
        "maturity-installments/options/terms/", InstallmentTermOptionsView.as_view(), name="installment-options-terms"
    ),
    path(
        "maturity-installments/items/<uuid:item_id>/process-payment/",
        InstallmentItemProcessPaymentView.as_view(),
        name="installment-item-process-payment",
    ),
    path(
        "maturity-installments/items/<uuid:item_id>/confirm-payment/",
        InstallmentItemConfirmPaymentView.as_view(),
        name="installment-item-confirm-payment",
    ),
    path("installment-plans/", InstallmentPlanListView.as_view(), name="installment-plan-list"),
    path("installment-plans/<uuid:plan_id>/", InstallmentPlanDetailView.as_view(), name="installment-plan-detail"),
]
