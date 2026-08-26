from django.urls import path

from .views import (
    BrandingConfigurationView,
    DocumentDownloadView,
    DocumentInstanceListView,
    DocumentRenderView,
)

app_name = "documents"

urlpatterns = [
    path("branding/", BrandingConfigurationView.as_view(), name="branding"),
    path("render/<str:document_type>/<str:object_id>/", DocumentRenderView.as_view(), name="render"),
    path("instances/", DocumentInstanceListView.as_view(), name="instances"),
    path("instances/<uuid:pk>/download/", DocumentDownloadView.as_view(), name="download"),
    path("instances/<uuid:pk>/preview/", DocumentDownloadView.as_view(), name="preview"),
]
