"""
GC Parameters — URL Configuration

Registers the GC Parameters bounded context under /api/v1/gc/:
- /api/v1/gc/parameters/...  List/Detail APIs for every parameter entity.
- /api/v1/gc/options/...      SmartSelects option endpoints ({value, label, meta}).

The permission namespace is gc_parameters.* for all of these.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.group_credit import options, views

router = DefaultRouter()

# Layer 1 — Scheme Setup
router.register(r"scheme-types", views.GCSchemeTypeViewSet, basename="gc-param-scheme-type")
router.register(r"scheme-rates", views.GCSchemePremiumRateViewSet, basename="gc-param-scheme-rate")
router.register(r"scheme-statuses", views.GCSchemeStatusViewSet, basename="gc-param-scheme-status")
router.register(r"member-statuses", views.GCSchemeMemberStatusViewSet, basename="gc-param-member-status")
router.register(r"renewal-statuses", views.GCSchemeRenewalStatusViewSet, basename="gc-param-renewal-status")
router.register(r"health-questions", views.GCHealthQuestionViewSet, basename="gc-param-health-question")
router.register(r"health-questionnaires", views.GCHealthQuestionnaireViewSet, basename="gc-param-health-questionnaire")
router.register(r"lookup-values", views.GCLookupValueViewSet, basename="gc-param-lookup-value")

# Layer 2 — Products & Riders
router.register(r"sub-products", views.GCSubProductViewSet, basename="gc-param-sub-product")
router.register(r"products", views.GCProductViewSet, basename="gc-param-product")
router.register(r"riders", views.GCRiderViewSet, basename="gc-param-rider")
router.register(r"rider-rates", views.GCRiderRateViewSet, basename="gc-param-rider-rate")

# Layer 4 — Medical Underwriting
router.register(r"medical/codes", views.GCMedicalCodeViewSet, basename="gc-param-medical-code")
router.register(r"medical/limits", views.GCMedicalLimitViewSet, basename="gc-param-medical-limit")
router.register(r"medical/decisions", views.GCUnderwritingDecisionViewSet, basename="gc-param-uw-decision")
router.register(r"medical/habits", views.GCPersonalHabitViewSet, basename="gc-param-personal-habit")
router.register(r"medical/histories", views.GCMedicalHistoryViewSet, basename="gc-param-medical-history")
router.register(r"medical/facilities", views.GCMedicalFacilityViewSet, basename="gc-param-medical-facility")
router.register(r"medical/practitioners", views.GCMedicalPractitionerViewSet, basename="gc-param-medical-practitioner")

# Layer 5 — Claim Setup
router.register(r"claims/types", views.GCClaimTypeViewSet, basename="gc-param-claim-type")
router.register(r"claims/reasons", views.GCClaimReasonViewSet, basename="gc-param-claim-reason")
router.register(r"claims/statuses", views.GCClaimStatusViewSet, basename="gc-param-claim-status")
router.register(r"claims/discharge-types", views.GCDischargeTypeViewSet, basename="gc-param-discharge-type")
router.register(r"claims/correspondent-types", views.GCCorrespondentTypeViewSet, basename="gc-param-correspondent-type")

urlpatterns = [
    path("parameters/", include(router.urls)),
    # SmartSelects options
    path("options/scheme-types/", options.GCSchemeTypeOptionView.as_view(), name="gc-option-scheme-types"),
    path("options/products/", options.GCProductOptionView.as_view(), name="gc-option-products"),
    path("options/questionnaires/", options.GCQuestionnaireOptionView.as_view(), name="gc-option-questionnaires"),
    path("options/claim-types/", options.GCClaimTypeOptionView.as_view(), name="gc-option-claim-types"),
]
