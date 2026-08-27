from django.urls import path

from .views import ClaimDetailView, ClaimListView


app_name = "ol_claims"

urlpatterns = [
    path("claims/", ClaimListView.as_view(), name="claim-list"),
    path("claims/<uuid:claim_id>/", ClaimDetailView.as_view(), name="claim-detail"),
]
