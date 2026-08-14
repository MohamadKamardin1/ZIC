from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.governance.models import AuditLog
from apps.ordinary_life.models import OLApplication, OLProduct
from apps.ordinary_life.services.application_service import OrdinaryLifeApplicationService
from apps.partners.models import Partner
from apps.users.models import User, UserGroup, UserPermission


class OrdinaryLifeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(
            username="phase8-api-staff",
            email="phase8-api-staff@example.com",
            password="Strong-pass-123!",
            user_type="STAFF",
            is_active=True,
            is_approved=True,
            is_staff=True,
        )
        self.partner = self._partner("P8-0001", "Asha", "Juma", "asha.p8@example.com", "255710000801")
        self.outsider = self._partner("P8-0002", "Hassan", "Ali", "hassan.p8@example.com", "255710000802")
        self.product = OLProduct.objects.create(
            code="OL_PHASE8_API",
            name="Phase 8 API Product",
            business_area="ORDINARY_LIFE",
            min_age=18,
            max_age=65,
            term_length_years=10,
            is_active=True,
        )

    @staticmethod
    def _partner(number, first_name, surname, email, mobile):
        return Partner.objects.create(
            partner_number=number,
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            first_name=first_name,
            surname=surname,
            date_of_birth=date(1990, 6, 15),
            identification_type="ZAN_ID",
            identification_number=number,
            email=email,
            mobile_number=mobile,
            status="ACTIVE",
            is_active=True,
        )

    def _application(self, partner=None):
        target = partner or self.partner
        return OrdinaryLifeApplicationService.create_application(
            partner=target,
            policyholder=target,
            life_assured=target,
            payer=target,
            declarations={"consent": True},
            actor=self.staff,
        )

    def _permissioned_user(self, partner_id=None):
        user = User.objects.create_user(
            username=f"phase8-reader-{User.objects.count()}",
            email=f"phase8-reader-{User.objects.count()}@example.com",
            password="Strong-pass-123!",
            user_type="PORTAL_USER",
            partner_id=partner_id,
            is_active=True,
            is_approved=True,
        )
        group = UserGroup.objects.create(name=f"Phase 8 Reader {User.objects.count()}")
        permission = UserPermission.objects.create(
            name="Ordinary Life Read",
            codename=f"ordinary_life.read.{User.objects.count()}",
            module="ordinary_life",
            action="READ",
            resource_type="ordinary_life",
        )
        group.permissions.add(permission)
        user.groups.add(group)
        return user

    def test_product_list_returns_standard_envelope_and_searches_entities(self):
        self.client.force_authenticate(self.staff)

        response = self.client.get(
            "/api/v1/ordinary-life/core/products/",
            {"search": "PHASE8"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["status_code"], 200)
        self.assertEqual(response.data["data"][0]["code"], "OL_PHASE8_API")
        self.assertIn("meta", response.data)

    def test_unauthenticated_and_unpermissioned_users_are_rejected(self):
        unauthenticated = self.client.get("/api/v1/ordinary-life/core/products/")
        self.assertEqual(unauthenticated.status_code, 401)

        unpermissioned = User.objects.create_user(
            username="phase8-no-permission",
            email="phase8-no-permission@example.com",
            password="Strong-pass-123!",
            user_type="PORTAL_USER",
            is_active=True,
            is_approved=True,
        )
        self.client.force_authenticate(unpermissioned)
        forbidden = self.client.get("/api/v1/ordinary-life/core/products/")
        self.assertEqual(forbidden.status_code, 403)

    def test_partner_scope_limits_read_results_to_visible_partner(self):
        visible_application = self._application(self.partner)
        hidden_application = self._application(self.outsider)
        user = self._permissioned_user(self.partner.pk)
        self.client.force_authenticate(user)

        response = self.client.get("/api/v1/ordinary-life/core/applications/")

        self.assertEqual(response.status_code, 200)
        identifiers = {item["id"] for item in response.data["data"]}
        self.assertIn(str(visible_application.pk), identifiers)
        self.assertNotIn(str(hidden_application.pk), identifiers)

    def test_application_create_and_submit_use_service_owned_actions(self):
        self.client.force_authenticate(self.staff)
        payload = {
            "partner": str(self.partner.pk),
            "policyholder": str(self.partner.pk),
            "life_assured": str(self.partner.pk),
            "payer": str(self.partner.pk),
            "declarations": {"consent": True},
        }

        created = self.client.post("/api/v1/ordinary-life/core/applications/", payload, format="json")

        self.assertEqual(created.status_code, 201)
        self.assertTrue(created.data["success"])
        application_id = created.data["data"]["id"]
        self.assertEqual(created.data["data"]["status"], "DRAFT")

        submitted = self.client.post(
            f"/api/v1/ordinary-life/core/applications/{application_id}/submit/",
            {"reason": "API intake validation completed"},
            format="json",
        )

        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.data["data"]["status"], "SUBMITTED")
        self.assertEqual(OLApplication.objects.get(pk=application_id).status, "SUBMITTED")

    def test_audit_history_filters_are_normalized_and_read_only(self):
        self.client.force_authenticate(self.staff)
        event = AuditLog.objects.create(
            action="UPDATE",
            app_label="ordinary_life",
            model_name="olproduct",
            object_id=str(self.product.pk),
            object_repr=str(self.product),
            before_state={"name": "Old"},
            after_state={"name": "New"},
            changed_fields={"name": {"before": "Old", "after": "New"}},
            reason="API audit test",
            source_channel="API",
            user=self.staff,
        )

        response = self.client.get(
            "/api/v1/ordinary-life/core/audit-history/",
            {"model_name": "OLPRODUCT", "object_id": str(self.product.pk), "action": "update"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["id"], str(event.pk))
        self.assertEqual(response.data["data"][0]["model_name"], "olproduct")
        self.assertEqual(
            self.client.post("/api/v1/ordinary-life/core/audit-history/", {}, format="json").status_code,
            405,
        )
