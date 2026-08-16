from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PartnerApplicationViewSet,
    PartnerApplicationDocumentViewSet,
    PartnerApplicationTaskViewSet,
    BranchViewSet,
    LocationViewSet,
    ApplicationPartnerTypeViewSet,
    ApplicationContactViewSet,
    ApplicationBankAccountViewSet,
    ApplicationFieldValueViewSet,
    ApplicationPartnerTypeSetupViewSet,
    download_template,
    bulk_upload,
    choices,
    UnifiedOnboardingRecordViewSet,
)

router = DefaultRouter()
router.register(r"applications", PartnerApplicationViewSet, basename="partner-applications")
router.register(r"unified-records", UnifiedOnboardingRecordViewSet, basename="unified-records")
router.register(r"branches", BranchViewSet, basename="branches")
router.register(r"locations", LocationViewSet, basename="locations")

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
    path("choices/", choices, name="choices"),
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
    path(
        "applications/<uuid:application_pk>/partner-types/",
        ApplicationPartnerTypeViewSet.as_view({"get": "list", "post": "create"}),
        name="application-partner-types",
    ),
    path(
        "applications/<uuid:application_pk>/partner-types/<uuid:pk>/",
        ApplicationPartnerTypeViewSet.as_view({
            "get": "retrieve",
            "put": "update",
            "patch": "partial_update",
            "delete": "destroy",
        }),
        name="application-partner-type-detail",
    ),
    path(
        "applications/<uuid:application_pk>/partner-types/<uuid:pk>/setup/field-values/",
        ApplicationPartnerTypeSetupViewSet.as_view({"get": "field_values", "patch": "field_values"}),
        name="application-partner-type-field-values",
    ),
    path(
        "applications/<uuid:application_pk>/partner-types/<uuid:pk>/setup/contacts/",
        ApplicationPartnerTypeSetupViewSet.as_view({"get": "contacts", "post": "contacts"}),
        name="application-partner-type-contacts",
    ),
    path(
        "applications/<uuid:application_pk>/partner-types/<uuid:pk>/setup/contacts/<uuid:contact_pk>/",
        ApplicationPartnerTypeSetupViewSet.as_view({"patch": "contact_detail", "put": "contact_detail", "delete": "contact_detail"}),
        name="application-partner-type-contact-detail",
    ),
    path(
        "applications/<uuid:application_pk>/partner-types/<uuid:pk>/setup/bank-accounts/",
        ApplicationPartnerTypeSetupViewSet.as_view({"get": "banks", "post": "banks"}),
        name="application-partner-type-bank-accounts",
    ),
    path(
        "applications/<uuid:application_pk>/partner-types/<uuid:pk>/setup/bank-accounts/<uuid:bank_pk>/",
        ApplicationPartnerTypeSetupViewSet.as_view({"patch": "bank_detail", "put": "bank_detail", "delete": "bank_detail"}),
        name="application-partner-type-bank-account-detail",
    ),
    path(
        "applications/<uuid:application_pk>/contacts/",
        ApplicationContactViewSet.as_view({"get": "list", "post": "create"}),
        name="application-contacts",
    ),
    path(
        "applications/<uuid:application_pk>/contacts/<uuid:pk>/",
        ApplicationContactViewSet.as_view({"delete": "destroy"}),
        name="application-contact-detail",
    ),
    path(
        "applications/<uuid:application_pk>/bank-accounts/",
        ApplicationBankAccountViewSet.as_view({"get": "list", "post": "create"}),
        name="application-bank-accounts",
    ),
    path(
        "applications/<uuid:application_pk>/bank-accounts/<uuid:pk>/",
        ApplicationBankAccountViewSet.as_view({"delete": "destroy"}),
        name="application-bank-account-detail",
    ),
    path(
        "applications/<uuid:application_pk>/field-values/",
        ApplicationFieldValueViewSet.as_view({"get": "list", "post": "create"}),
        name="application-field-values",
    ),
    path(
        "applications/<uuid:application_pk>/field-values/batch/",
        ApplicationFieldValueViewSet.as_view({"patch": "batch_update"}),
        name="application-field-values-batch",
    ),
    path(
        "applications/<uuid:application_pk>/field-values/<uuid:pk>/",
        ApplicationFieldValueViewSet.as_view({"delete": "destroy"}),
        name="application-field-value-detail",
    ),
]
