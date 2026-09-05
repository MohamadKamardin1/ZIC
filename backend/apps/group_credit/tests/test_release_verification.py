"""Prompt 6 — end-to-end integration, permission, audit, and field-coverage checks.

Verifies the GC Parameters bounded context holds together: the Scheme Type →
Product → Rider chain resolves both ways, the parameter APIs reject anonymous
callers and admit authenticated ones, a parameter change is fully audited
(actor / before / after / reason), and every audited parameter model carries the
four audit columns (created_at, updated_at, created_by, updated_by).
"""

from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.governance.models import AuditLog
from apps.governance.services.audit_service import AuditContext
from apps.group_credit.audit_receivers import AUDITED_MODELS
from apps.group_credit.models import (
    GCProduct,
    GCRider,
    GCRiderRate,
    GCSchemeType,
    GCSubProduct,
)
from apps.users.models import User

API_ROOT = "/api/v1/gc"

PARAMETER_LIST_PATHS = [
    "parameters/scheme-types",
    "parameters/scheme-rates",
    "parameters/scheme-statuses",
    "parameters/member-statuses",
    "parameters/renewal-statuses",
    "parameters/health-questions",
    "parameters/health-questionnaires",
    "parameters/lookup-values",
    "parameters/sub-products",
    "parameters/products",
    "parameters/riders",
    "parameters/rider-rates",
    "parameters/medical/codes",
    "parameters/medical/limits",
    "parameters/medical/decisions",
    "parameters/medical/habits",
    "parameters/medical/histories",
    "parameters/medical/facilities",
    "parameters/medical/practitioners",
    "parameters/claims/types",
    "parameters/claims/reasons",
    "parameters/claims/statuses",
    "parameters/claims/discharge-types",
    "parameters/claims/correspondent-types",
    "options/scheme-types",
    "options/products",
    "options/questionnaires",
    "options/claim-types",
]


def make_user(username, email):
    return User.objects.create_user(
        username=username,
        email=email,
        password="Strong-pass-123!",
        is_staff=False,
        is_superuser=False,
        is_active=True,
        is_approved=True,
    )


class GCParameterIntegrationTests(TestCase):
    """Prompt 6 scope 1 — Scheme Type -> Product -> Rider chain is queryable."""

    def test_scheme_product_rider_chain_links_are_queryable(self):
        scheme_type = GCSchemeType.objects.create(
            code="P6_BANK_LOAN",
            name="Bank Loan",
            partner_type_restriction="BANK",
        )
        sub_product = GCSubProduct.objects.create(
            code="P6_GROUP_CREDIT_LIFE", name="Group Credit Life"
        )
        product = GCProduct.objects.create(
            code="P6_CREDIT_LIFE_A",
            name="Credit Life Plan A",
            scheme_type_ref=scheme_type,
            sub_product=sub_product,
            insurance_class="CREDIT_LIFE",
            premium_basis="SINGLE",
            min_loan_term=6,
            max_loan_term=240,
        )
        rider = GCRider.objects.create(
            code="P6_ADB",
            name="Accidental Death Benefit",
            rider_category="ACCIDENTAL_DEATH",
            benefit_type="PERCENTAGE",
            requires_underwriting=True,
        )
        rate = GCRiderRate.objects.create(
            rider=rider,
            product_ref=product,
            rate_type="PERCENTAGE",
            rate_value="100.000000",
            currency="TZS",
            age_band_start=18,
            age_band_end=65,
            effective_date=date(2026, 1, 1),
            effective_from=date(2026, 1, 1),
            effective_to=None,
        )

        # Product is queryable from the scheme type and vice-versa.
        self.assertEqual(product.scheme_type_ref, scheme_type)
        self.assertEqual(product.sub_product, sub_product)
        self.assertEqual(
            GCSchemeType.objects.get(code="P6_BANK_LOAN").products.get(code="P6_CREDIT_LIFE_A"),
            product,
        )
        self.assertIn(product, scheme_type.products.all())

        # Rider is linked to the product via its rate, both directions.
        self.assertEqual(rate.product_ref, product)
        self.assertEqual(rate.rider, rider)
        self.assertEqual(product.rider_rates.get(rider=rider), rate)
        self.assertEqual(rider.rates.get(product_ref=product), rate)
        self.assertTrue(
            GCRiderRate.objects.filter(product_ref=product, rider=rider).exists()
        )
        self.assertIn(rider, {item.rider for item in product.rider_rates.all()})

        # Filters resolve the full chain from a single seed.
        fetched = GCSchemeType.objects.filter(products__rider_rates__rider=rider)
        self.assertEqual(fetched.count(), 1)
        self.assertEqual(fetched.first(), scheme_type)


class GCPermissionTests(TestCase):
    """Prompt 6 scope 2 — unauthorized users blocked; authorized users admitted."""

    def setUp(self):
        self.client = APIClient()

    def test_unauthorized_user_cannot_access_parameter_apis(self):
        for path in PARAMETER_LIST_PATHS:
            with self.subTest(path=path):
                response = self.client.get(f"{API_ROOT}/{path}/")
                self.assertEqual(response.status_code, 401)

    def test_authorized_user_can_access_all_parameter_apis(self):
        user = make_user("gc-param-consumer", "gc-param-consumer@example.com")
        self.client.force_authenticate(user)
        for path in PARAMETER_LIST_PATHS:
            with self.subTest(path=path):
                response = self.client.get(f"{API_ROOT}/{path}/")
                self.assertEqual(response.status_code, 200, response.data)


class GCAuditTests(TestCase):
    """Prompt 6 scope 3 — audit log captures actor, before, after and reason."""

    def tearDown(self):
        AuditContext.clear()

    def test_parameter_change_is_audited_with_actor_before_after_reason(self):
        user = make_user("gc-param-auditor", "gc-param-auditor@example.com")
        request = type(
            "Request",
            (),
            {
                "user": user,
                "path": f"{API_ROOT}/parameters/scheme-types/",
                "META": {},
                "request_id": "prompt6-audit-check",
            },
        )()
        label = GCSchemeType._meta.verbose_name.replace("_", " ")

        AuditContext.set_request(request)
        try:
            scheme_type = GCSchemeType.objects.create(
                code="P6_AUDIT", name="Before", partner_type_restriction="BANK"
            )
        finally:
            AuditContext.clear()

        create_log = AuditLog.objects.filter(
            action="CREATE", entity_id=scheme_type.pk
        ).latest("created_at")
        self.assertEqual(create_log.user, user)
        self.assertEqual(create_log.actor_type, AuditLog.ActorType.USER)
        self.assertEqual(create_log.source_channel, AuditLog.SourceChannel.API)
        self.assertEqual(create_log.reason, f"GC Parameters {label} created.")
        self.assertIsNone(create_log.before_state)
        self.assertEqual(create_log.after_state.get("code"), "P6_AUDIT")

        AuditContext.set_request(request)
        try:
            scheme_type.name = "After"
            scheme_type.save()
        finally:
            AuditContext.clear()

        update_log = AuditLog.objects.filter(
            action="UPDATE", entity_id=scheme_type.pk
        ).latest("created_at")
        self.assertEqual(update_log.user, user)
        self.assertEqual(update_log.actor_type, AuditLog.ActorType.USER)
        self.assertIn("name", update_log.changed_fields)
        self.assertEqual(update_log.before_state.get("name"), "Before")
        self.assertEqual(update_log.after_state.get("name"), "After")
        self.assertEqual(update_log.reason, f"GC Parameters {label} updated.")

    def test_audit_suppression_suppresses_parameter_audit_rows(self):
        from apps.group_credit.audit_receivers import audit_suppressed

        before_count = AuditLog.objects.filter(
            model_name="gcschemetype", action="CREATE"
        ).count()
        with audit_suppressed():
            scheme_type = GCSchemeType.objects.create(
                code="P6_SUPPRESSED", name="Suppressed"
            )
        self.assertEqual(
            AuditLog.objects.filter(
                model_name="gcschemetype",
                action="CREATE",
                object_id=str(scheme_type.pk),
            ).count(),
            0,
        )
        self.assertEqual(
            AuditLog.objects.filter(model_name="gcschemetype", action="CREATE").count(),
            before_count,
        )


class GCModelAuditFieldCoverageTests(TestCase):
    """Prompt 6 scope 4 — every GC parameter model carries the four audit columns."""

    def test_every_audited_parameter_model_has_the_four_audit_fields(self):
        required = {"created_at", "updated_at", "created_by", "updated_by"}
        self.assertEqual(len(AUDITED_MODELS), 24)
        for model in AUDITED_MODELS:
            with self.subTest(model=model.__name__):
                fields = {field.name for field in model._meta.concrete_fields}
                self.assertTrue(
                    required <= fields,
                    f"{model.__name__} is missing {sorted(required - fields)}",
                )
