# Generated manually for ONBOARDING.md remediation
# Seed all required ChoiceLists and ChoiceOptions for dynamic parameters

from django.db import migrations


def seed_choice_lists(apps, schema_editor):
    """Seed all choice lists for dynamic configuration"""
    ChoiceList = apps.get_model('system_parameters', 'ChoiceList')
    ChoiceOption = apps.get_model('system_parameters', 'ChoiceOption')

    choice_lists_data = {
        'PARTNER_TYPE_CHOICES': [
            ('INDIVIDUAL', 'Individual', 1),
            ('CORPORATE', 'Corporate', 2),
            ('AGENT', 'Agent', 3),
            ('BROKER', 'Broker', 4),
            ('BANCASSURER', 'Bancassurer', 5),
            ('SERVICE_PROVIDER', 'Service Provider', 6),
        ],
        'APPLICATION_STATUS_CHOICES': [
            ('DRAFT', 'Draft', 1),
            ('SUBMITTED', 'Submitted', 2),
            ('UNDER_REVIEW', 'Under Review', 3),
            ('PENDING_DOCUMENTS', 'Pending Documents', 4),
            ('COMPLIANCE_CHECK', 'Compliance Check', 5),
            ('FINANCIAL_REVIEW', 'Financial Review', 6),
            ('PENDING_APPROVAL', 'Pending Approval', 7),
            ('APPROVED', 'Approved', 8),
            ('REJECTED', 'Rejected', 9),
            ('CONVERTED', 'Converted to Partner', 10),
            ('SUSPENDED', 'Suspended', 11),
        ],
        'DOCUMENT_TYPE_CHOICES': [
            ('NATIONAL_ID', 'National ID', 1),
            ('PASSPORT', 'Passport', 2),
            ('ZAN_ID', 'Zanzibar ID', 3),
            ('DRIVING_LICENSE', 'Driving License', 4),
            ('TIN_CERTIFICATE', 'TIN Certificate', 5),
            ('VOTER_ID', 'Voter ID', 6),
            ('RESIDENT_PERMIT', 'Resident Permit', 7),
            ('MILITARY_ID', 'Military ID', 8),
            ('INCORPORATION_CERT', 'Certificate of Incorporation', 9),
            ('MEMORANDUM', 'Memorandum of Association', 10),
            ('BOARD_RESOLUTION', 'Board Resolution', 11),
            ('LICENSE', 'License/Certification', 12),
            ('OTHER', 'Other', 13),
        ],
        'GENDER_CHOICES': [
            ('MALE', 'Male', 1),
            ('FEMALE', 'Female', 2),
            ('OTHER', 'Other', 3),
        ],
        'TITLE_CHOICES': [
            ('MR', 'Mr', 1),
            ('MRS', 'Mrs', 2),
            ('MS', 'Ms', 3),
            ('DR', 'Dr', 4),
            ('PROF', 'Prof', 5),
        ],
        'MARITAL_STATUS_CHOICES': [
            ('SINGLE', 'Single', 1),
            ('MARRIED', 'Married', 2),
            ('DIVORCED', 'Divorced', 3),
            ('WIDOWED', 'Widowed', 4),
            ('OTHER', 'Other', 5),
        ],
        'NATIONALITY_CHOICES': [
            ('TANZANIAN', 'Tanzanian', 1),
            ('KENYAN', 'Kenyan', 2),
            ('UGANDAN', 'Ugandan', 3),
            ('RWANDAN', 'Rwandan', 4),
            ('BURUNDIAN', 'Burundian', 5),
            ('OTHER', 'Other', 6),
        ],
        'INDUSTRY_CHOICES': [
            ('AGRICULTURE', 'Agriculture', 1),
            ('BANKING', 'Banking & Finance', 2),
            ('CONSTRUCTION', 'Construction', 3),
            ('EDUCATION', 'Education', 4),
            ('HEALTHCARE', 'Healthcare', 5),
            ('IT', 'Information Technology', 6),
            ('INSURANCE', 'Insurance', 7),
            ('MANUFACTURING', 'Manufacturing', 8),
            ('TOURISM', 'Tourism & Hospitality', 9),
            ('GOVERNMENT', 'Government', 10),
            ('OTHER', 'Other', 11),
        ],
        'CONTACT_TYPE_CHOICES': [
            ('PRIMARY', 'Primary', 1),
            ('SECONDARY', 'Secondary', 2),
            ('BILLING', 'Billing', 3),
            ('TECHNICAL', 'Technical', 4),
            ('COMPLIANCE_OFFICER', 'Compliance Officer', 5),
            ('OTHER', 'Other', 6),
        ],
        'KYC_STATUS_CHOICES': [
            ('NOT_SET', 'Not Set', 1),
            ('PENDING_REVIEW', 'Pending Review', 2),
            ('VERIFIED', 'Verified', 3),
            ('REJECTED', 'Rejected', 4),
            ('EXPIRED', 'Expired', 5),
        ],
        'CURRENCY_CHOICES': [
            ('TZS', 'Tanzanian Shilling', 1),
            ('USD', 'US Dollar', 2),
            ('EUR', 'Euro', 3),
            ('GBP', 'British Pound', 4),
            ('KES', 'Kenyan Shilling', 5),
        ],
        'OTP_METHOD_CHOICES': [
            ('SMS', 'SMS', 1),
            ('EMAIL', 'Email', 2),
            ('AUTH_APP', 'Authenticator App', 3),
        ],
        'APPROVAL_STATUS_CHOICES': [
            ('PENDING', 'Pending', 1),
            ('APPROVED', 'Approved', 2),
            ('REJECTED', 'Rejected', 3),
            ('CANCELLED', 'Cancelled', 4),
        ],
        'USER_TYPE_CHOICES': [
            ('PORTAL_USER', 'Portal User', 1),
            ('MANAGER', 'Manager', 2),
            ('QUOTATION_ONLY', 'Quotation Only', 3),
            ('UNDERWRITER', 'Underwriter', 4),
            ('SYSTEM_MANAGER', 'System Manager', 5),
            ('AIMS_GROUP', 'AIMS Group', 6),
            ('SUPER_ADMIN', 'Super Admin', 7),
            ('ONBOARDING_CLERK', 'Onboarding Clerk', 8),
            ('COMPLIANCE_OFFICER', 'Compliance Officer', 9),
            ('FINANCE_MANAGER', 'Finance Manager', 10),
            ('ZIC_AUDITOR', 'ZIC Auditor', 11),
        ],
        'POLITICAL_RISK_CHOICES': [
            ('LOW', 'Low', 1),
            ('MEDIUM', 'Medium', 2),
            ('HIGH', 'High', 3),
            ('PEP', 'Politically Exposed Person', 4),
        ],
        'AML_RISK_CHOICES': [
            ('LOW', 'Low Risk', 1),
            ('MEDIUM', 'Medium Risk', 2),
            ('HIGH', 'High Risk', 3),
        ],
    }

    for list_code, options in choice_lists_data.items():
        choice_list, _ = ChoiceList.objects.get_or_create(
            code=list_code,
            defaults={
                'name': list_code.replace('_', ' ').title(),
                'description': f'Dynamic {list_code.lower().replace("_", " ")}',
                'is_active': True,
            }
        )

        for code, label, order in options:
            ChoiceOption.objects.get_or_create(
                choice_list=choice_list,
                code=code,
                defaults={
                    'label': label,
                    'sort_order': order,
                    'is_active': True,
                }
            )


def reverse_seed_choice_lists(apps, schema_editor):
    """Reverse: remove all seeded choice lists"""
    ChoiceList = apps.get_model('system_parameters', 'ChoiceList')
    ChoiceList.objects.filter(code__in=[
        'PARTNER_TYPE_CHOICES',
        'APPLICATION_STATUS_CHOICES',
        'DOCUMENT_TYPE_CHOICES',
        'GENDER_CHOICES',
        'TITLE_CHOICES',
        'MARITAL_STATUS_CHOICES',
        'NATIONALITY_CHOICES',
        'INDUSTRY_CHOICES',
        'CONTACT_TYPE_CHOICES',
        'KYC_STATUS_CHOICES',
        'CURRENCY_CHOICES',
        'OTP_METHOD_CHOICES',
        'APPROVAL_STATUS_CHOICES',
        'USER_TYPE_CHOICES',
        'POLITICAL_RISK_CHOICES',
        'AML_RISK_CHOICES',
    ]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('system_parameters', '0006_seed_nationality_choices'),
    ]

    operations = [
        migrations.RunPython(seed_choice_lists, reverse_seed_choice_lists),
    ]
