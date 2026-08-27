from django.urls import path

from .portal_views import ClaimPortalDetailView, ClaimPortalListView, ClaimPortalRegistrationView


app_name = "ol_claims_portal"

urlpatterns = [
    path("", ClaimPortalListView.as_view(), name="claim-portal-list"),
    path("register/", ClaimPortalRegistrationView.as_view(), name="claim-portal-register"),
    path("<str:claim_id>/", ClaimPortalDetailView.as_view(), name="claim-portal-detail"),
]
