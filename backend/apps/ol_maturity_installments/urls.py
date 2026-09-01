from django.urls import path

from .creation_views import InstallmentPlanCreateView
from .document_views import OLMaturityPaymentAdvicePrintView, OLMaturitySchedulePrintView
from .lifecycle_views import InstallmentItemReversePaymentView, InstallmentPlanCancelView
from .options import InstallmentFrequencyOptionsView, InstallmentTermOptionsView
from .payment_views import InstallmentItemConfirmPaymentView, InstallmentItemProcessPaymentView
from .reconciliation_views import InstallmentPlanReconciliationView
from .views import (
    InstallmentPlanDetailView,
    InstallmentPlanExportView,
    InstallmentPlanKpisView,
    InstallmentPlanListView,
)

app_name = "ol_maturity_installments"

urlpatterns = [
    path(
        "maturity-installments/",
        InstallmentPlanListView.as_view(),
        name="installment-plan-list",
    ),
    path(
        "maturity-installments/kpis/",
        InstallmentPlanKpisView.as_view(),
        name="installment-plan-kpis",
    ),
    path(
        "maturity-installments/export/",
        InstallmentPlanExportView.as_view(),
        name="installment-plan-export",
    ),
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
    path(
        "maturity-installments/items/<uuid:item_id>/reverse-payment/",
        InstallmentItemReversePaymentView.as_view(),
        name="installment-item-reverse-payment",
    ),
    path(
        "maturity-installments/plans/<uuid:plan_id>/cancel/",
        InstallmentPlanCancelView.as_view(),
        name="installment-plan-cancel",
    ),
    path(
        "maturity-installments/<uuid:plan_id>/reconciliation/",
        InstallmentPlanReconciliationView.as_view(),
        name="installment-plan-reconciliation",
    ),
    path(
        "maturity-installments/<uuid:plan_id>/print-schedule/",
        OLMaturitySchedulePrintView.as_view(),
        name="installment-plan-print-schedule",
    ),
    path(
        "maturity-installments/<uuid:plan_id>/print-advice/",
        OLMaturityPaymentAdvicePrintView.as_view(),
        name="installment-plan-print-advice",
    ),
    path(
        "maturity-installments/<uuid:plan_id>/",
        InstallmentPlanDetailView.as_view(),
        name="installment-plan-detail",
    ),
    path("installment-plans/", InstallmentPlanListView.as_view(), name="installment-plan-list-legacy"),
    path(
        "installment-plans/<uuid:plan_id>/",
        InstallmentPlanDetailView.as_view(),
        name="installment-plan-detail-legacy",
    ),
]
