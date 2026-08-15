from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.partners.models import PartnerType, PartnerTypeDocumentRequirement
from .models import ChoiceList, ChoiceOption, ParameterGroup, SystemParameter
from .serializers import SystemParameterWriteSerializer


class PartnerOnboardingConfigurationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="configuration-test",
            email="configuration-test@example.com",
            password="test-password",
        )
        self.client.force_authenticate(self.user)

        self.partner_group = ParameterGroup.objects.create(
            code="PARTNER",
            name="Partner Parameters",
            description="Partner onboarding configuration",
            sort_order=10,
        )
        self.validation_group = ParameterGroup.objects.create(
            parent=self.partner_group,
            code="PARTNER_VALIDATION",
            name="Field Validation",
            description="Partner onboarding validation rules",
            sort_order=10,
        )
        SystemParameter.objects.create(
            group=self.validation_group,
            code="INDIVIDUAL_REQUIRED_FIELDS",
            name="Individual Required Fields",
            value_type="JSON",
            json_value=["first_name", "surname", "mobile_number"],
        )
        self.choice_list = ChoiceList.objects.create(
            group=self.partner_group,
            code="ONBOARDING_TEST_CHOICES",
            name="Onboarding Test Choices",
        )
        ChoiceOption.objects.create(
            choice_list=self.choice_list,
            code="ONE",
            label="One",
            is_default=True,
        )
        self.partner_type = PartnerType.objects.create(
            code="CONFIG_TEST",
            name="Configuration Test Partner",
            description="Partner type used to verify the projection contract",
        )
        PartnerTypeDocumentRequirement.objects.create(
            partner_type=self.partner_type,
            code="TEST_DOCUMENT",
            description="A configured test document",
            is_required=True,
            is_mandatory=True,
        )

    def test_projection_returns_organized_parameter_and_requirement_catalog(self):
        response = self.client.get("/api/v1/system-parameters/configuration/partner-onboarding/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["version"], "partner-onboarding.v1")

        partner_group = next(item for item in payload["groups"] if item["code"] == "PARTNER")
        validation_group = next(item for item in partner_group["children"] if item["code"] == "PARTNER_VALIDATION")
        self.assertEqual(validation_group["parameters"][0]["code"], "INDIVIDUAL_REQUIRED_FIELDS")

        choice_list = next(item for item in payload["choiceLists"] if item["code"] == "ONBOARDING_TEST_CHOICES")
        self.assertEqual(choice_list["options"][0]["code"], "ONE")

        partner_type = next(item for item in payload["partnerTypes"] if item["code"] == "CONFIG_TEST")
        self.assertEqual(partner_type["documents"][0]["code"], "TEST_DOCUMENT")
        self.assertTrue(partner_type["documents"][0]["isMandatory"])

    def test_projection_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/system-parameters/configuration/partner-onboarding/")
        self.assertEqual(response.status_code, 401)


class TypedSystemParameterWriteTests(TestCase):
    def setUp(self):
        self.group = ParameterGroup.objects.create(
            code="PARTNER_VALIDATION",
            name="Partner Validation",
        )
        self.parameter = SystemParameter.objects.create(
            group=self.group,
            code="MINIMUM_AGE",
            name="Minimum Age",
            value_type="INTEGER",
            integer_value=18,
            string_value="stale-value",
        )

    def test_typed_value_write_coerces_and_clears_stale_storage(self):
        serializer = SystemParameterWriteSerializer(
            instance=self.parameter,
            data={"value_type": "INTEGER", "value": "21"},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()

        self.assertEqual(updated.integer_value, 21)
        self.assertIsNone(updated.string_value)
        self.assertIsNone(updated.float_value)
        self.assertEqual(updated.value, 21)
