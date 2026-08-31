from django.urls import path

from .views import InstallmentPlanDetailView, InstallmentPlanListView

app_name = "ol_maturity_installments"

urlpatterns = [
    path("installment-plans/", InstallmentPlanListView.as_view(), name="installment-plan-list"),
    path("installment-plans/<uuid:plan_id>/", InstallmentPlanDetailView.as_view(), name="installment-plan-detail"),
]
