"""Seed partner type configuration parameters under PARTNER group."""

from django.db import migrations


PARTNER_TYPES_METADATA = {
    "CLIENT": {
        "name": "Client",
        "description": "Standard client/end customer",
        "registration_types": ["INDIVIDUAL", "CORPORATE"],
        "sort_order": 10,
    },
    "INTERMEDIARY": {
        "name": "Intermediary",
        "description": "Insurance intermediary or agent",
        "registration_types": ["INDIVIDUAL", "CORPORATE"],
        "sort_order": 20,
    },
    "SERVICE_PROVIDER": {
        "name": "Service Provider",
        "description": "Third-party service provider (corporate only)",
        "registration_types": ["CORPORATE"],
        "sort_order": 30,
    },
    "BROKER": {
        "name": "Broker",
        "description": "Insurance broker",
        "registration_types": ["INDIVIDUAL", "CORPORATE"],
        "sort_order": 40,
    },
    "MEDICAL_PRACTITIONER": {
        "name": "Medical Practitioner",
        "description": "Medical professional on the provider panel",
        "registration_types": ["INDIVIDUAL"],
        "sort_order": 50,
    },
}

PARTNER_TYPE_DOCUMENTS = {
    "CLIENT": {
        "INDIVIDUAL": {
            "required": ["NID", "PASSPORT"],
            "optional": ["DRIVING_LICENSE", "VOTER_ID", "RESIDENT_PERMIT"],
        },
        "CORPORATE": {
            "required": ["INCORPORATION_CERT", "TIN_CERTIFICATE", "MEMORANDUM"],
            "optional": ["BOARD_RESOLUTION"],
        },
    },
    "INTERMEDIARY": {
        "INDIVIDUAL": {
            "required": ["NID", "PASSPORT"],
            "optional": ["DRIVING_LICENSE"],
        },
        "CORPORATE": {
            "required": ["INCORPORATION_CERT", "TIN_CERTIFICATE", "MEMORANDUM", "BOARD_RESOLUTION"],
            "optional": [],
        },
    },
    "SERVICE_PROVIDER": {
        "CORPORATE": {
            "required": ["INCORPORATION_CERT", "TIN_CERTIFICATE", "MEMORANDUM"],
            "optional": ["BOARD_RESOLUTION"],
        },
    },
    "BROKER": {
        "INDIVIDUAL": {
            "required": ["NID", "PASSPORT", "TIN_CERTIFICATE"],
            "optional": ["DRIVING_LICENSE", "VOTER_ID"],
        },
        "CORPORATE": {
            "required": ["INCORPORATION_CERT", "TIN_CERTIFICATE", "MEMORANDUM", "BOARD_RESOLUTION"],
            "optional": [],
        },
    },
    "MEDICAL_PRACTITIONER": {
        "INDIVIDUAL": {
            "required": ["NID", "PASSPORT"],
            "optional": ["DRIVING_LICENSE"],
        },
    },
}

PARTNER_TYPE_FORM_FIELDS = {
    "CLIENT": {
        "INDIVIDUAL": [
            "identification_type", "identification_number", "title",
            "first_name", "other_name", "surname", "gender",
            "date_of_birth", "marital_status", "occupation",
            "nationality", "email", "telephone_number", "mobile_number",
            "physical_address", "postal_address",
        ],
        "CORPORATE": [
            "company_name", "tin_number", "incorporation_date",
            "industry", "email", "telephone_number", "mobile_number",
            "contact_person", "contact_person_phone",
            "contact_person_email", "physical_address", "postal_address",
        ],
    },
    "INTERMEDIARY": {
        "INDIVIDUAL": [
            "identification_type", "identification_number", "title",
            "first_name", "other_name", "surname", "gender",
            "date_of_birth", "marital_status", "occupation",
            "nationality", "email", "telephone_number", "mobile_number",
            "physical_address", "postal_address",
            "license_number", "regulatory_body",
        ],
        "CORPORATE": [
            "company_name", "tin_number", "incorporation_date",
            "industry", "email", "telephone_number", "mobile_number",
            "contact_person", "contact_person_phone",
            "contact_person_email", "physical_address", "postal_address",
            "license_number", "regulatory_body", "commission_structure",
        ],
    },
    "SERVICE_PROVIDER": {
        "INDIVIDUAL": [
            "identification_type", "identification_number", "title",
            "first_name", "other_name", "surname", "gender",
            "date_of_birth", "marital_status", "occupation",
            "nationality", "email", "telephone_number", "mobile_number",
            "physical_address", "postal_address",
        ],
        "CORPORATE": [
            "company_name", "tin_number", "incorporation_date",
            "industry", "email", "telephone_number", "mobile_number",
            "contact_person", "contact_person_phone",
            "contact_person_email", "physical_address", "postal_address",
            "service_category", "contract_start_date",
            "contract_end_date", "insurance_certificate_ref",
        ],
    },
    "BROKER": {
        "INDIVIDUAL": [
            "identification_type", "identification_number", "title",
            "first_name", "other_name", "surname", "gender",
            "date_of_birth", "marital_status", "occupation",
            "nationality", "email", "telephone_number", "mobile_number",
            "physical_address", "postal_address",
            "license_number", "license_expiry_date",
            "regulatory_body", "commission_structure",
        ],
        "CORPORATE": [
            "company_name", "tin_number", "incorporation_date",
            "industry", "email", "telephone_number", "mobile_number",
            "contact_person", "contact_person_phone",
            "contact_person_email", "physical_address", "postal_address",
            "license_number", "license_expiry_date",
            "regulatory_body", "commission_structure",
            "e_and_o_insurance_ref",
        ],
    },
    "MEDICAL_PRACTITIONER": {
        "INDIVIDUAL": [
            "identification_type", "identification_number", "title",
            "first_name", "other_name", "surname", "gender",
            "date_of_birth", "marital_status", "nationality",
            "email", "telephone_number", "mobile_number",
            "physical_address", "postal_address",
            "professional_license_number", "specialization",
            "qualifications", "practice_name", "practice_address",
        ],
    },
}

PARTNER_TYPE_CONTACTS = {
    "CLIENT": {
        "allowed_contact_types": ["PRIMARY", "SECONDARY", "BILLING"],
        "required_fields": ["first_name", "last_name", "email", "phone"],
        "optional_fields": ["mobile", "designation", "notes"],
        "min_contacts": 1,
        "max_contacts": 3,
    },
    "INTERMEDIARY": {
        "allowed_contact_types": ["PRIMARY", "SECONDARY", "BILLING"],
        "required_fields": ["first_name", "last_name", "email", "phone", "designation"],
        "optional_fields": ["mobile", "notes"],
        "min_contacts": 1,
        "max_contacts": 3,
    },
    "SERVICE_PROVIDER": {
        "allowed_contact_types": ["PRIMARY", "TECHNICAL", "BILLING"],
        "required_fields": ["first_name", "last_name", "email", "phone", "designation"],
        "optional_fields": ["mobile", "notes"],
        "min_contacts": 2,
        "max_contacts": 5,
    },
    "BROKER": {
        "allowed_contact_types": ["PRIMARY", "SECONDARY", "BILLING"],
        "required_fields": ["first_name", "last_name", "email", "phone", "designation"],
        "optional_fields": ["mobile", "notes"],
        "min_contacts": 1,
        "max_contacts": 3,
    },
    "MEDICAL_PRACTITIONER": {
        "allowed_contact_types": ["PRIMARY", "TECHNICAL"],
        "required_fields": ["first_name", "last_name", "email", "phone"],
        "optional_fields": ["mobile", "designation", "notes"],
        "min_contacts": 1,
        "max_contacts": 2,
    },
}

PARTNER_TYPE_BANKS = {
    "CLIENT": {
        "required_fields": ["bank_name", "account_name", "account_number"],
        "optional_fields": ["branch_name", "swift_code", "iban"],
        "min_accounts": 0,
        "max_accounts": 3,
    },
    "INTERMEDIARY": {
        "required_fields": ["bank_name", "account_name", "account_number", "swift_code"],
        "optional_fields": ["branch_name", "iban"],
        "min_accounts": 1,
        "max_accounts": 3,
    },
    "SERVICE_PROVIDER": {
        "required_fields": ["bank_name", "account_name", "account_number"],
        "optional_fields": ["branch_name", "swift_code", "iban"],
        "min_accounts": 0,
        "max_accounts": 3,
    },
    "BROKER": {
        "required_fields": ["bank_name", "account_name", "account_number", "swift_code"],
        "optional_fields": ["branch_name", "iban"],
        "min_accounts": 1,
        "max_accounts": 3,
    },
    "MEDICAL_PRACTITIONER": {
        "required_fields": ["bank_name", "account_name", "account_number"],
        "optional_fields": ["branch_name", "swift_code", "iban"],
        "min_accounts": 0,
        "max_accounts": 2,
    },
}


def seed_partner_type_config(apps, schema_editor):
    ParameterGroup = apps.get_model("system_parameters", "ParameterGroup")
    SystemParameter = apps.get_model("system_parameters", "SystemParameter")

    partner = ParameterGroup.objects.get(code="PARTNER")

    pt_config = ParameterGroup.objects.create(
        parent=partner,
        code="PARTNER_TYPE_CONFIG",
        name="Partner Type Configuration",
        description="Per-partner-type rules for documents, form fields, contacts, and bank accounts",
        sort_order=80,
    )

    SystemParameter.objects.create(
        group=pt_config, code="PARTNER_TYPES_METADATA",
        name="Partner Types Metadata",
        value_type="JSON", json_value=PARTNER_TYPES_METADATA,
        description="Defines each partner type code, display name, description, allowed registration types, and sort order",
        sort_order=10,
    )
    SystemParameter.objects.create(
        group=pt_config, code="DOCUMENTS_CONFIG",
        name="Document Requirements per Partner Type",
        value_type="JSON", json_value=PARTNER_TYPE_DOCUMENTS,
        description="Required and optional document types per partner type and registration type (INDIVIDUAL/CORPORATE)",
        sort_order=20,
    )
    SystemParameter.objects.create(
        group=pt_config, code="FORM_FIELDS_CONFIG",
        name="Form Fields per Partner Type",
        value_type="JSON", json_value=PARTNER_TYPE_FORM_FIELDS,
        description="Which attribution form fields are collected per partner type and registration type",
        sort_order=30,
    )
    SystemParameter.objects.create(
        group=pt_config, code="CONTACTS_CONFIG",
        name="Contact Configuration per Partner Type",
        value_type="JSON", json_value=PARTNER_TYPE_CONTACTS,
        description="Allowed contact types, required/optional contact fields, min/max contacts per partner type",
        sort_order=40,
    )
    SystemParameter.objects.create(
        group=pt_config, code="BANKS_CONFIG",
        name="Bank Configuration per Partner Type",
        value_type="JSON", json_value=PARTNER_TYPE_BANKS,
        description="Required/optional bank fields and min/max bank accounts per partner type",
        sort_order=50,
    )


def reverse_seed(apps, schema_editor):
    ParameterGroup = apps.get_model("system_parameters", "ParameterGroup")
    SystemParameter = apps.get_model("system_parameters", "SystemParameter")
    SystemParameter.objects.filter(group__code="PARTNER_TYPE_CONFIG").delete()
    try:
        pg = ParameterGroup.objects.get(code="PARTNER_TYPE_CONFIG")
        pg.delete()
    except ParameterGroup.DoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("system_parameters", "0003_seed_password_policy"),
    ]
    operations = [
        migrations.RunPython(seed_partner_type_config, reverse_seed),
    ]
