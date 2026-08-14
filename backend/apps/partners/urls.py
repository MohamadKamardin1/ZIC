from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PartnerViewSet,
    PartnerTypeViewSet,
    PartnerTypeDocumentRequirementViewSet,
    PartnerTypeFieldConfigurationViewSet,
    PartnerTypeContactRequirementViewSet,
    PartnerTypeBankRequirementViewSet,
    PartnerTypeAssignmentSetupViewSet,
    UserPartnerLinkViewSet,
    PartnerContextView,
)

router = DefaultRouter()
router.register(r"links", UserPartnerLinkViewSet, basename="partner-links")
router.register(r"", PartnerViewSet, basename="partners")

partner_type_list = PartnerTypeViewSet.as_view({
    "get": "list",
    "post": "create",
})
partner_type_detail = PartnerTypeViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

doc_requirement_list = PartnerTypeDocumentRequirementViewSet.as_view({
    "get": "list",
    "post": "create",
})
doc_requirement_detail = PartnerTypeDocumentRequirementViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

field_config_list = PartnerTypeFieldConfigurationViewSet.as_view({
    "get": "list",
    "post": "create",
})
field_config_detail = PartnerTypeFieldConfigurationViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

contact_req_list = PartnerTypeContactRequirementViewSet.as_view({
    "get": "list",
    "post": "create",
})
contact_req_detail = PartnerTypeContactRequirementViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

bank_req_list = PartnerTypeBankRequirementViewSet.as_view({
    "get": "list",
    "post": "create",
})
bank_req_detail = PartnerTypeBankRequirementViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

urlpatterns = [
    path("context/", PartnerContextView.as_view(), name="partner-context"),
    path("types/", partner_type_list, name="partner-types-list"),
    path("types/<uuid:pk>/", partner_type_detail, name="partner-types-detail"),
    path(
        "types/<uuid:partner_type_pk>/documents/",
        doc_requirement_list,
        name="partner-type-documents",
    ),
    path(
        "types/<uuid:partner_type_pk>/documents/<uuid:pk>/",
        doc_requirement_detail,
        name="partner-type-document-detail",
    ),
    path(
        "types/<uuid:partner_type_pk>/fields/",
        field_config_list,
        name="partner-type-fields",
    ),
    path(
        "types/<uuid:partner_type_pk>/fields/<uuid:pk>/",
        field_config_detail,
        name="partner-type-field-detail",
    ),
    path(
        "types/<uuid:partner_type_pk>/contacts/",
        contact_req_list,
        name="partner-type-contacts",
    ),
    path(
        "types/<uuid:partner_type_pk>/contacts/<uuid:pk>/",
        contact_req_detail,
        name="partner-type-contact-detail",
    ),
    path(
        "types/<uuid:partner_type_pk>/banks/",
        bank_req_list,
        name="partner-type-banks",
    ),
    path(
        "types/<uuid:partner_type_pk>/banks/<uuid:pk>/",
        bank_req_detail,
        name="partner-type-bank-detail",
    ),
    path(
        "assignments/<uuid:pk>/setup/summary/",
        PartnerTypeAssignmentSetupViewSet.as_view({"get": "summary"}),
        name="assignment-setup-summary",
    ),
    path(
        "assignments/<uuid:pk>/setup/documents/",
        PartnerTypeAssignmentSetupViewSet.as_view({
            "get": "manage_documents",
            "post": "manage_documents",
        }),
        name="assignment-setup-documents",
    ),
    path(
        "assignments/<uuid:pk>/setup/documents/<uuid:document_pk>/",
        PartnerTypeAssignmentSetupViewSet.as_view({
            "get": "manage_document_detail",
            "patch": "manage_document_detail",
        }),
        name="assignment-setup-document-detail",
    ),
    path(
        "assignments/<uuid:pk>/setup/field-values/",
        PartnerTypeAssignmentSetupViewSet.as_view({
            "get": "manage_field_values",
            "patch": "manage_field_values",
        }),
        name="assignment-setup-field-values",
    ),
    path(
        "assignments/<uuid:pk>/setup/contacts/",
        PartnerTypeAssignmentSetupViewSet.as_view({
            "get": "manage_contacts",
            "post": "manage_contacts",
        }),
        name="assignment-setup-contacts",
    ),
    path(
        "assignments/<uuid:pk>/setup/contacts/<uuid:contact_pk>/",
        PartnerTypeAssignmentSetupViewSet.as_view({
            "get": "manage_contact_detail",
            "patch": "manage_contact_detail",
            "delete": "manage_contact_detail",
        }),
        name="assignment-setup-contact-detail",
    ),
    path(
        "assignments/<uuid:pk>/setup/bank-accounts/",
        PartnerTypeAssignmentSetupViewSet.as_view({
            "get": "manage_bank_accounts",
            "post": "manage_bank_accounts",
        }),
        name="assignment-setup-bank-accounts",
    ),
    path(
        "assignments/<uuid:pk>/setup/bank-accounts/<uuid:bank_pk>/",
        PartnerTypeAssignmentSetupViewSet.as_view({
            "get": "manage_bank_detail",
            "patch": "manage_bank_detail",
            "delete": "manage_bank_detail",
        }),
        name="assignment-setup-bank-detail",
    ),
    path(
        "assignments/<uuid:pk>/setup/kyc/",
        PartnerTypeAssignmentSetupViewSet.as_view({
            "get": "manage_kyc",
            "patch": "manage_kyc",
        }),
        name="assignment-setup-kyc",
    ),
    path(
        "assignments/<uuid:pk>/history/",
        PartnerTypeAssignmentSetupViewSet.as_view({"get": "history"}),
        name="assignment-history",
    ),
    path(
        "assignments/<uuid:pk>/activate/",
        PartnerTypeAssignmentSetupViewSet.as_view({"post": "activate"}),
        name="assignment-activate",
    ),
    path(
        "assignments/<uuid:pk>/deactivate/",
        PartnerTypeAssignmentSetupViewSet.as_view({"post": "deactivate"}),
        name="assignment-deactivate",
    ),
    path("", include(router.urls)),
]
