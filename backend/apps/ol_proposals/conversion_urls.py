from django.urls import path

from apps.ol_proposals.views import ProposalFromQuotationView

urlpatterns = [
    path("from-quotation/<uuid:quotation_id>/", ProposalFromQuotationView.as_view(), name="ol-proposals-from-quotation"),
]