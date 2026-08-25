from django.urls import path

from apps.front_office.receipts.views import (
    ExchangeRateView,
    ReceiptAllocateView,
    ReceiptAllocationOptionsView,
    ReceiptAllocationReverseView,
    ReceiptAutoAllocateView,
    ReceiptCancelView,
    ReceiptDetailView,
    ReceiptDocumentDownloadView,
    ReceiptDocumentsView,
    ReceiptExportView,
    ReceiptKpisView,
    ReceiptListView,
    ReceiptOptionsView,
    ReceiptPostView,
    ReceiptPrintView,
    ReceiptReverseView,
)

urlpatterns = [
    path("", ReceiptListView.as_view(), name="receipts-list"),
    path("kpis/", ReceiptKpisView.as_view(), name="receipts-kpis"),
    path("export/", ReceiptExportView.as_view(), name="receipts-export"),
    path("options/", ReceiptOptionsView.as_view(), name="receipts-options"),
    path("exchange-rate/", ExchangeRateView.as_view(), name="receipts-exchange-rate"),
    path("documents/<uuid:document_id>/download/", ReceiptDocumentDownloadView.as_view(), name="receipts-document-download"),
    path("<uuid:receipt_id>/allocation-options/", ReceiptAllocationOptionsView.as_view(), name="receipts-allocation-options"),
    path("<uuid:receipt_id>/allocate/", ReceiptAllocateView.as_view(), name="receipts-allocate"),
    path("<uuid:receipt_id>/auto-allocate/", ReceiptAutoAllocateView.as_view(), name="receipts-auto-allocate"),
    path("<uuid:receipt_id>/reverse/", ReceiptReverseView.as_view(), name="receipts-reverse"),
    path("<uuid:receipt_id>/allocations/<uuid:allocation_id>/reverse/", ReceiptAllocationReverseView.as_view(), name="receipts-allocation-reverse"),
    path("<uuid:receipt_id>/cancel/", ReceiptCancelView.as_view(), name="receipts-cancel"),
    path("<uuid:receipt_id>/post/", ReceiptPostView.as_view(), name="receipts-post"),
    path("<uuid:receipt_id>/print/", ReceiptPrintView.as_view(), name="receipts-print"),
    path("<uuid:receipt_id>/documents/", ReceiptDocumentsView.as_view(), name="receipts-documents"),
    path("<uuid:receipt_id>/", ReceiptDetailView.as_view(), name="receipts-detail"),
]
