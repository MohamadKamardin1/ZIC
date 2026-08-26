"""Partner portal receipts aliases mounted at ``/api/v1/portal/receipts/``.

Read-only, partner-scoped views reused from the receipts module so the web
portal consumes ``/api/v1/portal/receipts/`` while the front-office register
keeps ``/api/v1/front-office/receipts/portal/`` for compatibility.
"""

from django.urls import path

from apps.front_office.receipts.views import (
    PartnerPortalReceiptDetailView,
    PartnerPortalReceiptListView,
)

urlpatterns = [
    path("", PartnerPortalReceiptListView.as_view(), name="portal-receipts-list"),
    path("<uuid:receipt_id>/", PartnerPortalReceiptDetailView.as_view(), name="portal-receipts-detail"),
]
