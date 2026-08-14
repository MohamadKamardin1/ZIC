from django.urls import path

from .views import (
    CurrencyPairDetailView,
    CurrencyPairListView,
    CurrencyRefreshView,
    DashboardAlertDetailView,
    DashboardAlertListView,
    DashboardNotificationListView,
    DashboardNotificationReadAllView,
    DashboardNotificationReadView,
    DashboardOverviewView,
    DashboardTaskDetailView,
    DashboardTaskListCreateView,
    GlobalSearchView,
)

app_name = "dashboard"

urlpatterns = [
    path("overview/", DashboardOverviewView.as_view(), name="overview"),
    path("search/", GlobalSearchView.as_view(), name="search"),
    path("tasks/", DashboardTaskListCreateView.as_view(), name="tasks"),
    path("tasks/<int:pk>/", DashboardTaskDetailView.as_view(), name="task-detail"),
    path("alerts/", DashboardAlertListView.as_view(), name="alerts"),
    path("alerts/<int:pk>/<str:action>/", DashboardAlertDetailView.as_view(), name="alert-action"),
    path("notifications/", DashboardNotificationListView.as_view(), name="notifications"),
    path("notifications/<int:pk>/read/", DashboardNotificationReadView.as_view(), name="notification-read"),
    path("notifications/read-all/", DashboardNotificationReadAllView.as_view(), name="notification-read-all"),
    path("currencies/", CurrencyPairListView.as_view(), name="currencies"),
    path("currencies/<int:pk>/", CurrencyPairDetailView.as_view(), name="currency-detail"),
    path("currencies/refresh/", CurrencyRefreshView.as_view(), name="currency-refresh"),
]
