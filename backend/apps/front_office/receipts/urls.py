from django.urls import path

from apps.front_office.receipts.views import ReceiptDetailView, ReceiptListView, ReceiptOptionsView

urlpatterns = [
    path("", ReceiptListView.as_view(), name="receipts-list"),
    path("options/", ReceiptOptionsView.as_view(), name="receipts-options"),
    path("<uuid:receipt_id>/", ReceiptDetailView.as_view(), name="receipts-detail"),
]
