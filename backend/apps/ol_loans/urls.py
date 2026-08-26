from django.urls import path

from .approval_views import OLLoanApproveView, OLLoanBulkApproveView, OLLoanBulkRejectView, OLLoanRejectView
from .disbursement_views import OLLoanDisburseView
from .views import OLLoanDetailView, OLLoanListView, OLLoanOptionsView


app_name = "ol_loans"

urlpatterns = [
    path("loans/options/<str:kind>/", OLLoanOptionsView.as_view(), name="loan-options"),
    path("loans/bulk-approve/", OLLoanBulkApproveView.as_view(), name="loan-bulk-approve"),
    path("loans/bulk-reject/", OLLoanBulkRejectView.as_view(), name="loan-bulk-reject"),
    path("loans/<uuid:loan_id>/approve/", OLLoanApproveView.as_view(), name="loan-approve"),
    path("loans/<uuid:loan_id>/disburse/", OLLoanDisburseView.as_view(), name="loan-disburse"),
    path("loans/<uuid:loan_id>/reject/", OLLoanRejectView.as_view(), name="loan-reject"),
    path("loans/", OLLoanListView.as_view(), name="loan-list"),
    path("loans/<uuid:loan_id>/", OLLoanDetailView.as_view(), name="loan-detail"),
]
