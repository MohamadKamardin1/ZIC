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
