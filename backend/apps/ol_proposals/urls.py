from django.urls import path

from apps.ol_proposals.views import (
    ProposalBeneficiaryCollectionView,
    ProposalBeneficiaryItemView,
    ProposalCompletenessView,
    ProposalDetailView,
    ProposalDocumentCollectionView,
    ProposalEnrichmentOptionsView,
    ProposalEnrichView,
    ProposalHealthAnswersView,
    ProposalHealthQuestionsView,
    ProposalListView,
    ProposalMarkPaymentReadyView,
    ProposalPaymentReadinessView,
    ProposalUnderwritingDecisionView,
)

urlpatterns = [
    path("proposals/", ProposalListView.as_view(), name="ol-proposals-list"),
    path("proposals/options/<str:kind>/", ProposalEnrichmentOptionsView.as_view(), name="ol-proposals-enrichment-options"),
    path("proposals/<uuid:proposal_id>/", ProposalDetailView.as_view(), name="ol-proposals-detail"),
    path("proposals/<uuid:proposal_id>/enrich/", ProposalEnrichView.as_view(), name="ol-proposals-enrich"),
    path("proposals/<uuid:proposal_id>/completeness/", ProposalCompletenessView.as_view(), name="ol-proposals-completeness"),
    path("proposals/<uuid:proposal_id>/documents/", ProposalDocumentCollectionView.as_view(), name="ol-proposals-documents"),
    path("proposals/<uuid:proposal_id>/health-questions/", ProposalHealthQuestionsView.as_view(), name="ol-proposals-health-questions"),
    path("proposals/<uuid:proposal_id>/health-answers/", ProposalHealthAnswersView.as_view(), name="ol-proposals-health-answers"),
    path("proposals/<uuid:proposal_id>/underwriting-decision/", ProposalUnderwritingDecisionView.as_view(), name="ol-proposals-underwriting-decision"),
    path("proposals/<uuid:proposal_id>/payment-readiness/", ProposalPaymentReadinessView.as_view(), name="ol-proposals-payment-readiness"),
    path("proposals/<uuid:proposal_id>/mark-payment-ready/", ProposalMarkPaymentReadyView.as_view(), name="ol-proposals-mark-payment-ready"),
    path("proposals/<uuid:proposal_id>/beneficiaries/", ProposalBeneficiaryCollectionView.as_view(), name="ol-proposals-beneficiaries"),
    path("proposals/<uuid:proposal_id>/beneficiaries/<uuid:beneficiary_id>/", ProposalBeneficiaryItemView.as_view(), name="ol-proposals-beneficiary-item"),
]