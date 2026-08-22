from django.urls import path

from apps.ol_commitments.views import (
    LapseReviewView,
    OverdueNotificationsView,
    ProcessOverdueView,
)

urlpatterns = [
    path("commitments/process-overdue/", ProcessOverdueView.as_view(), name="ol-commitments-process-overdue"),
    path("commitments/lapse-review/", LapseReviewView.as_view(), name="ol-commitments-lapse-review"),
    path("notifications/overdue/", OverdueNotificationsView.as_view(), name="ol-commitments-overdue-notifications"),
]