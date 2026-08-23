from django.urls import path

from apps.ol_proposals.views import (
    ProposalBeneficiaryCollectionView,
    ProposalBeneficiaryItemView,
    ProposalCompletenessView,
    ProposalDetailView,
    ProposalEnrichmentOptionsView,
    ProposalEnrichView,
    ProposalListView,
)

urlpatterns = [
    path("proposals/", ProposalListView.as_view(), name="ol-proposals-list"),
    path("proposals/options/<str:kind>/", ProposalEnrichmentOptionsView.as_view(), name="ol-proposals-enrichment-options"),
    path("proposals/<uuid:proposal_id>/", ProposalDetailView.as_view(), name="ol-proposals-detail"),
    path("proposals/<uuid:proposal_id>/enrich/", ProposalEnrichView.as_view(), name="ol-proposals-enrich"),
    path("proposals/<uuid:proposal_id>/completeness/", ProposalCompletenessView.as_view(), name="ol-proposals-completeness"),
    path("proposals/<uuid:proposal_id>/beneficiaries/", ProposalBeneficiaryCollectionView.as_view(), name="ol-proposals-beneficiaries"),
    path("proposals/<uuid:proposal_id>/beneficiaries/<uuid:beneficiary_id>/", ProposalBeneficiaryItemView.as_view(), name="ol-proposals-beneficiary-item"),
]