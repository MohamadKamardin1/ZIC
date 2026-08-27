from django.urls import path

from .approval_views import OLLoanApproveView, OLLoanBulkApproveView, OLLoanBulkRejectView, OLLoanRejectView
from .balance_views import OLLoanBalanceView
from .disbursement_views import OLLoanDisburseView
from .offset_views import OLLoanOffsetView
from .document_views import OLLoanAgreementPrintView, OLLoanSchedulePrintView
from .integration_views import OLLoanDashboardHooksView
from .history_views import OLLoanAccrualsView, OLLoanRepaymentsView
from .portal_views import OLLoanPortalDetailView, OLLoanPortalListView
from .repayment_views import OLLoanRepayView
from .schedule_views import OLLoanScheduleView
from .views import OLLoanDetailView, OLLoanExportView, OLLoanKPIView, OLLoanListView, OLLoanOptionsView


app_name = "ol_loans"

urlpatterns = [
    path("loans/options/<str:kind>/", OLLoanOptionsView.as_view(), name="loan-options"),
    path("loans/kpis/", OLLoanKPIView.as_view(), name="loan-kpis"),
    path("loans/export/", OLLoanExportView.as_view(), name="loan-export"),
    path("loans/bulk-approve/", OLLoanBulkApproveView.as_view(), name="loan-bulk-approve"),
    path("loans/bulk-reject/", OLLoanBulkRejectView.as_view(), name="loan-bulk-reject"),
    path("loans/dashboard/", OLLoanDashboardHooksView.as_view(), name="loan-dashboard-hooks"),
    path("loans/portal/", OLLoanPortalListView.as_view(), name="loan-portal-list"),
    path("loans/portal/<uuid:loan_id>/", OLLoanPortalDetailView.as_view(), name="loan-portal-detail"),
    path("loans/<uuid:loan_id>/print-agreement/", OLLoanAgreementPrintView.as_view(), name="loan-print-agreement"),
    path("loans/<uuid:loan_id>/print-schedule/", OLLoanSchedulePrintView.as_view(), name="loan-print-schedule"),
    path("loans/<uuid:loan_id>/approve/", OLLoanApproveView.as_view(), name="loan-approve"),
    path("loans/<uuid:loan_id>/disburse/", OLLoanDisburseView.as_view(), name="loan-disburse"),
    path("loans/<uuid:loan_id>/balance/", OLLoanBalanceView.as_view(), name="loan-balance"),
    path("loans/<uuid:loan_id>/schedule/", OLLoanScheduleView.as_view(), name="loan-schedule"),
    path("loans/<uuid:loan_id>/repayments/", OLLoanRepaymentsView.as_view(), name="loan-repayments"),
    path("loans/<uuid:loan_id>/accruals/", OLLoanAccrualsView.as_view(), name="loan-accruals"),
    path("loans/<uuid:loan_id>/repay/", OLLoanRepayView.as_view(), name="loan-repay"),
    path("loans/<uuid:loan_id>/offset/", OLLoanOffsetView.as_view(), name="loan-offset"),
    path("loans/<uuid:loan_id>/reject/", OLLoanRejectView.as_view(), name="loan-reject"),
    path("loans/", OLLoanListView.as_view(), name="loan-list"),
    path("loans/<uuid:loan_id>/", OLLoanDetailView.as_view(), name="loan-detail"),
]
