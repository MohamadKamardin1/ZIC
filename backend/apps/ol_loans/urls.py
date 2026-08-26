from django.urls import path

from .views import OLLoanDetailView, OLLoanListView, OLLoanOptionsView


app_name = "ol_loans"

urlpatterns = [
    path("loans/options/<str:kind>/", OLLoanOptionsView.as_view(), name="loan-options"),
    path("loans/", OLLoanListView.as_view(), name="loan-list"),
    path("loans/<uuid:loan_id>/", OLLoanDetailView.as_view(), name="loan-detail"),
]
