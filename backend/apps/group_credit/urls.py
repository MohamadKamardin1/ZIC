"""
Group Credit — URL Configuration

Registers all REST API endpoints for the Group Credit module
under the /api/v1/group-credit/ namespace.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.group_credit import views

router = DefaultRouter()

# Layer 1 — Parameters / Setup
router.register(r"lookup-values", views.GCLookupValueViewSet, basename="gc-lookup-value")
router.register(r"scheme-types", views.GCSchemeTypeViewSet, basename="gc-scheme-type")
router.register(r"scheme-statuses", views.GCSchemeStatusViewSet, basename="gc-scheme-status")
router.register(r"member-statuses", views.GCSchemeMemberStatusViewSet, basename="gc-member-status")
router.register(r"renewal-statuses", views.GCSchemeRenewalStatusViewSet, basename="gc-renewal-status")
router.register(r"premium-rates", views.GCSchemePremiumRateViewSet, basename="gc-premium-rate")
router.register(r"health-questions", views.GCHealthQuestionViewSet, basename="gc-health-question")
router.register(r"health-questionnaires", views.GCHealthQuestionnaireViewSet, basename="gc-health-questionnaire")

# Layer 2 — Products & Riders
router.register(r"sub-products", views.GCSubProductViewSet, basename="gc-sub-product")
router.register(r"products", views.GCProductViewSet, basename="gc-product")
router.register(r"riders", views.GCRiderViewSet, basename="gc-rider")
router.register(r"rider-rates", views.GCRiderRateViewSet, basename="gc-rider-rate")

# Layer 3 — Quotations
router.register(r"quotations", views.GCQuotationViewSet, basename="gc-quotation")

# Layer 4 — Schemes & Members
router.register(r"schemes", views.GCSchemeViewSet, basename="gc-scheme")
router.register(r"members", views.GCSchemeMemberViewSet, basename="gc-member")

# Layer 5 — Medical UW
router.register(r"medical-codes", views.GCMedicalCodeViewSet, basename="gc-medical-code")
router.register(r"medical-limits", views.GCMedicalLimitViewSet, basename="gc-medical-limit")
router.register(r"uw-decisions", views.GCUnderwritingDecisionViewSet, basename="gc-uw-decision")
router.register(r"personal-habits", views.GCPersonalHabitViewSet, basename="gc-personal-habit")
router.register(r"medical-history", views.GCMedicalHistoryViewSet, basename="gc-medical-history")
router.register(r"medical-facilities", views.GCMedicalFacilityViewSet, basename="gc-medical-facility")
router.register(r"medical-practitioners", views.GCMedicalPractitionerViewSet, basename="gc-medical-practitioner")
router.register(r"medical-cases", views.GCMedicalCaseViewSet, basename="gc-medical-case")

# Layer 6 — Claims
router.register(r"claim-types", views.GCClaimTypeViewSet, basename="gc-claim-type")
router.register(r"claim-reasons", views.GCClaimReasonViewSet, basename="gc-claim-reason")
router.register(r"claim-statuses", views.GCClaimStatusViewSet, basename="gc-claim-status")
router.register(r"discharge-types", views.GCDischargeTypeViewSet, basename="gc-discharge-type")
router.register(r"correspondent-types", views.GCCorrespondentTypeViewSet, basename="gc-correspondent-type")
router.register(r"claims", views.GCClaimViewSet, basename="gc-claim")
router.register(r"medical-invoices", views.GCMedicalInvoiceViewSet, basename="gc-medical-invoice")

# Layer 7 — Renewals
router.register(r"renewals", views.GCSchemeRenewalViewSet, basename="gc-renewal")

# Nested resources
quotation_category_list = views.GCQuotationCategoryViewSet.as_view({
    "get": "list", "post": "create",
})
quotation_category_detail = views.GCQuotationCategoryViewSet.as_view({
    "get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy",
})
quotation_rider_list = views.GCQuotationRiderViewSet.as_view({
    "get": "list", "post": "create",
})
quotation_rider_detail = views.GCQuotationRiderViewSet.as_view({
    "get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy",
})
scheme_category_list = views.GCSchemeCategoryViewSet.as_view({
    "get": "list", "post": "create",
})
scheme_category_detail = views.GCSchemeCategoryViewSet.as_view({
    "get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy",
})
scheme_rider_list = views.GCSchemeRiderViewSet.as_view({
    "get": "list", "post": "create",
})
scheme_rider_detail = views.GCSchemeRiderViewSet.as_view({
    "get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy",
})
scheme_member_list = views.GCSchemeMemberViewSet.as_view({
    "get": "list", "post": "create",
})
scheme_member_detail = views.GCSchemeMemberViewSet.as_view({
    "get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy",
})
member_dependent_list = views.GCSchemeMemberDependentViewSet.as_view({
    "get": "list", "post": "create",
})
member_dependent_detail = views.GCSchemeMemberDependentViewSet.as_view({
    "get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy",
})
claim_installment_list = views.GCClaimInstallmentViewSet.as_view({
    "get": "list", "post": "create",
})
claim_installment_detail = views.GCClaimInstallmentViewSet.as_view({
    "get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy",
})

urlpatterns = [
    path("", include(router.urls)),

    # Quotation nested resources
    path(
        "quotations/<uuid:quotation_pk>/categories/",
        quotation_category_list, name="gc-quotation-category-list",
    ),
    path(
        "quotations/<uuid:quotation_pk>/categories/<uuid:pk>/",
        quotation_category_detail, name="gc-quotation-category-detail",
    ),
    path(
        "quotations/<uuid:quotation_pk>/riders/",
        quotation_rider_list, name="gc-quotation-rider-list",
    ),
    path(
        "quotations/<uuid:quotation_pk>/riders/<uuid:pk>/",
        quotation_rider_detail, name="gc-quotation-rider-detail",
    ),

    # Scheme nested resources
    path(
        "schemes/<uuid:scheme_pk>/categories/",
        scheme_category_list, name="gc-scheme-category-list",
    ),
    path(
        "schemes/<uuid:scheme_pk>/categories/<uuid:pk>/",
        scheme_category_detail, name="gc-scheme-category-detail",
    ),
    path(
        "schemes/<uuid:scheme_pk>/riders/",
        scheme_rider_list, name="gc-scheme-rider-list",
    ),
    path(
        "schemes/<uuid:scheme_pk>/riders/<uuid:pk>/",
        scheme_rider_detail, name="gc-scheme-rider-detail",
    ),
    path(
        "schemes/<uuid:scheme_pk>/members/",
        scheme_member_list, name="gc-scheme-member-list",
    ),
    path(
        "schemes/<uuid:scheme_pk>/members/<uuid:pk>/",
        scheme_member_detail, name="gc-scheme-member-detail",
    ),

    # Member nested resources
    path(
        "members/<uuid:member_pk>/dependents/",
        member_dependent_list, name="gc-member-dependent-list",
    ),
    path(
        "members/<uuid:member_pk>/dependents/<uuid:pk>/",
        member_dependent_detail, name="gc-member-dependent-detail",
    ),

    # Claim nested resources
    path(
        "claims/<uuid:claim_pk>/installments/",
        claim_installment_list, name="gc-claim-installment-list",
    ),
    path(
        "claims/<uuid:claim_pk>/installments/<uuid:pk>/",
        claim_installment_detail, name="gc-claim-installment-detail",
    ),
]
