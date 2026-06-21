import logging

from rest_framework import serializers

from apps.partners.models import (
    Partner,
    PartnerContact,
    PartnerBankAccount,
)

logger = logging.getLogger(__name__)


class PartnerContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerContact
        fields = [
            "id", "partner", "contact_type", "first_name", "last_name",
            "email", "phone", "mobile", "designation", "is_primary",
            "notes", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "partner", "created_at", "updated_at"]


class PartnerBankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerBankAccount
        fields = [
            "id", "partner", "bank_name", "branch_name",
            "account_name", "account_number", "swift_code", "iban",
            "currency", "is_primary", "is_verified", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "partner", "is_verified", "created_at", "updated_at",
        ]


class PartnerListSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()

    class Meta:
        model = Partner
        fields = [
            "id", "partner_number", "partner_type", "display_name",
            "email", "mobile_number", "status",
            "political_risk", "aml_risk", "created_at",
        ]
        read_only_fields = fields


class PartnerDetailSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()
    contacts = PartnerContactSerializer(many=True, read_only=True)
    bank_accounts = PartnerBankAccountSerializer(many=True, read_only=True)

    class Meta:
        model = Partner
        fields = [
            "id", "partner_number", "partner_type", "status",
            "display_name",
            # Individual
            "identification_type", "identification_number",
            "title", "first_name", "other_name", "surname",
            "gender", "date_of_birth", "marital_status",
            "occupation", "nationality",
            # Corporate
            "company_name", "tin_number", "incorporation_date",
            "industry", "contact_person", "contact_person_phone",
            "contact_person_email", "physical_address", "postal_address",
            # Common
            "email", "telephone_number", "mobile_number",
            "political_risk", "aml_risk",
            # Audit
            "created_from_application",
            "activated_at", "deactivated_at", "deactivation_reason",
            "created_at", "updated_at",
            # Nested
            "contacts", "bank_accounts",
        ]
        read_only_fields = fields


class PartnerUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = [
            "telephone_number", "mobile_number",
            "physical_address", "postal_address",
            "occupation", "contact_person",
            "contact_person_phone", "contact_person_email",
        ]
