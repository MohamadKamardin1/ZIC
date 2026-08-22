from django.urls import path

from apps.ol_commitments.views import (
    CommitmentActionDispatchView,
    CommitmentDetailView,
    CommitmentImportDetailView,
    CommitmentImportsView,
    CommitmentKPIsView,
    CommitmentListView,
    CommitmentOptionsView,
    CommitmentReferencesView,
    CommitmentSourcesView,
    LapseReviewView,
    ManualCommitmentCreateView,
    OverdueNotificationsView,
    ProcessOverdueView,
)

urlpatterns = [
    path("commitments/", CommitmentListView.as_view(), name="ol-commitments-list"),
    path("commitments/kpis/", CommitmentKPIsView.as_view(), name="ol-commitments-kpis"),
    path("commitments/manual/", ManualCommitmentCreateView.as_view(), name="ol-commitments-manual"),
    path("commitments/process-overdue/", ProcessOverdueView.as_view(), name="ol-commitments-process-overdue"),
    path("commitments/lapse-review/", LapseReviewView.as_view(), name="ol-commitments-lapse-review"),
    path("commitments/<uuid:commitment_id>/", CommitmentDetailView.as_view(), name="ol-commitments-detail"),
    path("commitments/<uuid:commitment_id>/<str:action>/", CommitmentActionDispatchView.as_view(), name="ol-commitments-action"),
    path("options/", CommitmentOptionsView.as_view(), name="ol-commitments-options"),
    path("options/sources/", CommitmentSourcesView.as_view(), name="ol-commitments-sources"),
    path("options/references/", CommitmentReferencesView.as_view(), name="ol-commitments-references"),
    path("imports/", CommitmentImportsView.as_view(), name="ol-commitments-imports"),
    path("imports/<uuid:import_id>/", CommitmentImportDetailView.as_view(), name="ol-commitments-import-detail"),
    path("notifications/overdue/", OverdueNotificationsView.as_view(), name="ol-commitments-overdue-notifications"),
]