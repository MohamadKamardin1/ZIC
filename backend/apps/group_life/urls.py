"""
Group Life — URL Configuration

REST router registrations for all Group Life ViewSets.
Mounted at: /api/v1/group-life/
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.group_life.views import (
    # Layer 1 — Setup
    GLSchemeTypeViewSet, GLSchemeStatusViewSet,
    GLSchemeMemberStatusViewSet, GLSchemeRenewalStatusViewSet,
    GLSchemePremiumRateViewSet, GLHealthQuestionViewSet,
    GLHealthQuestionnaireViewSet,
    # Layer 2 — Products & Riders
    GLSubProductViewSet, GLProductViewSet,
    GLRiderViewSet, GLRiderRateViewSet,
    # Layer 3 — Quotations
    GLQuotationViewSet, GLQuotationCategoryViewSet, GLQuotationRiderViewSet,
    # Layer 4 — Schemes & Members
    GLSchemeViewSet, GLSchemeCategoryViewSet, GLSchemeRiderViewSet,
    GLSchemeMemberViewSet, GLSchemeMemberDependentViewSet,
    # Layer 5 — Medical UW
    GLMedicalCodeViewSet, GLMedicalLimitViewSet,
    GLUnderwritingDecisionViewSet, GLPersonalHabitViewSet,
    GLMedicalHistoryViewSet, GLMedicalFacilityViewSet,
    GLMedicalPractitionerViewSet, GLMedicalCaseViewSet,
    # Layer 6 — Claims
    GLClaimTypeViewSet, GLClaimReasonViewSet, GLClaimStatusViewSet,
    GLDischargeTypeViewSet, GLCorrespondentTypeViewSet,
    GLClaimViewSet, GLClaimInstallmentViewSet, GLMedicalInvoiceViewSet,
    # Layer 7 — Renewals
    GLSchemeRenewalViewSet,
)


# ---------------------------------------------------------------------------
# Setup Router — /api/v1/group-life/setup/
# ---------------------------------------------------------------------------

setup_router = DefaultRouter()
setup_router.register(r"scheme-types", GLSchemeTypeViewSet, basename="gl-scheme-types")
setup_router.register(r"scheme-statuses", GLSchemeStatusViewSet, basename="gl-scheme-statuses")
setup_router.register(r"member-statuses", GLSchemeMemberStatusViewSet, basename="gl-member-statuses")
setup_router.register(r"renewal-statuses", GLSchemeRenewalStatusViewSet, basename="gl-renewal-statuses")
setup_router.register(r"premium-rates", GLSchemePremiumRateViewSet, basename="gl-premium-rates")
setup_router.register(r"sub-products", GLSubProductViewSet, basename="gl-sub-products")
setup_router.register(r"products", GLProductViewSet, basename="gl-products")
setup_router.register(r"riders", GLRiderViewSet, basename="gl-riders")
setup_router.register(r"rider-rates", GLRiderRateViewSet, basename="gl-rider-rates")
setup_router.register(r"health-questions", GLHealthQuestionViewSet, basename="gl-health-questions")
setup_router.register(r"health-questionnaires", GLHealthQuestionnaireViewSet, basename="gl-health-questionnaires")
setup_router.register(r"claim-types", GLClaimTypeViewSet, basename="gl-claim-types")
setup_router.register(r"claim-reasons", GLClaimReasonViewSet, basename="gl-claim-reasons")
setup_router.register(r"claim-statuses", GLClaimStatusViewSet, basename="gl-claim-statuses")
setup_router.register(r"discharge-types", GLDischargeTypeViewSet, basename="gl-discharge-types")
setup_router.register(r"correspondent-types", GLCorrespondentTypeViewSet, basename="gl-correspondent-types")
setup_router.register(r"medical-codes", GLMedicalCodeViewSet, basename="gl-medical-codes")
setup_router.register(r"medical-facilities", GLMedicalFacilityViewSet, basename="gl-medical-facilities")
setup_router.register(r"medical-practitioners", GLMedicalPractitionerViewSet, basename="gl-medical-practitioners")
setup_router.register(r"medical-limits", GLMedicalLimitViewSet, basename="gl-medical-limits")
setup_router.register(r"uw-decisions", GLUnderwritingDecisionViewSet, basename="gl-uw-decisions")
setup_router.register(r"personal-habits", GLPersonalHabitViewSet, basename="gl-personal-habits")
setup_router.register(r"medical-histories", GLMedicalHistoryViewSet, basename="gl-medical-histories")


# ---------------------------------------------------------------------------
# Main Router — /api/v1/group-life/
# ---------------------------------------------------------------------------

main_router = DefaultRouter()
main_router.register(r"quotations", GLQuotationViewSet, basename="gl-quotations")
main_router.register(r"schemes", GLSchemeViewSet, basename="gl-schemes")
main_router.register(r"members", GLSchemeMemberViewSet, basename="gl-members")
main_router.register(r"medical-cases", GLMedicalCaseViewSet, basename="gl-medical-cases")
main_router.register(r"claims", GLClaimViewSet, basename="gl-claims")
main_router.register(r"medical-invoices", GLMedicalInvoiceViewSet, basename="gl-medical-invoices")
main_router.register(r"renewals", GLSchemeRenewalViewSet, basename="gl-renewals")


# ---------------------------------------------------------------------------
# Nested resource views
# ---------------------------------------------------------------------------

# Quotation nested resources
quotation_categories = GLQuotationCategoryViewSet.as_view({"get": "list", "post": "create"})
quotation_category_detail = GLQuotationCategoryViewSet.as_view({
    "get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy",
})
quotation_riders = GLQuotationRiderViewSet.as_view({"get": "list", "post": "create"})
quotation_rider_detail = GLQuotationRiderViewSet.as_view({
    "get": "retrieve", "delete": "destroy",
})

# Scheme nested resources
scheme_categories = GLSchemeCategoryViewSet.as_view({"get": "list", "post": "create"})
scheme_category_detail = GLSchemeCategoryViewSet.as_view({
    "get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy",
})
scheme_riders = GLSchemeRiderViewSet.as_view({"get": "list", "post": "create"})
scheme_rider_detail = GLSchemeRiderViewSet.as_view({
    "get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy",
})
scheme_members = GLSchemeMemberViewSet.as_view({"get": "list", "post": "create"})
scheme_member_detail = GLSchemeMemberViewSet.as_view({
    "get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy",
})

# Member nested resources
member_dependents = GLSchemeMemberDependentViewSet.as_view({"get": "list", "post": "create"})
member_dependent_detail = GLSchemeMemberDependentViewSet.as_view({
    "get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy",
})

# Claim nested resources
claim_installments = GLClaimInstallmentViewSet.as_view({"get": "list", "post": "create"})
claim_installment_detail = GLClaimInstallmentViewSet.as_view({
    "get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy",
})


urlpatterns = [
    # Setup endpoints
    path("setup/", include(setup_router.urls)),

    # Main CRUD endpoints
    path("", include(main_router.urls)),

    # Quotation nested resources
    path(
        "quotations/<uuid:quotation_pk>/categories/",
        quotation_categories, name="gl-quotation-categories",
    ),
    path(
        "quotations/<uuid:quotation_pk>/categories/<uuid:pk>/",
        quotation_category_detail, name="gl-quotation-category-detail",
    ),
    path(
        "quotations/<uuid:quotation_pk>/riders/",
        quotation_riders, name="gl-quotation-riders",
    ),
    path(
        "quotations/<uuid:quotation_pk>/riders/<uuid:pk>/",
        quotation_rider_detail, name="gl-quotation-rider-detail",
    ),

    # Scheme nested resources
    path(
        "schemes/<uuid:scheme_pk>/categories/",
        scheme_categories, name="gl-scheme-categories",
    ),
    path(
        "schemes/<uuid:scheme_pk>/categories/<uuid:pk>/",
        scheme_category_detail, name="gl-scheme-category-detail",
    ),
    path(
        "schemes/<uuid:scheme_pk>/riders/",
        scheme_riders, name="gl-scheme-riders",
    ),
    path(
        "schemes/<uuid:scheme_pk>/riders/<uuid:pk>/",
        scheme_rider_detail, name="gl-scheme-rider-detail",
    ),
    path(
        "schemes/<uuid:scheme_pk>/members/",
        scheme_members, name="gl-scheme-members",
    ),
    path(
        "schemes/<uuid:scheme_pk>/members/<uuid:pk>/",
        scheme_member_detail, name="gl-scheme-member-detail",
    ),

    # Member nested resources
    path(
        "members/<uuid:member_pk>/dependents/",
        member_dependents, name="gl-member-dependents",
    ),
    path(
        "members/<uuid:member_pk>/dependents/<uuid:pk>/",
        member_dependent_detail, name="gl-member-dependent-detail",
    ),

    # Claim nested resources
    path(
        "claims/<uuid:claim_pk>/installments/",
        claim_installments, name="gl-claim-installments",
    ),
    path(
        "claims/<uuid:claim_pk>/installments/<uuid:pk>/",
        claim_installment_detail, name="gl-claim-installment-detail",
    ),
]
