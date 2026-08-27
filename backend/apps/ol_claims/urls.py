from django.urls import path

from .document_views import ClaimAssessmentReadinessView, ClaimDocumentsView
from .options import (
    ClaimBenefitOptionsView,
    ClaimMemberOptionsView,
    ClaimReasonOptionsView,
    ClaimTypeOptionsView,
)
from .registration_views import ClaimRegistrationView
from .views import ClaimDetailView, ClaimListView


app_name = "ol_claims"

urlpatterns = [
    path("policies/<uuid:policy_id>/claims/", ClaimRegistrationView.as_view(), name="policy-claim-registration"),
    path("claims/<uuid:claim_id>/documents/", ClaimDocumentsView.as_view(), name="claim-documents"),
    path("claims/<uuid:claim_id>/assessment-readiness/", ClaimAssessmentReadinessView.as_view(), name="claim-assessment-readiness"),
    path("claims/options/types/", ClaimTypeOptionsView.as_view(), name="claim-options-types"),
    path("claims/options/reasons/", ClaimReasonOptionsView.as_view(), name="claim-options-reasons"),
    path("claims/options/benefits/", ClaimBenefitOptionsView.as_view(), name="claim-options-benefits"),
    path("claims/options/members/", ClaimMemberOptionsView.as_view(), name="claim-options-members"),
    path("claims/", ClaimListView.as_view(), name="claim-list"),
    path("claims/<uuid:claim_id>/", ClaimDetailView.as_view(), name="claim-detail"),
]
