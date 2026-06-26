"""Seed Zanzibar life insurance commission partner types and DB configuration tables."""

from django.db import migrations

logger = __import__("logging").getLogger(__name__)

NEW_PARTNER_TYPES = [
    {
        "code": "AGENT",
        "name": "Insurance Agent",
        "description": "Individual insurance agent licensed by TIRA to sell life insurance and earn commission",
        "registration_types": ["INDIVIDUAL"],
        "sort_order": 25,
    },
    {
        "code": "AGENCY",
        "name": "Insurance Agency",
        "description": "Corporate insurance agency managing multiple agents, earning override commissions",
        "registration_types": ["CORPORATE"],
        "sort_order": 35,
    },
    {
        "code": "BANCASSURANCE",
        "name": "Bancassurance Partner",
        "description": "Bank or financial institution distributing life insurance products under bancassurance model",
        "registration_types": ["CORPORATE"],
        "sort_order": 45,
    },
    {
        "code": "REINSURANCE_BROKER",
        "name": "Reinsurance Broker",
        "description": "Intermediary arranging reinsurance coverage for life insurance portfolios",
        "registration_types": ["INDIVIDUAL", "CORPORATE"],
        "sort_order": 55,
    },
    {
        "code": "TAKAFUL_OPERATOR",
        "name": "Takaful Operator",
        "description": "Islamic insurance operator providing Shariah-compliant life insurance (family takaful)",
        "registration_types": ["CORPORATE"],
        "sort_order": 65,
    },
    {
        "code": "MICROINSURANCE_AGENT",
        "name": "Microinsurance Agent",
        "description": "Agent specialized in microinsurance products for low-income communities in Zanzibar",
        "registration_types": ["INDIVIDUAL", "CORPORATE"],
        "sort_order": 75,
    },
]

# =========================================================================
# Partner Type Field Configuration
# =========================================================================

FIELD_CONFIGS = {
    "AGENT": [
        {
            "field_code": "license_number",
            "field_name": "TIRA License Number",
            "field_type": "TEXT",
            "is_required": True,
            "validation_rules": {"max_length": 50, "pattern": "^[A-Z0-9-/]+$"},
            "display_order": 1,
        },
        {
            "field_code": "regulatory_body",
            "field_name": "Regulatory Body",
            "field_type": "DROPDOWN",
            "is_required": True,
            "validation_rules": {
                "options": ["TIRA", "ZIC", "ZANZIBAR_INSURANCE"],
                "default": "TIRA",
            },
            "display_order": 2,
        },
        {
            "field_code": "license_expiry_date",
            "field_name": "License Expiry Date",
            "field_type": "DATE",
            "is_required": True,
            "display_order": 3,
        },
        {
            "field_code": "commission_rate",
            "field_name": "Commission Rate",
            "field_type": "PERCENTAGE",
            "is_required": True,
            "validation_rules": {"min": 0.0, "max": 0.30, "decimal_places": 2},
            "display_order": 4,
        },
        {
            "field_code": "commission_structure",
            "field_name": "Commission Structure",
            "field_type": "DROPDOWN",
            "is_required": True,
            "validation_rules": {
                "options": ["LEVEL", "HEIRARCHICAL", "OVERRIDE", "HYBRID"],
                "default": "LEVEL",
            },
            "display_order": 5,
        },
        {
            "field_code": "tax_id",
            "field_name": "Tax Identification Number (TIN)",
            "field_type": "TEXT",
            "is_required": True,
            "validation_rules": {
                "max_length": 20,
                "pattern": "^[0-9]{9}[A-Z]$",
            },
            "display_order": 6,
        },
        {
            "field_code": "territory",
            "field_name": "Sales Territory",
            "field_type": "TEXT",
            "is_required": False,
            "display_order": 7,
        },
        {
            "field_code": "years_of_experience",
            "field_name": "Years of Experience",
            "field_type": "NUMBER",
            "is_required": False,
            "validation_rules": {"min": 0, "max": 70},
            "display_order": 8,
        },
        {
            "field_code": "payment_method",
            "field_name": "Preferred Payment Method",
            "field_type": "DROPDOWN",
            "is_required": True,
            "validation_rules": {
                "options": ["BANK_TRANSFER", "CHEQUE", "MOBILE_MONEY"],
                "default": "BANK_TRANSFER",
            },
            "display_order": 9,
        },
        {
            "field_code": "supervisory_agent",
            "field_name": "Supervisory Agent",
            "field_type": "TEXT",
            "is_required": False,
            "display_order": 10,
        },
    ],
    "AGENCY": [
        {
            "field_code": "license_number",
            "field_name": "Agency License Number",
            "field_type": "TEXT",
            "is_required": True,
            "validation_rules": {"max_length": 50, "pattern": "^[A-Z0-9-/]+$"},
            "display_order": 1,
        },
        {
            "field_code": "regulatory_body",
            "field_name": "Regulatory Body",
            "field_type": "DROPDOWN",
            "is_required": True,
            "validation_rules": {
                "options": ["TIRA", "ZIC", "ZANZIBAR_INSURANCE"],
                "default": "TIRA",
            },
            "display_order": 2,
        },
        {
            "field_code": "license_expiry_date",
            "field_name": "License Expiry Date",
            "field_type": "DATE",
            "is_required": True,
            "display_order": 3,
        },
        {
            "field_code": "commission_rate",
            "field_name": "Override Commission Rate",
            "field_type": "PERCENTAGE",
            "is_required": True,
            "validation_rules": {"min": 0.0, "max": 0.30, "decimal_places": 2},
            "display_order": 4,
        },
        {
            "field_code": "commission_structure",
            "field_name": "Commission Structure",
            "field_type": "DROPDOWN",
            "is_required": True,
            "validation_rules": {
                "options": ["TIED", "INDEPENDENT", "HYBRID"],
                "default": "TIED",
            },
            "display_order": 5,
        },
        {
            "field_code": "corporate_registration_number",
            "field_name": "Corporate Registration Number (BRELA)",
            "field_type": "TEXT",
            "is_required": True,
            "validation_rules": {"max_length": 50, "pattern": "^[0-9-]+$"},
            "display_order": 6,
        },
        {
            "field_code": "tax_id",
            "field_name": "Tax Identification Number (TIN)",
            "field_type": "TEXT",
            "is_required": True,
            "validation_rules": {
                "max_length": 20,
                "pattern": "^[0-9]{9}[A-Z]$",
            },
            "display_order": 7,
        },
        {
            "field_code": "number_of_agents",
            "field_name": "Number of Agents",
            "field_type": "NUMBER",
            "is_required": False,
            "validation_rules": {"min": 1},
            "display_order": 8,
        },
        {
            "field_code": "contract_start_date",
            "field_name": "Agency Contract Start Date",
            "field_type": "DATE",
            "is_required": True,
            "display_order": 9,
        },
        {
            "field_code": "contract_end_date",
            "field_name": "Agency Contract End Date",
            "field_type": "DATE",
            "is_required": False,
            "display_order": 10,
        },
    ],
    "BANCASSURANCE": [
        {
            "field_code": "bancassurance_license_number",
            "field_name": "Bancassurance License Number",
            "field_type": "TEXT",
            "is_required": True,
            "validation_rules": {"max_length": 50},
            "display_order": 1,
        },
        {
            "field_code": "regulatory_body",
            "field_name": "Regulatory Body",
            "field_type": "DROPDOWN",
            "is_required": True,
            "validation_rules": {
                "options": ["TIRA", "BOT", "ZANZIBAR_INSURANCE"],
                "default": "TIRA",
            },
            "display_order": 2,
        },
        {
            "field_code": "license_expiry_date",
            "field_name": "License Expiry Date",
            "field_type": "DATE",
            "is_required": True,
            "display_order": 3,
        },
        {
            "field_code": "commission_rate",
            "field_name": "Bancassurance Commission Rate",
            "field_type": "PERCENTAGE",
            "is_required": True,
            "validation_rules": {"min": 0.0, "max": 0.25, "decimal_places": 2},
            "display_order": 4,
        },
        {
            "field_code": "partnership_agreement_ref",
            "field_name": "Partnership Agreement Reference",
            "field_type": "TEXT",
            "is_required": True,
            "display_order": 5,
        },
        {
            "field_code": "partnership_start_date",
            "field_name": "Partnership Start Date",
            "field_type": "DATE",
            "is_required": True,
            "display_order": 6,
        },
        {
            "field_code": "partnership_end_date",
            "field_name": "Partnership End Date",
            "field_type": "DATE",
            "is_required": False,
            "display_order": 7,
        },
        {
            "field_code": "branch_network",
            "field_name": "Branch Network Locations",
            "field_type": "MULTI_SELECT",
            "is_required": False,
            "display_order": 8,
        },
        {
            "field_code": "products_offered",
            "field_name": "Products Offered",
            "field_type": "MULTI_SELECT",
            "is_required": True,
            "validation_rules": {
                "options": [
                    "INDIVIDUAL_LIFE",
                    "GROUP_LIFE",
                    "CREDIT_LIFE",
                    "EDUCATION_ENDOWMENT",
                    "TERM_LIFE",
                    "WHOLE_LIFE",
                    "RETIREMENT_ANNUITY",
                ],
            },
            "display_order": 9,
        },
    ],
    "REINSURANCE_BROKER": [
        {
            "field_code": "license_number",
            "field_name": "Reinsurance Broker License Number",
            "field_type": "TEXT",
            "is_required": True,
            "validation_rules": {"max_length": 50},
            "display_order": 1,
        },
        {
            "field_code": "regulatory_body",
            "field_name": "Regulatory Body",
            "field_type": "DROPDOWN",
            "is_required": True,
            "validation_rules": {
                "options": ["TIRA", "ZIC"],
                "default": "TIRA",
            },
            "display_order": 2,
        },
        {
            "field_code": "license_expiry_date",
            "field_name": "License Expiry Date",
            "field_type": "DATE",
            "is_required": True,
            "display_order": 3,
        },
        {
            "field_code": "brokerage_rate",
            "field_name": "Brokerage Rate",
            "field_type": "PERCENTAGE",
            "is_required": True,
            "validation_rules": {"min": 0.0, "max": 0.15, "decimal_places": 2},
            "display_order": 4,
        },
        {
            "field_code": "corporate_registration_number",
            "field_name": "Corporate Registration Number",
            "field_type": "TEXT",
            "is_required": True,
            "display_order": 5,
        },
        {
            "field_code": "tax_id",
            "field_name": "Tax Identification Number (TIN)",
            "field_type": "TEXT",
            "is_required": True,
            "validation_rules": {
                "max_length": 20,
                "pattern": "^[0-9]{9}[A-Z]$",
            },
            "display_order": 6,
        },
        {
            "field_code": "professional_indemnity_ref",
            "field_name": "Professional Indemnity Insurance Reference",
            "field_type": "TEXT",
            "is_required": True,
            "display_order": 7,
        },
        {
            "field_code": "pi_expiry_date",
            "field_name": "Professional Indemnity Expiry Date",
            "field_type": "DATE",
            "is_required": True,
            "display_order": 8,
        },
        {
            "field_code": "reinsurer_credentials",
            "field_name": "Reinsurer Credentials / Panel",
            "field_type": "TEXT",
            "is_required": False,
            "display_order": 9,
        },
    ],
    "TAKAFUL_OPERATOR": [
        {
            "field_code": "takaful_license_number",
            "field_name": "Takaful License Number",
            "field_type": "TEXT",
            "is_required": True,
            "validation_rules": {"max_length": 50},
            "display_order": 1,
        },
        {
            "field_code": "regulatory_body",
            "field_name": "Regulatory Body",
            "field_type": "DROPDOWN",
            "is_required": True,
            "validation_rules": {
                "options": ["TIRA", "ZIC", "ZAKAT_AND_TRUST"],
                "default": "TIRA",
            },
            "display_order": 2,
        },
        {
            "field_code": "license_expiry_date",
            "field_name": "License Expiry Date",
            "field_type": "DATE",
            "is_required": True,
            "display_order": 3,
        },
        {
            "field_code": "takaful_commission_rate",
            "field_name": "Takaful Commission Rate (Wakalah Fee)",
            "field_type": "PERCENTAGE",
            "is_required": True,
            "validation_rules": {"min": 0.0, "max": 0.35, "decimal_places": 2},
            "display_order": 4,
        },
        {
            "field_code": "takaful_model",
            "field_name": "Takaful Model",
            "field_type": "DROPDOWN",
            "is_required": True,
            "validation_rules": {
                "options": [
                    "MUDHARABAH",
                    "WAKALAH",
                    "MUSHARAKAH",
                    "COMBINATION",
                    "WAQF",
                ],
                "default": "WAKALAH",
            },
            "display_order": 5,
        },
        {
            "field_code": "shariah_board_ref",
            "field_name": "Shariah Board Reference",
            "field_type": "TEXT",
            "is_required": True,
            "display_order": 6,
        },
        {
            "field_code": "corporate_registration_number",
            "field_name": "Corporate Registration Number",
            "field_type": "TEXT",
            "is_required": True,
            "display_order": 7,
        },
        {
            "field_code": "tax_id",
            "field_name": "Tax Identification Number (TIN)",
            "field_type": "TEXT",
            "is_required": True,
            "validation_rules": {
                "max_length": 20,
                "pattern": "^[0-9]{9}[A-Z]$",
            },
            "display_order": 8,
        },
    ],
    "MICROINSURANCE_AGENT": [
        {
            "field_code": "license_number",
            "field_name": "Microinsurance License Number",
            "field_type": "TEXT",
            "is_required": True,
            "validation_rules": {"max_length": 50},
            "display_order": 1,
        },
        {
            "field_code": "regulatory_body",
            "field_name": "Regulatory Body",
            "field_type": "DROPDOWN",
            "is_required": True,
            "validation_rules": {
                "options": ["TIRA", "ZIC"],
                "default": "TIRA",
            },
            "display_order": 2,
        },
        {
            "field_code": "commission_rate",
            "field_name": "Commission Rate",
            "field_type": "PERCENTAGE",
            "is_required": True,
            "validation_rules": {"min": 0.0, "max": 0.20, "decimal_places": 2},
            "display_order": 3,
        },
        {
            "field_code": "tax_id",
            "field_name": "Tax Identification Number (TIN)",
            "field_type": "TEXT",
            "is_required": True,
            "validation_rules": {
                "max_length": 20,
                "pattern": "^[0-9]{9}[A-Z]$",
            },
            "display_order": 4,
        },
        {
            "field_code": "territory",
            "field_name": "Service Territory / Shehia",
            "field_type": "TEXT",
            "is_required": True,
            "display_order": 5,
        },
        {
            "field_code": "community_organisation",
            "field_name": "Community Organisation Affiliation",
            "field_type": "TEXT",
            "is_required": False,
            "display_order": 6,
        },
        {
            "field_code": "payment_method",
            "field_name": "Preferred Payment Method",
            "field_type": "DROPDOWN",
            "is_required": True,
            "validation_rules": {
                "options": ["MOBILE_MONEY", "BANK_TRANSFER", "CASH"],
                "default": "MOBILE_MONEY",
            },
            "display_order": 7,
        },
    ],
    # Commission-specific field additions for existing types
    "INTERMEDIARY": [
        {
            "field_code": "commission_rate",
            "field_name": "Commission Rate",
            "field_type": "PERCENTAGE",
            "is_required": True,
            "validation_rules": {"min": 0.0, "max": 0.30, "decimal_places": 2},
            "display_order": 20,
        },
        {
            "field_code": "commission_structure",
            "field_name": "Commission Structure",
            "field_type": "DROPDOWN",
            "is_required": True,
            "validation_rules": {
                "options": ["LEVEL", "HEIRARCHICAL", "OVERRIDE"],
                "default": "LEVEL",
            },
            "display_order": 21,
        },
        {
            "field_code": "payment_method",
            "field_name": "Preferred Payment Method",
            "field_type": "DROPDOWN",
            "is_required": True,
            "validation_rules": {
                "options": ["BANK_TRANSFER", "CHEQUE", "MOBILE_MONEY"],
                "default": "BANK_TRANSFER",
            },
            "display_order": 22,
        },
    ],
    "BROKER": [
        {
            "field_code": "brokerage_rate",
            "field_name": "Brokerage Rate",
            "field_type": "PERCENTAGE",
            "is_required": True,
            "validation_rules": {"min": 0.0, "max": 0.30, "decimal_places": 2},
            "display_order": 20,
        },
        {
            "field_code": "payment_method",
            "field_name": "Preferred Payment Method",
            "field_type": "DROPDOWN",
            "is_required": True,
            "validation_rules": {
                "options": ["BANK_TRANSFER", "CHEQUE"],
                "default": "BANK_TRANSFER",
            },
            "display_order": 21,
        },
        {
            "field_code": "broker_commission_terms",
            "field_name": "Commission Payment Terms",
            "field_type": "DROPDOWN",
            "is_required": True,
            "validation_rules": {
                "options": [
                    "UPFRONT",
                    "INSTALMENT",
                    "DEFERRED",
                    "AS_EARNED",
                ],
                "default": "AS_EARNED",
            },
            "display_order": 22,
        },
    ],
    "SERVICE_PROVIDER": [
        {
            "field_code": "service_fee_rate",
            "field_name": "Service Fee Rate",
            "field_type": "PERCENTAGE",
            "is_required": False,
            "validation_rules": {"min": 0.0, "max": 1.0, "decimal_places": 2},
            "display_order": 20,
        },
        {
            "field_code": "payment_terms",
            "field_name": "Payment Terms",
            "field_type": "DROPDOWN",
            "is_required": True,
            "validation_rules": {
                "options": ["NET_15", "NET_30", "NET_45", "NET_60"],
                "default": "NET_30",
            },
            "display_order": 21,
        },
    ],
    "CLIENT": [],
    "MEDICAL_PRACTITIONER": [],
}

# =========================================================================
# Document Requirements per Partner Type
# =========================================================================

DOCUMENT_REQUIREMENTS = {
    "AGENT": [
        {"code": "TIRA_AGENT_LICENSE", "description": "TIRA Agent License Certificate", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 1},
        {"code": "COMMISSION_AGREEMENT", "description": "Commission Agreement / Agency Contract", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 2},
        {"code": "TAX_CLEARANCE_CERT", "description": "Tax Clearance Certificate (TRA)", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 3},
        {"code": "PROFESSIONAL_INDEMNITY", "description": "Professional Indemnity Insurance", "is_required": True, "is_mandatory": False, "allow_multiple_uploads": False, "sort_order": 4},
        {"code": "NID", "description": "National ID / Passport", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 5},
        {"code": "BANK_DETAILS_FORM", "description": "Bank Details Form for Commission Payments", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 6},
        {"code": "COP_CERTIFICATE", "description": "Certificate of Proficiency (COP) in Insurance", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 7},
    ],
    "AGENCY": [
        {"code": "AGENCY_LICENSE", "description": "TIRA Agency License Certificate", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 1},
        {"code": "INCORPORATION_CERT", "description": "Certificate of Incorporation (BRELA)", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 2},
        {"code": "TIN_CERTIFICATE", "description": "Tax Identification Number Certificate", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 3},
        {"code": "MEMORANDUM", "description": "Memorandum & Articles of Association", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 4},
        {"code": "COMMISSION_AGREEMENT", "description": "Agency Commission Agreement", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 5},
        {"code": "TAX_CLEARANCE_CERT", "description": "Tax Clearance Certificate", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 6},
        {"code": "BOARD_RESOLUTION", "description": "Board Resolution for Insurance Agency Business", "is_required": True, "is_mandatory": False, "allow_multiple_uploads": False, "sort_order": 7},
        {"code": "BANK_DETAILS_FORM", "description": "Bank Details Form", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 8},
    ],
    "BANCASSURANCE": [
        {"code": "BANCASSURANCE_LICENSE", "description": "Bancassurance License from TIRA", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 1},
        {"code": "BANKING_LICENSE", "description": "Banking License / BOT Certificate", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 2},
        {"code": "PARTNERSHIP_AGREEMENT", "description": "Bancassurance Partnership Agreement", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 3},
        {"code": "INCORPORATION_CERT", "description": "Certificate of Incorporation", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 4},
        {"code": "TIN_CERTIFICATE", "description": "Tax Identification Number Certificate", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 5},
        {"code": "TAX_CLEARANCE_CERT", "description": "Tax Clearance Certificate", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 6},
        {"code": "BOARD_RESOLUTION", "description": "Board Resolution for Bancassurance", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 7},
    ],
    "REINSURANCE_BROKER": [
        {"code": "REINSURANCE_BROKER_LICENSE", "description": "Reinsurance Broker License from TIRA", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 1},
        {"code": "INCORPORATION_CERT", "description": "Certificate of Incorporation", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 2},
        {"code": "TIN_CERTIFICATE", "description": "Tax Identification Number Certificate", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 3},
        {"code": "MEMORANDUM", "description": "Memorandum & Articles of Association", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 4},
        {"code": "PROFESSIONAL_INDEMNITY", "description": "Professional Indemnity Insurance (min TZS 10M)", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 5},
        {"code": "TAX_CLEARANCE_CERT", "description": "Tax Clearance Certificate", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 6},
        {"code": "BANK_GUARANTEE", "description": "Bank Guarantee (TZS 3M or Government Bond)", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 7},
        {"code": "BANK_DETAILS_FORM", "description": "Bank Details Form", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 8},
    ],
    "TAKAFUL_OPERATOR": [
        {"code": "TAKAFUL_LICENSE", "description": "Takaful License from TIRA", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 1},
        {"code": "SHARIAH_BOARD_APPROVAL", "description": "Shariah Board Approval / Fatwa", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 2},
        {"code": "INCORPORATION_CERT", "description": "Certificate of Incorporation", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 3},
        {"code": "TIN_CERTIFICATE", "description": "Tax Identification Number Certificate", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 4},
        {"code": "MEMORANDUM", "description": "Memorandum & Articles of Association", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 5},
        {"code": "TAKAFUL_FUND_SEPARATION", "description": "Takaful Fund Separation Audited Statement", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 6},
        {"code": "TAX_CLEARANCE_CERT", "description": "Tax Clearance Certificate", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 7},
        {"code": "BANK_DETAILS_FORM", "description": "Bank Details Form", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 8},
    ],
    "MICROINSURANCE_AGENT": [
        {"code": "MICROINSURANCE_LICENSE", "description": "Microinsurance Agent License", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 1},
        {"code": "COMMISSION_AGREEMENT", "description": "Microinsurance Commission Agreement", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 2},
        {"code": "NID", "description": "National ID / Passport", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 3},
        {"code": "COMMUNITY_LETTER", "description": "Community / Shehia Introduction Letter", "is_required": True, "is_mandatory": False, "allow_multiple_uploads": False, "sort_order": 4},
        {"code": "BANK_DETAILS_FORM", "description": "Bank / Mobile Money Details Form", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 5},
    ],
}

EXISTING_TYPE_DOCUMENTS = {
    "INTERMEDIARY": [
        {"code": "TIRA_INTERMEDIARY_LICENSE", "description": "TIRA Intermediary License", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 5},
        {"code": "COMMISSION_AGREEMENT", "description": "Commission Agreement", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 6},
    ],
    "BROKER": [
        {"code": "COMMISSION_AGREEMENT", "description": "Broker Commission Agreement", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 6},
        {"code": "PROFESSIONAL_INDEMNITY", "description": "Professional Indemnity Insurance (min TZS 10M)", "is_required": True, "is_mandatory": True, "allow_multiple_uploads": False, "sort_order": 7},
    ],
}

# =========================================================================
# Contact Requirements per Partner Type
# =========================================================================

CONTACT_REQUIREMENTS = {
    "AGENT": [
        {"contact_type": "PRIMARY", "is_required": True, "multiple_allowed": False, "display_order": 1},
        {"contact_type": "SECONDARY", "is_required": False, "multiple_allowed": False, "display_order": 2},
    ],
    "AGENCY": [
        {"contact_type": "PRIMARY", "is_required": True, "multiple_allowed": False, "display_order": 1},
        {"contact_type": "TECHNICAL", "is_required": True, "multiple_allowed": False, "display_order": 2},
        {"contact_type": "BILLING", "is_required": True, "multiple_allowed": False, "display_order": 3},
        {"contact_type": "COMPLIANCE", "is_required": True, "multiple_allowed": False, "display_order": 4},
    ],
    "BANCASSURANCE": [
        {"contact_type": "PRIMARY", "is_required": True, "multiple_allowed": False, "display_order": 1},
        {"contact_type": "TECHNICAL", "is_required": True, "multiple_allowed": False, "display_order": 2},
        {"contact_type": "BILLING", "is_required": True, "multiple_allowed": False, "display_order": 3},
        {"contact_type": "LEGAL", "is_required": False, "multiple_allowed": False, "display_order": 4},
    ],
    "REINSURANCE_BROKER": [
        {"contact_type": "PRIMARY", "is_required": True, "multiple_allowed": False, "display_order": 1},
        {"contact_type": "TECHNICAL", "is_required": True, "multiple_allowed": False, "display_order": 2},
        {"contact_type": "BILLING", "is_required": True, "multiple_allowed": False, "display_order": 3},
    ],
    "TAKAFUL_OPERATOR": [
        {"contact_type": "PRIMARY", "is_required": True, "multiple_allowed": False, "display_order": 1},
        {"contact_type": "SHARIAH", "is_required": True, "multiple_allowed": False, "display_order": 2},
        {"contact_type": "BILLING", "is_required": True, "multiple_allowed": False, "display_order": 3},
    ],
    "MICROINSURANCE_AGENT": [
        {"contact_type": "PRIMARY", "is_required": True, "multiple_allowed": False, "display_order": 1},
        {"contact_type": "SECONDARY", "is_required": False, "multiple_allowed": False, "display_order": 2},
    ],
}

UPDATED_CONTACT_REQUIREMENTS = {
    "INTERMEDIARY": [
        {"contact_type": "BILLING", "is_required": True, "multiple_allowed": False, "display_order": 3},
    ],
    "BROKER": [
        {"contact_type": "BILLING", "is_required": True, "multiple_allowed": False, "display_order": 3},
    ],
}

# =========================================================================
# Bank Requirements per Partner Type
# =========================================================================

BANK_REQUIREMENTS = {
    "AGENT": [
        {"bank_type": "COMMISSION", "is_required": True, "multiple_allowed": False, "validation_rules": {"require_swift": False}, "display_order": 1},
    ],
    "AGENCY": [
        {"bank_type": "OPERATIONS", "is_required": True, "multiple_allowed": False, "validation_rules": {"require_swift": True}, "display_order": 1},
        {"bank_type": "COMMISSION", "is_required": True, "multiple_allowed": False, "validation_rules": {"require_swift": False}, "display_order": 2},
    ],
    "BANCASSURANCE": [
        {"bank_type": "OPERATIONS", "is_required": True, "multiple_allowed": False, "validation_rules": {"require_swift": True}, "display_order": 1},
        {"bank_type": "COMMISSION", "is_required": True, "multiple_allowed": False, "validation_rules": {"require_swift": True}, "display_order": 2},
    ],
    "REINSURANCE_BROKER": [
        {"bank_type": "OPERATIONS", "is_required": True, "multiple_allowed": False, "validation_rules": {"require_swift": True}, "display_order": 1},
        {"bank_type": "TRUST", "is_required": True, "multiple_allowed": False, "validation_rules": {"require_swift": True}, "display_order": 2},
    ],
    "TAKAFUL_OPERATOR": [
        {"bank_type": "OPERATIONS", "is_required": True, "multiple_allowed": False, "validation_rules": {"require_swift": True}, "display_order": 1},
        {"bank_type": "TAKAFUL_FUND", "is_required": True, "multiple_allowed": True, "validation_rules": {"require_swift": True, "require_segregation": True}, "display_order": 2},
    ],
    "MICROINSURANCE_AGENT": [
        {"bank_type": "COMMISSION", "is_required": False, "multiple_allowed": False, "validation_rules": {"require_swift": False}, "display_order": 1},
    ],
}

# =========================================================================
# Merge into system parameter JSON configs
# =========================================================================

PARTNER_TYPES_METADATA_UPDATE = {
    "AGENT": {
        "name": "Insurance Agent",
        "description": "Individual insurance agent licensed by TIRA to sell life insurance and earn commission",
        "registration_types": ["INDIVIDUAL"],
        "sort_order": 25,
    },
    "AGENCY": {
        "name": "Insurance Agency",
        "description": "Corporate insurance agency managing multiple agents, earning override commissions",
        "registration_types": ["CORPORATE"],
        "sort_order": 35,
    },
    "BANCASSURANCE": {
        "name": "Bancassurance Partner",
        "description": "Bank or financial institution distributing life insurance products under bancassurance model",
        "registration_types": ["CORPORATE"],
        "sort_order": 45,
    },
    "REINSURANCE_BROKER": {
        "name": "Reinsurance Broker",
        "description": "Intermediary arranging reinsurance coverage for life insurance portfolios",
        "registration_types": ["INDIVIDUAL", "CORPORATE"],
        "sort_order": 55,
    },
    "TAKAFUL_OPERATOR": {
        "name": "Takaful Operator",
        "description": "Islamic insurance operator providing Shariah-compliant life insurance (family takaful)",
        "registration_types": ["CORPORATE"],
        "sort_order": 65,
    },
    "MICROINSURANCE_AGENT": {
        "name": "Microinsurance Agent",
        "description": "Agent specialized in microinsurance products for low-income communities in Zanzibar",
        "registration_types": ["INDIVIDUAL", "CORPORATE"],
        "sort_order": 75,
    },
}

DOCUMENTS_CONFIG_UPDATE = {
    "AGENT": {
        "INDIVIDUAL": {
            "required": [
                "TIRA_AGENT_LICENSE",
                "COMMISSION_AGREEMENT",
                "TAX_CLEARANCE_CERT",
                "NID",
                "BANK_DETAILS_FORM",
                "COP_CERTIFICATE",
            ],
            "optional": [
                "PROFESSIONAL_INDEMNITY",
            ],
        },
    },
    "AGENCY": {
        "CORPORATE": {
            "required": [
                "AGENCY_LICENSE",
                "INCORPORATION_CERT",
                "TIN_CERTIFICATE",
                "MEMORANDUM",
                "COMMISSION_AGREEMENT",
                "TAX_CLEARANCE_CERT",
                "BOARD_RESOLUTION",
                "BANK_DETAILS_FORM",
            ],
            "optional": [],
        },
    },
    "BANCASSURANCE": {
        "CORPORATE": {
            "required": [
                "BANCASSURANCE_LICENSE",
                "BANKING_LICENSE",
                "PARTNERSHIP_AGREEMENT",
                "INCORPORATION_CERT",
                "TIN_CERTIFICATE",
                "TAX_CLEARANCE_CERT",
                "BOARD_RESOLUTION",
            ],
            "optional": [],
        },
    },
    "REINSURANCE_BROKER": {
        "INDIVIDUAL": {
            "required": [
                "REINSURANCE_BROKER_LICENSE",
                "TIN_CERTIFICATE",
                "PROFESSIONAL_INDEMNITY",
                "TAX_CLEARANCE_CERT",
                "NID",
                "BANK_DETAILS_FORM",
            ],
            "optional": [],
        },
        "CORPORATE": {
            "required": [
                "REINSURANCE_BROKER_LICENSE",
                "INCORPORATION_CERT",
                "TIN_CERTIFICATE",
                "MEMORANDUM",
                "PROFESSIONAL_INDEMNITY",
                "TAX_CLEARANCE_CERT",
                "BANK_GUARANTEE",
                "BANK_DETAILS_FORM",
            ],
            "optional": [],
        },
    },
    "TAKAFUL_OPERATOR": {
        "CORPORATE": {
            "required": [
                "TAKAFUL_LICENSE",
                "SHARIAH_BOARD_APPROVAL",
                "INCORPORATION_CERT",
                "TIN_CERTIFICATE",
                "MEMORANDUM",
                "TAKAFUL_FUND_SEPARATION",
                "TAX_CLEARANCE_CERT",
                "BANK_DETAILS_FORM",
            ],
            "optional": [],
        },
    },
    "MICROINSURANCE_AGENT": {
        "INDIVIDUAL": {
            "required": [
                "MICROINSURANCE_LICENSE",
                "COMMISSION_AGREEMENT",
                "NID",
                "BANK_DETAILS_FORM",
            ],
            "optional": [
                "COMMUNITY_LETTER",
            ],
        },
        "CORPORATE": {
            "required": [
                "MICROINSURANCE_LICENSE",
                "COMMISSION_AGREEMENT",
                "INCORPORATION_CERT",
                "TIN_CERTIFICATE",
            ],
            "optional": [
                "TAX_CLEARANCE_CERT",
            ],
        },
    },
    # Add commission docs to existing types
    "INTERMEDIARY": {
        "INDIVIDUAL": {
            "required": [
                "NID",
                "PASSPORT",
                "TIRA_INTERMEDIARY_LICENSE",
                "COMMISSION_AGREEMENT",
            ],
            "optional": ["DRIVING_LICENSE"],
        },
        "CORPORATE": {
            "required": [
                "INCORPORATION_CERT",
                "TIN_CERTIFICATE",
                "MEMORANDUM",
                "BOARD_RESOLUTION",
                "TIRA_INTERMEDIARY_LICENSE",
                "COMMISSION_AGREEMENT",
            ],
            "optional": [],
        },
    },
    "BROKER": {
        "INDIVIDUAL": {
            "required": [
                "NID",
                "PASSPORT",
                "TIN_CERTIFICATE",
                "COMMISSION_AGREEMENT",
                "PROFESSIONAL_INDEMNITY",
            ],
            "optional": ["DRIVING_LICENSE", "VOTER_ID"],
        },
        "CORPORATE": {
            "required": [
                "INCORPORATION_CERT",
                "TIN_CERTIFICATE",
                "MEMORANDUM",
                "BOARD_RESOLUTION",
                "COMMISSION_AGREEMENT",
                "PROFESSIONAL_INDEMNITY",
            ],
            "optional": [],
        },
    },
}

FORM_FIELDS_CONFIG_UPDATE = {
    "AGENT": {
        "INDIVIDUAL": [
            "identification_type", "identification_number", "title",
            "first_name", "other_name", "surname", "gender",
            "date_of_birth", "marital_status", "occupation",
            "nationality", "email", "telephone_number", "mobile_number",
            "physical_address", "postal_address",
            "license_number", "regulatory_body", "license_expiry_date",
            "commission_rate", "commission_structure", "tax_id",
            "territory", "years_of_experience", "payment_method",
            "supervisory_agent",
        ],
    },
    "AGENCY": {
        "CORPORATE": [
            "company_name", "tin_number", "incorporation_date",
            "industry", "email", "telephone_number", "mobile_number",
            "contact_person", "contact_person_phone",
            "contact_person_email", "physical_address", "postal_address",
            "license_number", "regulatory_body", "license_expiry_date",
            "commission_rate", "commission_structure",
            "corporate_registration_number", "tax_id",
            "number_of_agents", "contract_start_date", "contract_end_date",
        ],
    },
    "BANCASSURANCE": {
        "CORPORATE": [
            "company_name", "tin_number", "incorporation_date",
            "industry", "email", "telephone_number", "mobile_number",
            "contact_person", "contact_person_phone",
            "contact_person_email", "physical_address", "postal_address",
            "bancassurance_license_number", "regulatory_body",
            "license_expiry_date", "commission_rate",
            "partnership_agreement_ref", "partnership_start_date",
            "partnership_end_date", "branch_network", "products_offered",
        ],
    },
    "REINSURANCE_BROKER": {
        "INDIVIDUAL": [
            "identification_type", "identification_number", "title",
            "first_name", "other_name", "surname", "gender",
            "date_of_birth", "marital_status", "occupation",
            "nationality", "email", "telephone_number", "mobile_number",
            "physical_address", "postal_address",
            "license_number", "regulatory_body", "license_expiry_date",
            "brokerage_rate", "corporate_registration_number", "tax_id",
            "professional_indemnity_ref", "pi_expiry_date",
            "reinsurer_credentials",
        ],
        "CORPORATE": [
            "company_name", "tin_number", "incorporation_date",
            "industry", "email", "telephone_number", "mobile_number",
            "contact_person", "contact_person_phone",
            "contact_person_email", "physical_address", "postal_address",
            "license_number", "regulatory_body", "license_expiry_date",
            "brokerage_rate", "corporate_registration_number", "tax_id",
            "professional_indemnity_ref", "pi_expiry_date",
            "reinsurer_credentials",
        ],
    },
    "TAKAFUL_OPERATOR": {
        "CORPORATE": [
            "company_name", "tin_number", "incorporation_date",
            "industry", "email", "telephone_number", "mobile_number",
            "contact_person", "contact_person_phone",
            "contact_person_email", "physical_address", "postal_address",
            "takaful_license_number", "regulatory_body",
            "license_expiry_date", "takaful_commission_rate",
            "takaful_model", "shariah_board_ref",
            "corporate_registration_number", "tax_id",
        ],
    },
    "MICROINSURANCE_AGENT": {
        "INDIVIDUAL": [
            "identification_type", "identification_number", "title",
            "first_name", "other_name", "surname", "gender",
            "date_of_birth", "marital_status", "occupation",
            "nationality", "email", "telephone_number", "mobile_number",
            "physical_address", "postal_address",
            "license_number", "regulatory_body",
            "commission_rate", "tax_id",
            "territory", "community_organisation", "payment_method",
        ],
        "CORPORATE": [
            "company_name", "tin_number", "incorporation_date",
            "industry", "email", "telephone_number", "mobile_number",
            "contact_person", "contact_person_phone",
            "contact_person_email", "physical_address", "postal_address",
            "license_number", "regulatory_body",
            "commission_rate", "tax_id",
            "territory", "community_organisation", "payment_method",
        ],
    },
    # Commission fields added to existing types
    "INTERMEDIARY": {
        "INDIVIDUAL": [
            "identification_type", "identification_number", "title",
            "first_name", "other_name", "surname", "gender",
            "date_of_birth", "marital_status", "occupation",
            "nationality", "email", "telephone_number", "mobile_number",
            "physical_address", "postal_address",
            "license_number", "regulatory_body",
            "commission_rate", "commission_structure", "payment_method",
        ],
        "CORPORATE": [
            "company_name", "tin_number", "incorporation_date",
            "industry", "email", "telephone_number", "mobile_number",
            "contact_person", "contact_person_phone",
            "contact_person_email", "physical_address", "postal_address",
            "license_number", "regulatory_body", "commission_structure",
            "commission_rate", "payment_method",
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
            "brokerage_rate", "payment_method", "broker_commission_terms",
        ],
        "CORPORATE": [
            "company_name", "tin_number", "incorporation_date",
            "industry", "email", "telephone_number", "mobile_number",
            "contact_person", "contact_person_phone",
            "contact_person_email", "physical_address", "postal_address",
            "license_number", "license_expiry_date",
            "regulatory_body", "commission_structure",
            "e_and_o_insurance_ref",
            "brokerage_rate", "payment_method", "broker_commission_terms",
        ],
    },
    "SERVICE_PROVIDER": {
        "CORPORATE": [
            "company_name", "tin_number", "incorporation_date",
            "industry", "email", "telephone_number", "mobile_number",
            "contact_person", "contact_person_phone",
            "contact_person_email", "physical_address", "postal_address",
            "service_category", "contract_start_date",
            "contract_end_date", "insurance_certificate_ref",
            "service_fee_rate", "payment_terms",
        ],
    },
}

CONTACTS_CONFIG_UPDATE = {
    "AGENT": {
        "allowed_contact_types": ["PRIMARY", "SECONDARY"],
        "required_fields": ["first_name", "last_name", "email", "phone"],
        "optional_fields": ["mobile", "designation", "notes"],
        "min_contacts": 1,
        "max_contacts": 2,
    },
    "AGENCY": {
        "allowed_contact_types": ["PRIMARY", "TECHNICAL", "BILLING", "COMPLIANCE"],
        "required_fields": ["first_name", "last_name", "email", "phone", "designation"],
        "optional_fields": ["mobile", "notes"],
        "min_contacts": 2,
        "max_contacts": 5,
    },
    "BANCASSURANCE": {
        "allowed_contact_types": ["PRIMARY", "TECHNICAL", "BILLING", "LEGAL"],
        "required_fields": ["first_name", "last_name", "email", "phone", "designation"],
        "optional_fields": ["mobile", "notes"],
        "min_contacts": 2,
        "max_contacts": 5,
    },
    "REINSURANCE_BROKER": {
        "allowed_contact_types": ["PRIMARY", "TECHNICAL", "BILLING"],
        "required_fields": ["first_name", "last_name", "email", "phone", "designation"],
        "optional_fields": ["mobile", "notes"],
        "min_contacts": 2,
        "max_contacts": 4,
    },
    "TAKAFUL_OPERATOR": {
        "allowed_contact_types": ["PRIMARY", "SHARIAH", "BILLING"],
        "required_fields": ["first_name", "last_name", "email", "phone", "designation"],
        "optional_fields": ["mobile", "notes"],
        "min_contacts": 2,
        "max_contacts": 4,
    },
    "MICROINSURANCE_AGENT": {
        "allowed_contact_types": ["PRIMARY", "SECONDARY"],
        "required_fields": ["first_name", "last_name", "email", "phone"],
        "optional_fields": ["mobile", "notes"],
        "min_contacts": 1,
        "max_contacts": 2,
    },
    "INTERMEDIARY": {
        "allowed_contact_types": ["PRIMARY", "SECONDARY", "BILLING"],
        "required_fields": ["first_name", "last_name", "email", "phone", "designation"],
        "optional_fields": ["mobile", "notes"],
        "min_contacts": 1,
        "max_contacts": 3,
    },
    "BROKER": {
        "allowed_contact_types": ["PRIMARY", "SECONDARY", "BILLING"],
        "required_fields": ["first_name", "last_name", "email", "phone", "designation"],
        "optional_fields": ["mobile", "notes"],
        "min_contacts": 1,
        "max_contacts": 3,
    },
}

BANKS_CONFIG_UPDATE = {
    "AGENT": {
        "required_fields": ["bank_name", "account_name", "account_number"],
        "optional_fields": ["branch_name", "swift_code"],
        "min_accounts": 1,
        "max_accounts": 2,
    },
    "AGENCY": {
        "required_fields": ["bank_name", "account_name", "account_number", "swift_code"],
        "optional_fields": ["branch_name", "iban"],
        "min_accounts": 1,
        "max_accounts": 4,
    },
    "BANCASSURANCE": {
        "required_fields": ["bank_name", "account_name", "account_number", "swift_code"],
        "optional_fields": ["branch_name", "iban"],
        "min_accounts": 1,
        "max_accounts": 4,
    },
    "REINSURANCE_BROKER": {
        "required_fields": ["bank_name", "account_name", "account_number", "swift_code"],
        "optional_fields": ["branch_name", "iban"],
        "min_accounts": 1,
        "max_accounts": 4,
    },
    "TAKAFUL_OPERATOR": {
        "required_fields": ["bank_name", "account_name", "account_number", "swift_code"],
        "optional_fields": ["branch_name", "iban"],
        "min_accounts": 2,
        "max_accounts": 5,
    },
    "MICROINSURANCE_AGENT": {
        "required_fields": ["bank_name", "account_name", "account_number"],
        "optional_fields": ["branch_name", "swift_code"],
        "min_accounts": 0,
        "max_accounts": 2,
    },
    "INTERMEDIARY": {
        "required_fields": ["bank_name", "account_name", "account_number", "swift_code"],
        "optional_fields": ["branch_name", "iban"],
        "min_accounts": 1,
        "max_accounts": 3,
    },
    "BROKER": {
        "required_fields": ["bank_name", "account_name", "account_number", "swift_code"],
        "optional_fields": ["branch_name", "iban"],
        "min_accounts": 1,
        "max_accounts": 3,
    },
}


# =========================================================================
# Migration Functions
# =========================================================================

def seed_partner_types(apps, schema_editor):
    PartnerType = apps.get_model("partners", "PartnerType")

    created = 0
    for pt in NEW_PARTNER_TYPES:
        _, was_created = PartnerType.objects.get_or_create(
            code=pt["code"],
            defaults={
                "name": pt["name"],
                "description": pt["description"],
            },
        )
        if was_created:
            created += 1
    if created:
        logger.info("Created %s new partner type(s)", created)


def seed_field_configurations(apps, schema_editor):
    PartnerType = apps.get_model("partners", "PartnerType")
    PartnerTypeFieldConfiguration = apps.get_model(
        "partners", "PartnerTypeFieldConfiguration"
    )

    total = 0
    for type_code, fields in FIELD_CONFIGS.items():
        try:
            pt = PartnerType.objects.get(code=type_code)
        except PartnerType.DoesNotExist:
            logger.warning("PartnerType %s not found, skipping field configs", type_code)
            continue
        for field in fields:
            _, created = PartnerTypeFieldConfiguration.objects.get_or_create(
                partner_type=pt,
                field_code=field["field_code"],
                defaults={
                    "field_name": field["field_name"],
                    "field_type": field["field_type"],
                    "is_required": field.get("is_required", False),
                    "validation_rules": field.get("validation_rules", {}),
                    "display_order": field.get("display_order", 0),
                    "default_value": field.get("default_value", ""),
                    "visibility_rules": field.get("visibility_rules", {}),
                    "is_active": True,
                },
            )
            if created:
                total += 1
    if total:
        logger.info("Created %s field configuration(s) across partner types", total)


def seed_document_requirements(apps, schema_editor):
    PartnerType = apps.get_model("partners", "PartnerType")
    PartnerTypeDocumentRequirement = apps.get_model(
        "partners", "PartnerTypeDocumentRequirement"
    )

    def create_docs(type_code, doc_list):
        count = 0
        try:
            pt = PartnerType.objects.get(code=type_code)
        except PartnerType.DoesNotExist:
            logger.warning("PartnerType %s not found, skipping docs", type_code)
            return 0
        for doc in doc_list:
            _, created = PartnerTypeDocumentRequirement.objects.get_or_create(
                partner_type=pt,
                code=doc["code"],
                defaults={
                    "description": doc["description"],
                    "is_required": doc["is_required"],
                    "is_mandatory": doc.get("is_mandatory", doc["is_required"]),
                    "sort_order": doc.get("sort_order", 0),
                    "allow_multiple_uploads": doc.get("allow_multiple_uploads", False),
                    "is_active": True,
                },
            )
            if created:
                count += 1
        return count

    total = 0
    for type_code, docs in DOCUMENT_REQUIREMENTS.items():
        total += create_docs(type_code, docs)
    for type_code, docs in EXISTING_TYPE_DOCUMENTS.items():
        total += create_docs(type_code, docs)
    if total:
        logger.info("Created %s document requirement(s) across partner types", total)


def seed_contact_requirements(apps, schema_editor):
    PartnerType = apps.get_model("partners", "PartnerType")
    PartnerTypeContactRequirement = apps.get_model(
        "partners", "PartnerTypeContactRequirement"
    )

    def create_contacts(type_code, contacts):
        count = 0
        try:
            pt = PartnerType.objects.get(code=type_code)
        except PartnerType.DoesNotExist:
            return 0
        for contact in contacts:
            _, created = PartnerTypeContactRequirement.objects.get_or_create(
                partner_type=pt,
                contact_type=contact["contact_type"],
                defaults={
                    "is_required": contact["is_required"],
                    "multiple_allowed": contact.get("multiple_allowed", False),
                    "display_order": contact.get("display_order", 0),
                    "is_active": True,
                },
            )
            if created:
                count += 1
        return count

    total = 0
    for type_code, contacts in CONTACT_REQUIREMENTS.items():
        total += create_contacts(type_code, contacts)
    for type_code, contacts in UPDATED_CONTACT_REQUIREMENTS.items():
        # Update existing contact types (make billing required)
        try:
            pt = PartnerType.objects.get(code=type_code)
        except PartnerType.DoesNotExist:
            continue
        for contact in contacts:
            PartnerTypeContactRequirement.objects.update_or_create(
                partner_type=pt,
                contact_type=contact["contact_type"],
                defaults={
                    "is_required": contact["is_required"],
                    "multiple_allowed": contact.get("multiple_allowed", False),
                    "display_order": contact.get("display_order", 0),
                    "is_active": True,
                },
            )
            total += 1
    if total:
        logger.info("Created/updated %s contact requirement(s) across partner types", total)


def seed_bank_requirements(apps, schema_editor):
    PartnerType = apps.get_model("partners", "PartnerType")
    PartnerTypeBankRequirement = apps.get_model(
        "partners", "PartnerTypeBankRequirement"
    )

    total = 0
    for type_code, banks in BANK_REQUIREMENTS.items():
        try:
            pt = PartnerType.objects.get(code=type_code)
        except PartnerType.DoesNotExist:
            logger.warning("PartnerType %s not found, skipping bank reqs", type_code)
            continue
        for bank in banks:
            _, created = PartnerTypeBankRequirement.objects.get_or_create(
                partner_type=pt,
                bank_type=bank["bank_type"],
                defaults={
                    "is_required": bank["is_required"],
                    "multiple_allowed": bank.get("multiple_allowed", False),
                    "validation_rules": bank.get("validation_rules", {}),
                    "display_order": bank.get("display_order", 0),
                    "is_active": True,
                },
            )
            if created:
                total += 1
    if total:
        logger.info("Created %s bank requirement(s) across partner types", total)


def update_system_parameters(apps, schema_editor):
    """Merge new partner types into existing JSON system parameters."""
    SystemParameter = apps.get_model("system_parameters", "SystemParameter")

    updates = {
        "PARTNER_TYPES_METADATA": PARTNER_TYPES_METADATA_UPDATE,
        "DOCUMENTS_CONFIG": DOCUMENTS_CONFIG_UPDATE,
        "FORM_FIELDS_CONFIG": FORM_FIELDS_CONFIG_UPDATE,
        "CONTACTS_CONFIG": CONTACTS_CONFIG_UPDATE,
        "BANKS_CONFIG": BANKS_CONFIG_UPDATE,
    }

    for code, new_data in updates.items():
        try:
            param = SystemParameter.objects.get(code=code)
            existing = param.json_value or {}
            existing.update(new_data)
            param.json_value = existing
            param.save(update_fields=["json_value", "updated_at"])
            logger.info(
                "Updated %s with %s new partner type(s)",
                code,
                len(new_data),
            )
        except SystemParameter.DoesNotExist:
            logger.warning("System parameter %s not found, skipping", code)


def reverse_seed(apps, schema_editor):
    PartnerType = apps.get_model("partners", "PartnerType")
    PartnerTypeFieldConfiguration = apps.get_model(
        "partners", "PartnerTypeFieldConfiguration"
    )
    PartnerTypeDocumentRequirement = apps.get_model(
        "partners", "PartnerTypeDocumentRequirement"
    )
    PartnerTypeContactRequirement = apps.get_model(
        "partners", "PartnerTypeContactRequirement"
    )
    PartnerTypeBankRequirement = apps.get_model(
        "partners", "PartnerTypeBankRequirement"
    )

    new_codes = [pt["code"] for pt in NEW_PARTNER_TYPES]

    # Delete DB config rows for new types
    for code in new_codes:
        try:
            pt = PartnerType.objects.get(code=code)
            PartnerTypeFieldConfiguration.objects.filter(
                partner_type=pt
            ).delete()
            PartnerTypeDocumentRequirement.objects.filter(
                partner_type=pt
            ).delete()
            PartnerTypeContactRequirement.objects.filter(
                partner_type=pt
            ).delete()
            PartnerTypeBankRequirement.objects.filter(
                partner_type=pt
            ).delete()
        except PartnerType.DoesNotExist:
            pass

    # Delete DB config rows created for existing types (commission-specific)
    for code in ["INTERMEDIARY", "BROKER", "SERVICE_PROVIDER"]:
        try:
            pt = PartnerType.objects.get(code=code)
            PartnerTypeFieldConfiguration.objects.filter(
                partner_type=pt,
                field_code__in=[
                    "commission_rate",
                    "commission_structure",
                    "payment_method",
                    "brokerage_rate",
                    "broker_commission_terms",
                    "service_fee_rate",
                    "payment_terms",
                ],
            ).delete()
            PartnerTypeDocumentRequirement.objects.filter(
                partner_type=pt,
                code__in=[
                    "TIRA_INTERMEDIARY_LICENSE",
                    "COMMISSION_AGREEMENT",
                    "PROFESSIONAL_INDEMNITY",
                ],
            ).delete()
        except PartnerType.DoesNotExist:
            pass

    # Delete new partner types
    PartnerType.objects.filter(code__in=new_codes).delete()

    # Revert system parameters
    SystemParameter = apps.get_model("system_parameters", "SystemParameter")
    for code in [
        "PARTNER_TYPES_METADATA",
        "DOCUMENTS_CONFIG",
        "FORM_FIELDS_CONFIG",
        "CONTACTS_CONFIG",
        "BANKS_CONFIG",
    ]:
        try:
            param = SystemParameter.objects.get(code=code)
            existing = param.json_value or {}
            for k in PARTNER_TYPES_METADATA_UPDATE:
                existing.pop(k, None)
            # Revert INTERMEDIARY and BROKER to remove commission fields
            existing["INTERMEDIARY"] = {
                "allowed_contact_types": ["PRIMARY", "SECONDARY", "BILLING"],
                "required_fields": ["first_name", "last_name", "email", "phone", "designation"],
                "optional_fields": ["mobile", "notes"],
                "min_contacts": 1,
                "max_contacts": 3,
            }
            existing["BROKER"] = {
                "allowed_contact_types": ["PRIMARY", "SECONDARY", "BILLING"],
                "required_fields": ["first_name", "last_name", "email", "phone", "designation"],
                "optional_fields": ["mobile", "notes"],
                "min_contacts": 1,
                "max_contacts": 3,
            }
            param.json_value = existing
            param.save(update_fields=["json_value"])
        except SystemParameter.DoesNotExist:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ("partners", "0007_add_governance_extensions"),
        ("system_parameters", "0005_seed_commission_parameters"),
    ]

    operations = [
        migrations.RunPython(seed_partner_types, reverse_seed),
        migrations.RunPython(seed_field_configurations, reverse_seed),
        migrations.RunPython(seed_document_requirements, reverse_seed),
        migrations.RunPython(seed_contact_requirements, reverse_seed),
        migrations.RunPython(seed_bank_requirements, reverse_seed),
        migrations.RunPython(update_system_parameters, reverse_seed),
    ]
