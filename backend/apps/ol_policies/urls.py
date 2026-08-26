from django.urls import path

from .views import PolicyDetailView, PolicyListView

app_name = "ol_policies"

urlpatterns = [
    path("policies/", PolicyListView.as_view(), name="policy-list"),
    path("policies/<uuid:policy_id>/", PolicyDetailView.as_view(), name="policy-detail"),
]
