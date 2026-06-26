"""Seed life insurance commission parameters under PARTNER group."""

from django.db import migrations

COMMISSION_PARAMETERS = [
    {
        "code": "COMMISSION_RATES",
        "name": "Commission Rate Defaults",
        "description": "Default commission rates per product line for life insurance",
        "value_type": "JSON",
        "json_value": {
            "INDIVIDUAL_LIFE": 0.20,
            "GROUP_LIFE": 0.10,
            "CREDIT_LIFE": 0.15,
            "EDUCATION_ENDOWMENT": 0.18,
            "TERM_LIFE": 0.15,
            "WHOLE_LIFE": 0.20,
            "RETIREMENT_ANNUITY": 0.12,
        },
        "sort_order": 10,
        "group_code": "PARTNER_COMMISSION",
        "group_name": "Commission Parameters",
        "group_description": "Life insurance commission rates, rules, and payment configuration",
        "group_sort_order": 85,
    },
    {
        "code": "COMMISSION_TAX_RATES",
        "name": "Commission Withholding Tax Rates",
        "description": "Withholding tax rates on commission payments per Tanzania/Zanzibar tax law",
        "value_type": "JSON",
        "json_value": {
            "RESIDENT_INDIVIDUAL": 0.05,
            "RESIDENT_CORPORATE": 0.05,
            "NON_RESIDENT_INDIVIDUAL": 0.15,
            "NON_RESIDENT_CORPORATE": 0.15,
        },
        "sort_order": 20,
    },
    {
        "code": "COMMISSION_PAYMENT_TERMS",
        "name": "Commission Payment Terms",
        "description": "Payment terms and settlement rules for commission disbursement",
        "value_type": "JSON",
        "json_value": {
            "net_days": 30,
            "settlement_cycle": "MONTHLY",
            "payment_currency": "TZS",
            "min_payment_amount": 5000,
            "max_payment_amount": 100000000,
        },
        "sort_order": 30,
    },
    {
        "code": "COMMISSION_CALCULATION_BASIS",
        "name": "Commission Calculation Basis",
        "description": "Basis for calculating commission — on premium collected, premium due, or sum assured",
        "value_type": "STRING",
        "string_value": "PREMIUM_COLLECTED",
        "sort_order": 40,
    },
    {
        "code": "COMMISSION_SETTLEMENT_CURRENCY",
        "name": "Commission Settlement Currency",
        "description": "Default currency for commission settlement (TZS, USD, EUR)",
        "value_type": "STRING",
        "string_value": "TZS",
        "sort_order": 50,
    },
    {
        "code": "COMMISSION_APPROVAL_THRESHOLD",
        "name": "Commission Approval Threshold",
        "description": "Commission amounts above this threshold (in TZS) require additional approval",
        "value_type": "FLOAT",
        "float_value": 10000000.0,
        "sort_order": 60,
    },
    {
        "code": "COMMISSION_ELIGIBILITY_RULES",
        "name": "Commission Eligibility Rules",
        "description": "Rules determining whether a commission is eligible for payment",
        "value_type": "JSON",
        "json_value": {
            "min_policy_age_days": 30,
            "chargeback_period_days": 180,
            "max_commission_rate_per_policy": 0.30,
            "lapse_allowed_before_payment": False,
            "grace_period_days": 15,
        },
        "sort_order": 70,
    },
    {
        "code": "COMMISSION_APPROVAL_RULES",
        "name": "Commission Approval Rules",
        "description": "Maker/checker approval rules for commission operations",
        "value_type": "JSON",
        "json_value": {
            "APPROVAL_REQUIRED_COMMISSION_PAYMENT": True,
            "APPROVAL_REQUIRED_COMMISSION_RATE_CHANGE": True,
            "APPROVAL_REQUIRED_COMMISSION_CHARGEBACK": True,
            "approval_threshold": 10000000,
            "auto_approve_below_threshold": True,
        },
        "sort_order": 80,
    },
    {
        "code": "COMMISSION_REGULATORY_LIMITS",
        "name": "Regulatory Limits on Commission",
        "description": "TIRA/Zanzibar regulatory caps on commission rates per line of business",
        "value_type": "JSON",
        "json_value": {
            "max_commission_rate": 0.30,
            "max_commission_rate_life": 0.25,
            "max_commission_rate_motor": 0.15,
            "max_commission_rate_medical": 0.10,
            "max_commission_rate_microinsurance": 0.20,
            "regulator": "TIRA",
            "regulation_reference": "Insurance Act No. 10 of 2009",
        },
        "sort_order": 90,
    },
    {
        "code": "COMMISSION_PAYMENT_METHODS",
        "name": "Allowed Commission Payment Methods",
        "description": "List of allowed methods for disbursing commission payments",
        "value_type": "JSON",
        "json_value": {
            "allowed_methods": [
                "BANK_TRANSFER",
                "CHEQUE",
                "MOBILE_MONEY",
            ],
            "default_method": "BANK_TRANSFER",
        },
        "sort_order": 100,
    },
]


def seed_commission_parameters(apps, schema_editor):
    ParameterGroup = apps.get_model("system_parameters", "ParameterGroup")
    SystemParameter = apps.get_model("system_parameters", "SystemParameter")

    partner_group = ParameterGroup.objects.get(code="PARTNER")

    for param in COMMISSION_PARAMETERS:
        group_code = param.pop("group_code", None)
        group_name = param.pop("group_name", None)
        group_description = param.pop("group_description", None)
        group_sort_order = param.pop("group_sort_order", None)

        group = partner_group
        if group_code:
            group, _ = ParameterGroup.objects.get_or_create(
                parent=partner_group,
                code=group_code,
                defaults={
                    "name": group_name or group_code,
                    "description": group_description or "",
                    "sort_order": group_sort_order or 80,
                },
            )

        SystemParameter.objects.get_or_create(
            group=group,
            code=param["code"],
            defaults=param,
        )


def reverse_seed(apps, schema_editor):
    ParameterGroup = apps.get_model("system_parameters", "ParameterGroup")
    SystemParameter = apps.get_model("system_parameters", "SystemParameter")
    SystemParameter.objects.filter(
        code__startswith="COMMISSION_",
    ).delete()
    try:
        pg = ParameterGroup.objects.get(code="PARTNER_COMMISSION")
        pg.delete()
    except ParameterGroup.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ("system_parameters", "0004_seed_partner_type_config"),
    ]

    operations = [
        migrations.RunPython(seed_commission_parameters, reverse_seed),
    ]
