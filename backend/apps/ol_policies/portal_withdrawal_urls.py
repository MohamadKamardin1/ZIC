from django.urls import path

from .portal_withdrawal_views import PartnerPortalWithdrawalDetailView, PartnerPortalWithdrawalListView

app_name = "ol_policies_portal_withdrawals"

urlpatterns = [
    path("", PartnerPortalWithdrawalListView.as_view(), name="withdrawals-list"),
    path("<uuid:withdrawal_id>/", PartnerPortalWithdrawalDetailView.as_view(), name="withdrawal-detail"),
]
