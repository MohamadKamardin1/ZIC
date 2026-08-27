from django.urls import path

from .assessment_views import ClaimAssessmentView, ClaimNotesView
from .document_views import ClaimAssessmentReadinessView, ClaimDocumentsView
from .financial_views import ClaimFinancialSummaryView
from .medical_views import ClaimMedicalEvaluationView, ClaimMedicalRequirementView, ClaimMedicalResultView
from .requisition_views import ClaimRaiseRequisitionView
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
    path("claims/<uuid:claim_id>/assess/", ClaimAssessmentView.as_view(), name="claim-assess"),
    path("claims/<uuid:claim_id>/notes/", ClaimNotesView.as_view(), name="claim-notes"),
    path("claims/<uuid:claim_id>/financial-summary/", ClaimFinancialSummaryView.as_view(), name="claim-financial-summary"),
    path("claims/<uuid:claim_id>/raise-requisition/", ClaimRaiseRequisitionView.as_view(), name="claim-raise-requisition"),
    path("claims/<uuid:claim_id>/medical/evaluate/", ClaimMedicalEvaluationView.as_view(), name="claim-medical-evaluate"),
    path("claims/<uuid:claim_id>/medical/require/", ClaimMedicalRequirementView.as_view(), name="claim-medical-require"),
    path("claims/<uuid:claim_id>/medical/result/", ClaimMedicalResultView.as_view(), name="claim-medical-result"),
    path("claims/options/types/", ClaimTypeOptionsView.as_view(), name="claim-options-types"),
    path("claims/options/reasons/", ClaimReasonOptionsView.as_view(), name="claim-options-reasons"),
    path("claims/options/benefits/", ClaimBenefitOptionsView.as_view(), name="claim-options-benefits"),
    path("claims/options/members/", ClaimMemberOptionsView.as_view(), name="claim-options-members"),
    path("claims/", ClaimListView.as_view(), name="claim-list"),
    path("claims/<uuid:claim_id>/", ClaimDetailView.as_view(), name="claim-detail"),
]
