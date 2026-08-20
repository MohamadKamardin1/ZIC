import inspect

from django.core.management import call_command
from django.test import TestCase
from rest_framework import serializers
from rest_framework.test import APIClient

from apps.ol_parameters.models import OLPlanType, OLProduct
from apps.ol_quotations.models import OLQuotation
from apps.ol_quotations.serializers import OLQuotationSerializer
from apps.partner_onboarding.models import Location
from apps.partners.models import Partner
from apps.users.models import User


OPTION_ENTITIES = [
    "identity-types",
    "locations",
    "agents",
    "products",
    "plan-types",
    "payment-frequencies",
    "quote-bases",
    "premium-factors",
    "member-relations",
    "cover-types",
    "payment-modes",
    "investment-funds",
    "investment-fund-types",
    "riders",
    "benefit-types",
    "currencies",
]


class OLOptionRegistryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_zanzibar_ol_demo", verbosity=0)
        cls.admin = User.objects.create_superuser(
            username="ol-options-admin",
            email="ol-options-admin@example.com",
            password="Strong-pass-123!",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def get_options(self, entity, **params):
        response = self.client.get(f"/api/v1/ol/options/{entity}/", params)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["success"])
        return response.data["data"]

    def test_every_wizard_entity_returns_seeded_labeled_options(self):
        for entity in OPTION_ENTITIES:
            with self.subTest(entity=entity):
                data = self.get_options(entity, page_size=200)
                self.assertGreater(data["count"], 0)
                self.assertEqual(data["items"], data["results"])
                for option in data["items"]:
                    self.assertIn("value", option)
                    self.assertTrue(option["label"])
                    self.assertIn("meta", option)
                    self.assertNotEqual(option["label"], option["value"])

    def test_search_and_pagination_work_for_large_entities(self):
        for entity in ("products", "agents", "riders"):
            with self.subTest(entity=entity):
                first_page = self.get_options(entity, q="", page=1, page_size=1)
                self.assertGreater(first_page["count"], 0)
                self.assertLessEqual(len(first_page["items"]), 1)
                self.assertEqual(first_page["pagination"]["page_size"], 1)

                query = first_page["items"][0]["label"].split(" — ")[0]
                search_page = self.get_options(entity, q=query, page_size=1)
                self.assertGreater(search_page["count"], 0)
                self.assertLessEqual(len(search_page["items"]), 1)
                self.assertTrue(any(query.casefold() in item["label"].casefold() for item in search_page["items"]))

    def test_inactive_catalog_records_are_excluded(self):
        inactive = OLPlanType.objects.create(
            code="INACTIVE-OPTION-TEST",
            name="Inactive Option Test",
            plan_category="TERM",
            is_active=False,
        )
        data = self.get_options("plan-types", q=inactive.code, page_size=200)
        self.assertEqual(data["count"], 0)

    def test_quotation_detail_contains_fk_display_labels(self):
        product = OLProduct.objects.first()
        self.assertIsNotNone(product)
        partner = Partner.objects.filter(is_active=True, status="ACTIVE").first()
        location = Location.objects.filter(is_active=True).select_related("branch").first()
        self.assertIsNotNone(partner)
        self.assertIsNotNone(location)

        quotation = OLQuotation.objects.create(
            quote_number="OPT-LABEL-0001",
            quote_name="Option label quotation",
            product=product,
            partner=partner,
            linked_partner=partner,
            agent=self.admin,
            agent_partner=partner,
            location_master=location,
            location=location.name,
            currency="TZS",
        )
        payload = OLQuotationSerializer(quotation).data

        for field in (
            "partner_display",
            "product_display",
            "linked_partner_display",
            "agent_display",
            "location_display",
            "currency_display",
        ):
            self.assertIn(field, payload)
            self.assertTrue(payload[field], field)

        self.assertIn(location.code, payload["location_display"])
        self.assertIn(product.code, payload["product_display"])
        self.assertIn(partner.partner_number, payload["partner_display"])
        self.assertEqual(payload["currency_display"], "TZS — Tanzanian Shilling")
        self.assertNotEqual(payload["product_display"], str(product.pk))
        self.assertNotEqual(payload["partner_display"], str(partner.pk))

    def test_model_serializers_expose_display_field_for_each_serialized_fk(self):
        modules = []
        for module_name in ("apps.ol_quotations.serializers", "apps.ol_parameters.serializers"):
            module = __import__(module_name, fromlist=["serializers"])
            modules.append(module)

        for module in modules:
            for _, serializer_class in inspect.getmembers(module, inspect.isclass):
                if not issubclass(serializer_class, serializers.ModelSerializer):
                    continue
                meta = getattr(serializer_class, "Meta", None)
                model = getattr(meta, "model", None)
                if model is None:
                    continue
                serializer = serializer_class()
                serialized_fields = serializer.fields
                for model_field in model._meta.get_fields():
                    if not getattr(model_field, "many_to_one", False) or not getattr(model_field, "concrete", False):
                        continue
                    if model_field.name in serialized_fields:
                        self.assertIn(
                            f"{model_field.name}_display",
                            serialized_fields,
                            f"{module.__name__}.{serializer_class.__name__} exposes {model_field.name} without a display field",
                        )


class OLOptionQuickCreateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_zanzibar_ol_demo", verbosity=0)
        cls.admin = User.objects.create_superuser(
            username="ol-quick-create-admin",
            email="ol-quick-create-admin@example.com",
            password="Strong-pass-123!",
        )
        cls.regular_user = User.objects.create_user(
            username="ol-quick-create-user",
            email="ol-quick-create-user@example.com",
            password="Strong-pass-123!",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_schema_endpoint_returns_minimal_fields_for_registered_entities(self):
        expected = {
            "identity-types": {"code", "name"},
            "locations": {"code", "name", "branch"},
            "agents": {"partner_type", "legal_name", "national_id", "phone", "email"},
            "products": {"code", "name", "plan_type", "insurance_class", "investment_linked"},
            "plan-types": {"code", "name", "plan_category"},
            "payment-frequencies": {"code", "name"},
            "quote-bases": {"code", "name"},
            "premium-factors": {"code", "name"},
            "member-relations": {"code", "name"},
            "cover-types": {"code", "name"},
            "payment-modes": {"code", "name"},
            "investment-funds": {"code", "name", "fund_type"},
            "investment-fund-types": {"code", "name", "risk_profile"},
            "riders": {"code", "name", "rider_category", "benefit_type"},
            "benefit-types": {"code", "name"},
            "currencies": {"code", "name"},
        }
        for entity, required_fields in expected.items():
            with self.subTest(entity=entity):
                response = self.client.get(f"/api/v1/ol/options/{entity}/quick-create-schema/")
                self.assertEqual(response.status_code, 200, response.data)
                self.assertTrue(response.data["success"])
                schema = response.data["data"]
                actual = {field["name"] for field in schema["fields"]}
                self.assertTrue(required_fields.issubset(actual))
                self.assertEqual(schema["entity"], entity)
                for field in schema["fields"]:
                    self.assertIn("type", field)
                    self.assertIn("required", field)
                    self.assertIn("choices", field)
                    self.assertIn("default", field)

    def test_quick_create_returns_selectable_labeled_object_and_audit_record(self):
        response = self.client.post(
            "/api/v1/ol/options/identity-types/quick-create/",
            {"code": "QC-NIDA", "name": "Quick Create National ID"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data["success"])
        option = response.data["data"]["option"]
        self.assertEqual(option["value"], "QC-NIDA")
        self.assertEqual(option["label"], "Quick Create National ID")
        self.assertEqual(response.data["data"]["value"], option["value"])
        self.assertEqual(response.data["data"]["label"], option["label"])

        from apps.governance.models import AuditLog

        audit = AuditLog.objects.filter(object_id=option["id"]).latest("created_at")
        self.assertEqual(audit.source_channel, AuditLog.SourceChannel.QUICK_CREATE)
        self.assertEqual(audit.reason, "Created from OL quotation wizard")

    def test_quick_create_denies_user_without_required_permission(self):
        self.client.force_authenticate(self.regular_user)
        response = self.client.post(
            "/api/v1/ol/options/identity-types/quick-create/",
            {"code": "QC-DENIED", "name": "Denied Quick Create"},
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(response.data["success"])

    def test_quick_create_rejects_duplicate_code_or_name(self):
        first = self.client.post(
            "/api/v1/ol/options/payment-modes/quick-create/",
            {"code": "QC-CASH", "name": "Quick Cash"},
            format="json",
        )
        self.assertEqual(first.status_code, 201, first.data)
        duplicate_code = self.client.post(
            "/api/v1/ol/options/payment-modes/quick-create/",
            {"code": "QC-CASH", "name": "Another Cash"},
            format="json",
        )
        self.assertEqual(duplicate_code.status_code, 400, duplicate_code.data)
        self.assertIn("code", duplicate_code.data["errors"])

        duplicate_name = self.client.post(
            "/api/v1/ol/options/payment-modes/quick-create/",
            {"code": "QC-CASH-2", "name": "Quick Cash"},
            format="json",
        )
        self.assertEqual(duplicate_name.status_code, 400, duplicate_name.data)
        self.assertIn("name", duplicate_name.data["errors"])

    def test_location_schema_contains_active_branch_choices(self):
        response = self.client.get("/api/v1/ol/options/locations/quick-create-schema/")
        self.assertEqual(response.status_code, 200, response.data)
        branch_field = next(field for field in response.data["data"]["fields"] if field["name"] == "branch")
        self.assertTrue(branch_field["choices"])
        self.assertIn("—", branch_field["choices"][0]["label"])

    def test_agent_quick_create_creates_partner_assignment_and_selectable_label(self):
        response = self.client.post(
            "/api/v1/ol/options/agents/quick-create/",
            {
                "partner_type": "AGENT",
                "legal_name": "Quick Zanzibar Agency",
                "phone": "+255777990001",
                "email": "quick-zanzibar-agency@example.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        option = response.data["data"]["option"]
        partner = Partner.objects.get(pk=option["value"])
        self.assertEqual(partner.partner_type, "AGENT")
        self.assertTrue(partner.type_assignments.filter(partner_type__code="AGENT", status="ACTIVE").exists())
        self.assertIn(partner.partner_number, option["label"])
        self.assertTrue(option["meta"]["completion_required"])
