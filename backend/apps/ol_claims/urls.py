from django.urls import path

from .options import (
    ClaimBenefitOptionsView,
    ClaimMemberOptionsView,
    ClaimReasonOptionsView,
    ClaimTypeOptionsView,
)
from .views import ClaimDetailView, ClaimListView


app_name = "ol_claims"

urlpatterns = [
    path("claims/options/types/", ClaimTypeOptionsView.as_view(), name="claim-options-types"),
    path("claims/options/reasons/", ClaimReasonOptionsView.as_view(), name="claim-options-reasons"),
    path("claims/options/benefits/", ClaimBenefitOptionsView.as_view(), name="claim-options-benefits"),
    path("claims/options/members/", ClaimMemberOptionsView.as_view(), name="claim-options-members"),
    path("claims/", ClaimListView.as_view(), name="claim-list"),
    path("claims/<uuid:claim_id>/", ClaimDetailView.as_view(), name="claim-detail"),
]
