from django.urls import path

from .options import InstallmentFrequencyOptionsView, InstallmentTermOptionsView
from .views import InstallmentPlanDetailView, InstallmentPlanListView

app_name = "ol_maturity_installments"

urlpatterns = [
    path(
        "maturity-installments/options/frequencies/",
        InstallmentFrequencyOptionsView.as_view(),
        name="installment-options-frequencies",
    ),
    path(
        "maturity-installments/options/terms/", InstallmentTermOptionsView.as_view(), name="installment-options-terms"
    ),
    path("installment-plans/", InstallmentPlanListView.as_view(), name="installment-plan-list"),
    path("installment-plans/<uuid:plan_id>/", InstallmentPlanDetailView.as_view(), name="installment-plan-detail"),
]
