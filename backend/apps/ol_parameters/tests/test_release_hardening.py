from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from apps.ol_parameters.models import OLParameterTableRegistry
from apps.users.models import PermissionGroup, User, UserGroup, UserPermission


class OLParameterReleaseHardeningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_ol_parameters_release", verbosity=0)
        cls.viewer = User.objects.create_user(
            username="ol-release-viewer",
            email="ol-release-viewer@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
        )
        viewer_group = UserGroup.objects.get(code="OL_PARAMETER_VIEWER")
        cls.viewer.groups.add(viewer_group)

    def setUp(self):
        self.client = APIClient()

    def test_release_seed_is_idempotent_and_covers_exactly_nine_groups(self):
        expected_groups = {
            "OL_DEFAULT_SETUP",
            "OL_POLICY_SETUP",
            "OL_PRODUCT_SETUP",
            "OL_PRODUCT_RATING",
            "OL_RIDER_SETUP",
            "OL_AGENT_MANAGEMENT",
            "OL_LOAN_SETUP",
            "OL_MEDICAL_UW",
            "OL_CLAIM_SETUP",
        }
        canonical_slugs = {
            "ol-default-setup",
            "ol-policy-setup",
            "ol-product-setup",
            "ol-product-rating",
            "ol-rider-setup",
            "ol-agent-management",
            "ol-loan-setup",
            "ol-medical-underwriting",
            "ol-claim-setup",
        }
        before = {
            row.slug: row.updated_at
            for row in OLParameterTableRegistry.objects.filter(slug__in=canonical_slugs)
        }
        call_command("seed_ol_parameters_release", verbosity=0)
        canonical_rows = OLParameterTableRegistry.objects.filter(slug__in=canonical_slugs)
        self.assertEqual(canonical_rows.count(), 9)
        self.assertSetEqual(
            set(canonical_rows.values_list("parameter_group", flat=True)),
            expected_groups,
        )
        self.assertEqual(
            set(before),
            set(canonical_rows.values_list("slug", flat=True)),
        )
        self.assertEqual(
            PermissionGroup.objects.get(module_code="OL_PARAMETERS").permissions.count(),
            5,
        )

    def test_seeded_viewer_can_read_representative_endpoint_from_each_group(self):
        self.client.force_authenticate(self.viewer)
        endpoints = [
            "default-system-parameters",
            "policy-statuses",
            "products",
            "premium-rate-tables",
            "rider-setups",
            "agent-commission-setups",
            "loan-system-setups",
            "medical-codes",
            "claim-types",
        ]
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(f"/api/v1/ol-parameters/{endpoint}/")
                self.assertEqual(response.status_code, 200)
                self.assertIn("data", response.data)

    def test_seeded_viewer_cannot_mutate_and_administrator_has_full_lifecycle_permissions(self):
        viewer_permission = UserPermission.objects.get(codename="ol_parameters.view")
        self.assertEqual(viewer_permission.action, UserPermission.Action.VIEW)
        viewer_group = UserGroup.objects.get(code="OL_PARAMETER_VIEWER")
        self.assertSetEqual(
            set(viewer_group.permissions.values_list("codename", flat=True)),
            {"ol_parameters.view"},
        )
        administrator = UserGroup.objects.get(code="OL_PARAMETER_ADMINISTRATOR")
        self.assertSetEqual(
            set(administrator.permissions.values_list("codename", flat=True)),
            {
                "ol_parameters.view",
                "ol_parameters.create",
                "ol_parameters.update",
                "ol_parameters.deactivate",
                "ol_parameters.configure",
            },
        )

        self.client.force_authenticate(self.viewer)
        response = self.client.post(
            "/api/v1/ol-parameters/claim-types/",
            {"code": "REL-CLAIM", "name": "Release Claim"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_readiness_exposes_all_nine_group_sections(self):
        response = self.client.get("/api/v1/ol-parameters/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")
        for section in (
            "default_setup",
            "policy_setup",
            "product_setup",
            "product_rating_part1",
            "product_rating_part2",
            "rider_setup",
            "agent_management",
            "loan_setup",
            "medical_underwriting",
            "claim_setup",
        ):
            with self.subTest(section=section):
                self.assertIn(section, response.data)
        self.assertGreaterEqual(response.data["registry"]["active"], 9)

    def test_canonical_permissions_are_unique_and_active(self):
        self.assertEqual(
            UserPermission.objects.filter(module="ol_parameters", is_active=True).count(),
            5,
        )
        self.assertEqual(
            UserPermission.objects.filter(module="ol_parameters", is_active=True)
            .values_list("codename", flat=True)
            .distinct()
            .count(),
            5,
        )
        self.assertTrue(
            PermissionGroup.objects.filter(
                module_code="OL_PARAMETERS",
                name="OL Parameters Configuration",
            ).exists()
        )

    def test_registry_metadata_points_to_existing_models_and_has_table_contracts(self):
        canonical_slugs = {
            "ol-default-setup",
            "ol-policy-setup",
            "ol-product-setup",
            "ol-product-rating",
            "ol-rider-setup",
            "ol-agent-management",
            "ol-loan-setup",
            "ol-medical-underwriting",
            "ol-claim-setup",
        }
        rows = OLParameterTableRegistry.objects.filter(
            is_active=True,
            slug__in=canonical_slugs,
        )
        self.assertEqual(rows.count(), 9)
        for row in rows:
            with self.subTest(slug=row.slug):
                self.assertTrue(row.visible_columns)
                self.assertTrue(row.searchable_fields)
                self.assertTrue(row.filter_fields)
                self.assertEqual(row.permission_code, "ol_parameters.view")
                self.assertEqual(
                    set(row.allowed_actions),
                    {"view", "create", "update", "deactivate", "configure"},
                )
                self.assertTrue(row.export_support)
                self.assertEqual(row.permission_requirements["view"], "ol_parameters.view")
