from django.urls import path

from .endorsement_views import PolicyEndorsementDetailView, PolicyEndorsementListCreateView
from .issuance_views import PolicyIssueView
from .views import PolicyDetailView, PolicyExportView, PolicyKPIsView, PolicyListView

app_name = "ol_policies"

urlpatterns = [
    path("policies/issue/", PolicyIssueView.as_view(), name="policy-issue"),
    path("policies/kpis/", PolicyKPIsView.as_view(), name="policy-kpis"),
    path("policies/export/", PolicyExportView.as_view(), name="policy-export"),
    path("policies/", PolicyListView.as_view(), name="policy-list"),
    path(
        "policies/<uuid:policy_id>/endorsements/<uuid:endorsement_id>/",
        PolicyEndorsementDetailView.as_view(),
        name="policy-endorsement-detail",
    ),
    path(
        "policies/<uuid:policy_id>/endorsements/",
        PolicyEndorsementListCreateView.as_view(),
        name="policy-endorsement-list-create",
    ),
    path("policies/<uuid:policy_id>/", PolicyDetailView.as_view(), name="policy-detail"),
]
