from django.urls import path

from apps.ol_proposals.views import ProposalDetailView, ProposalListView

urlpatterns = [
    path("proposals/", ProposalListView.as_view(), name="ol-proposals-list"),
    path("proposals/<uuid:proposal_id>/", ProposalDetailView.as_view(), name="ol-proposals-detail"),
]