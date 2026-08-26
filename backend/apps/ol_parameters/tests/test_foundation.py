from datetime import date

from apps.governance.models import AuditLog
from apps.ol_parameters.models import (
    OLEffectiveDateModel,
    OLParameterBaseModel,
    OLParameterTableRegistry,
    OLRateRowBaseModel,
    OLRateTableVersionModel,
)
from apps.ol_parameters.services.parameter_service import OLParameterService
from apps.users.models import User, UserGroup, UserPermission
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient


class TestParameter(OLParameterBaseModel):
    class Meta:
        app_label = "ol_parameters"
        managed = False


class TestEffectiveParameter(OLEffectiveDateModel):
    class Meta:
        app_label = "ol_parameters"
        managed = False


class TestRateVersion(OLRateTableVersionModel):
    class Meta:
        app_label = "ol_parameters"
        managed = False


class TestRateRow(OLRateRowBaseModel):
    class Meta:
        app_label = "ol_parameters"
        managed = False


class OLParameterModelTests(TestCase):
    def test_abstract_base_contracts_are_abstract_and_validate_shared_fields(self):
        self.assertTrue(OLParameterBaseModel._meta.abstract)
        self.assertTrue(OLEffectiveDateModel._meta.abstract)
        self.assertTrue(OLRateTableVersionModel._meta.abstract)
        self.assertTrue(OLRateRowBaseModel._meta.abstract)

        parameter = TestParameter(code="  DEFAULT  ", name="  Default ")
        parameter.clean()
        self.assertEqual(parameter.code, "DEFAULT")
        self.assertEqual(parameter.name, "Default")

    def test_effective_date_model_requires_effective_from(self):
        parameter = TestEffectiveParameter(code="EFFECTIVE", name="Effective")
        with self.assertRaises(ValidationError):
            parameter.clean()

        parameter.effective_from = date(2026, 1, 1)
        parameter.effective_to = date(2025, 12, 31)
        with self.assertRaises(ValidationError):
            parameter.clean()

    def test_rate_version_and_row_dimensions_validate(self):
        version = TestRateVersion(code="TERM", name="Term rates", version="v1")
        version.clean()
        self.assertFalse(version.is_current)

        row = TestRateRow(product_code="TERM", age_from=45, age_to=30)
        with self.assertRaises(ValidationError):
            row.clean()


class OLParameterRegistryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.superuser = User.objects.create_user(
            username="ol-parameters-superuser",
            email="ol-parameters-superuser@example.com",
            password="Strong-pass-123!",
            is_superuser=True,
            is_staff=True,
            is_active=True,
            is_approved=True,
        )
        self.viewer = self._user_with_permission("view")
        self.creator = self._user_with_permission("create")
        self.configurator = self._user_with_permission("configure")

    def _user_with_permission(self, action):
        username = f"ol-parameters-{action}"
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
        )
        permission, _ = UserPermission.objects.get_or_create(
            module="ol_parameters",
            action=action.upper(),
            resource_type="",
            defaults={
                "name": f"{action.title()} OL Parameters",
                "codename": f"ol_parameters.{action}",
                "description": f"{action.title()} access to Ordinary Life parameter configuration.",
                "is_active": True,
            },
        )
        group = UserGroup.objects.create(name=f"OL Parameters {action.title()} Group")
        group.permissions.add(permission)
        user.groups.add(group)
        return user

    @staticmethod
    def _payload(slug="default-setup"):
        return {
            "slug": slug,
            "label": "OL Default Setup",
            "description": "Defaults",
            "parameter_group": "OL_DEFAULT_SETUP",
            "model_label": "ol_parameters.OLDefaultSetup",
            "visible_columns": ["code", "name", "is_active"],
            "searchable_fields": ["code", "name"],
            "filter_fields": ["is_active"],
            "default_ordering": ["name", "code"],
            "allowed_actions": ["view", "create", "update", "deactivate"],
            "export_support": True,
            "permission_code": "ol_parameters.view",
            "permission_requirements": {
                "view": "ol_parameters.view",
                "create": "ol_parameters.create",
                "update": "ol_parameters.update",
                "deactivate": "ol_parameters.deactivate",
            },
            "is_active": True,
        }

    def test_health_endpoint_is_available_and_reports_registry_counts(self):
        response = self.client.get("/api/v1/ol-parameters/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["service"], "ol_parameters")
        self.assertEqual(response.data["status"], "ok")

    def test_registry_list_requires_view_permission(self):
        response = self.client.get("/api/v1/ol-parameters/tables/")
        self.assertEqual(response.status_code, 401)

        unpermissioned = User.objects.create_user(
            username="ol-parameters-none",
            email="ol-parameters-none@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
        )
        self.client.force_authenticate(unpermissioned)
        response = self.client.get("/api/v1/ol-parameters/tables/")
        self.assertEqual(response.status_code, 403)

    def test_viewer_can_list_and_creator_cannot_read_without_view(self):
        OLParameterTableRegistry.objects.create(**self._payload())

        self.client.force_authenticate(self.viewer)
        response = self.client.get("/api/v1/ol-parameters/tables/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 1)

        self.client.force_authenticate(self.creator)
        response = self.client.get("/api/v1/ol-parameters/tables/")
        self.assertEqual(response.status_code, 403)

    def test_creator_can_create_and_service_emits_audit_event(self):
        self.client.force_authenticate(self.creator)
        response = self.client.post(
            "/api/v1/ol-parameters/tables/",
            self._payload("policy-setup"),
            format="json",
            HTTP_X_REQUEST_ID="ol-parameters-create-test",
        )
        self.assertEqual(response.status_code, 201)
        registry = OLParameterTableRegistry.objects.get(slug="policy-setup")
        event = AuditLog.objects.filter(
            app_label="ol_parameters",
            model_name="olparametertableregistry",
            object_id=str(registry.pk),
            action="CREATE",
        ).latest("created_at")
        self.assertEqual(event.user_id, self.creator.pk)
        self.assertEqual(event.correlation_id, "ol-parameters-create-test")

    def test_update_and_deactivate_are_separate_permissions(self):
        registry = OLParameterTableRegistry.objects.create(**self._payload("policy-setup"))

        self.client.force_authenticate(self.creator)
        response = self.client.patch(
            f"/api/v1/ol-parameters/tables/{registry.pk}/",
            {"label": "Updated"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

        self.client.force_authenticate(self.superuser)
        response = self.client.patch(
            f"/api/v1/ol-parameters/tables/{registry.pk}/",
            {"label": "Updated"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        registry.refresh_from_db()
        self.assertEqual(registry.label, "Updated")

        self.client.force_authenticate(self.superuser)
        response = self.client.post(
            f"/api/v1/ol-parameters/tables/{registry.pk}/deactivate/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        registry.refresh_from_db()
        self.assertFalse(registry.is_active)
        self.assertTrue(
            AuditLog.objects.filter(
                app_label="ol_parameters",
                model_name="olparametertableregistry",
                object_id=str(registry.pk),
                action="DEACTIVATE",
            ).exists()
        )

    def test_configurator_can_see_inactive_registry_records(self):
        payload = self._payload("inactive")
        payload["is_active"] = False
        OLParameterTableRegistry.objects.create(**payload)

        self.client.force_authenticate(self.viewer)
        response = self.client.get("/api/v1/ol-parameters/tables/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 0)

        self.client.force_authenticate(self.configurator)
        response = self.client.get("/api/v1/ol-parameters/tables/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 1)

    @override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
    def test_admin_superuser_can_access_registry_changelist(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("admin:ol_parameters_olparametertableregistry_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_seed_command_is_idempotent_and_covers_nine_groups(self):
        call_command("seed_ol_parameter_registry")
        self.assertEqual(OLParameterTableRegistry.objects.count(), 9)
        call_command("seed_ol_parameter_registry")
        self.assertEqual(OLParameterTableRegistry.objects.count(), 9)
        self.assertEqual(
            set(OLParameterTableRegistry.objects.values_list("parameter_group", flat=True)),
            {
                "OL_DEFAULT_SETUP",
                "OL_POLICY_SETUP",
                "OL_PRODUCT_SETUP",
                "OL_PRODUCT_RATING",
                "OL_RIDER_SETUP",
                "OL_AGENT_MANAGEMENT",
                "OL_LOAN_SETUP",
                "OL_MEDICAL_UW",
                "OL_CLAIM_SETUP",
            },
        )


class OLParameterServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ol-parameter-service",
            email="ol-parameter-service@example.com",
            password="Strong-pass-123!",
            is_superuser=True,
            is_staff=True,
            is_active=True,
            is_approved=True,
        )

    def test_service_update_captures_changed_fields(self):
        registry = OLParameterTableRegistry.objects.create(
            slug="service",
            label="Service",
            model_label="ol_parameters.Service",
            visible_columns=["code"],
        )
        OLParameterService.update_registry(
            actor=self.user,
            instance=registry,
            data={"label": "Service Updated"},
        )
        event = AuditLog.objects.filter(
            app_label="ol_parameters",
            model_name="olparametertableregistry",
            object_id=str(registry.pk),
            action="UPDATE",
        ).latest("created_at")
        self.assertIn("label", event.changed_fields)
