from django.urls import path

from apps.front_office.receipts.views import (
    ExchangeRateView,
    ReceiptAllocateView,
    ReceiptAllocationOptionsView,
    ReceiptAutoAllocateView,
    ReceiptDetailView,
    ReceiptListView,
    ReceiptOptionsView,
    ReceiptPostView,
)

urlpatterns = [
    path("", ReceiptListView.as_view(), name="receipts-list"),
    path("options/", ReceiptOptionsView.as_view(), name="receipts-options"),
    path("exchange-rate/", ExchangeRateView.as_view(), name="receipts-exchange-rate"),
    path("<uuid:receipt_id>/allocation-options/", ReceiptAllocationOptionsView.as_view(), name="receipts-allocation-options"),
    path("<uuid:receipt_id>/allocate/", ReceiptAllocateView.as_view(), name="receipts-allocate"),
    path("<uuid:receipt_id>/auto-allocate/", ReceiptAutoAllocateView.as_view(), name="receipts-auto-allocate"),
    path("<uuid:receipt_id>/post/", ReceiptPostView.as_view(), name="receipts-post"),
    path("<uuid:receipt_id>/", ReceiptDetailView.as_view(), name="receipts-detail"),
]
