from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PartnerApplicationViewSet,
    PartnerApplicationDocumentViewSet,
    PartnerApplicationTaskViewSet,
    download_template,
    bulk_upload,
)

router = DefaultRouter()
router.register(r"applications", PartnerApplicationViewSet, basename="partner-applications")

application_documents = PartnerApplicationDocumentViewSet.as_view({
    "get": "list",
    "post": "create",
})
application_document_detail = PartnerApplicationDocumentViewSet.as_view({
    "get": "retrieve",
    "delete": "destroy",
})
application_document_verify = PartnerApplicationDocumentViewSet.as_view({
    "post": "verify",
})
application_tasks = PartnerApplicationTaskViewSet.as_view({
    "get": "list",
    "post": "create",
})
application_task_detail = PartnerApplicationTaskViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})
application_task_complete = PartnerApplicationTaskViewSet.as_view({
    "post": "complete",
})

urlpatterns = [
    path("applications/bulk-upload/template/", download_template, name="bulk-upload-template"),
    path("applications/bulk-upload/", bulk_upload, name="bulk-upload"),
    path("", include(router.urls)),
    path(
        "applications/<uuid:application_pk>/documents/",
        application_documents,
        name="application-documents",
    ),
    path(
        "applications/<uuid:application_pk>/documents/<uuid:pk>/",
        application_document_detail,
        name="application-document-detail",
    ),
    path(
        "applications/<uuid:application_pk>/documents/<uuid:pk>/verify/",
        application_document_verify,
        name="application-document-verify",
    ),
    path(
        "applications/<uuid:application_pk>/tasks/",
        application_tasks,
        name="application-tasks",
    ),
    path(
        "applications/<uuid:application_pk>/tasks/<uuid:pk>/",
        application_task_detail,
        name="application-task-detail",
    ),
    path(
        "applications/<uuid:application_pk>/tasks/<uuid:pk>/complete/",
        application_task_complete,
        name="application-task-complete",
    ),
]
