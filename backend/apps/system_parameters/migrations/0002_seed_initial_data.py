"""Seed initial system parameter groups and default parameters."""

from django.db import migrations


def seed_initial_groups(apps, schema_editor):
    ParameterGroup = apps.get_model("system_parameters", "ParameterGroup")
    SystemParameter = apps.get_model("system_parameters", "SystemParameter")
    ChoiceList = apps.get_model("system_parameters", "ChoiceList")
    ChoiceOption = apps.get_model("system_parameters", "ChoiceOption")

    # ------------------------------------------------------------------
    # 1. Create Top-Level Groups
    # ------------------------------------------------------------------

    general = ParameterGroup.objects.create(
        code="GENERAL", name="General Parameters",
        description="System-wide settings and global configuration",
        sort_order=10,
    )
    partner = ParameterGroup.objects.create(
        code="PARTNER", name="Partner Parameters",
        description="Partner onboarding workflow, choices, compliance, validation, numbering",
        sort_order=20,
    )
    users = ParameterGroup.objects.create(
        code="USERS", name="User Parameters",
        description="User account settings, session policies, authentication rules",
        sort_order=30,
    )
    reinsurance = ParameterGroup.objects.create(
        code="REINSURANCE", name="Reinsurance Parameters",
        description="Reinsurance treaties, limits, cession rules",
        sort_order=40,
    )

    # ------------------------------------------------------------------
    # 2. Create Partner Sub-Groups
    # ------------------------------------------------------------------

    workflow = ParameterGroup.objects.create(
        parent=partner, code="PARTNER_WORKFLOW", name="Workflow & Statuses",
        description="State machine transitions, allowed statuses, permission rules",
        sort_order=10,
    )
    choices_grp = ParameterGroup.objects.create(
        parent=partner, code="PARTNER_CHOICES", name="Dropdown Choices",
        description="All selectable options: ID types, titles, genders, industries, etc.",
        sort_order=20,
    )
    documents = ParameterGroup.objects.create(
        parent=partner, code="PARTNER_DOCUMENTS", name="Document Config",
        description="Allowed MIME types, file size limits, upload rules",
        sort_order=30,
    )
    compliance = ParameterGroup.objects.create(
        parent=partner, code="PARTNER_COMPLIANCE", name="Compliance Rules",
        description="Risk scoring weights, thresholds, high-risk industries",
        sort_order=40,
    )
    validation = ParameterGroup.objects.create(
        parent=partner, code="PARTNER_VALIDATION", name="Field Validation",
        description="Required fields per partner type, age validation, data rules",
        sort_order=50,
    )
    numbering = ParameterGroup.objects.create(
        parent=partner, code="PARTNER_NUMBERING", name="Numbering Formats",
        description="Application and partner number prefixes, formats, sequences",
        sort_order=60,
    )
    schedules = ParameterGroup.objects.create(
        parent=partner, code="PARTNER_SCHEDULES", name="Scheduled Tasks",
        description="Intervals for automated jobs: draft cleanup, reminders, reports",
        sort_order=70,
    )

    # ------------------------------------------------------------------
    # 3. Seed System Parameters
    # ------------------------------------------------------------------

    SystemParameter.objects.create(
        group=workflow, code="STATE_MACHINE", name="State Machine Transitions",
        value_type="JSON", json_value={
            "ACTIVE": ["DRAFT", "SUBMITTED"],
            "DRAFT": ["SUBMITTED"],
            "SUBMITTED": ["UNDER_REVIEW", "DRAFT"],
            "UNDER_REVIEW": ["PENDING_DOCUMENTS", "COMPLIANCE_CHECK", "REJECTED"],
            "PENDING_DOCUMENTS": ["UNDER_REVIEW", "COMPLIANCE_CHECK", "REJECTED"],
            "COMPLIANCE_CHECK": ["APPROVED", "REJECTED", "SUSPENDED"],
            "APPROVED": ["CONVERTED"],
            "SUSPENDED": ["COMPLIANCE_CHECK", "REJECTED"],
            "REJECTED": [],
            "CONVERTED": [],
        },
        description="Allowed status transitions for partner applications",
        sort_order=10,
    )
    SystemParameter.objects.create(
        group=workflow, code="TERMINAL_STATUSES", name="Terminal Statuses",
        value_type="JSON", json_value=["REJECTED", "CONVERTED"],
        description="Statuses that cannot transition to any other status",
        sort_order=20,
    )
    SystemParameter.objects.create(
        group=documents, code="ALLOWED_MIME_TYPES", name="Allowed MIME Types",
        value_type="JSON", json_value=[
            "application/pdf", "image/jpeg", "image/png", "image/jpg",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ],
        sort_order=10,
    )
    SystemParameter.objects.create(
        group=documents, code="MAX_FILE_SIZE_MB", name="Max File Size (MB)",
        value_type="INTEGER", integer_value=10,
        sort_order=20,
    )
    SystemParameter.objects.create(
        group=documents, code="EXCEL_EXTENSIONS", name="Excel File Extensions",
        value_type="JSON", json_value=[".xlsx", ".xls"],
        sort_order=30,
    )
    SystemParameter.objects.create(
        group=compliance, code="RISK_WEIGHTS_POLITICAL", name="Political Risk Weights",
        value_type="JSON", json_value={"LOW": 0, "MEDIUM": 10, "HIGH": 25, "PEP": 40},
        sort_order=10,
    )
    SystemParameter.objects.create(
        group=compliance, code="RISK_WEIGHTS_AML", name="AML Risk Weights",
        value_type="JSON", json_value={"LOW": 0, "MEDIUM": 10, "HIGH": 25},
        sort_order=20,
    )
    SystemParameter.objects.create(
        group=compliance, code="HIGH_RISK_THRESHOLDS", name="High-Risk Thresholds",
        value_type="JSON", json_value={"INDIVIDUAL": 50, "CORPORATE": 60},
        sort_order=30,
    )
    SystemParameter.objects.create(
        group=compliance, code="HIGH_RISK_INDUSTRIES", name="High-Risk Industries",
        value_type="JSON", json_value=[
            "FINANCIAL_SERVICES", "OIL_GAS", "MINING", "CHEMICALS", "REAL_ESTATE",
        ],
        sort_order=40,
    )
    SystemParameter.objects.create(
        group=compliance, code="INDUSTRY_RISK_BONUS", name="Industry Risk Bonus",
        value_type="INTEGER", integer_value=15, sort_order=50,
    )
    SystemParameter.objects.create(
        group=compliance, code="PEP_INDIVIDUAL_BONUS", name="PEP Individual Bonus",
        value_type="INTEGER", integer_value=10, sort_order=60,
    )
    SystemParameter.objects.create(
        group=compliance, code="MAX_RISK_SCORE", name="Max Risk Score",
        value_type="INTEGER", integer_value=100, sort_order=70,
    )
    SystemParameter.objects.create(
        group=validation, code="MINIMUM_AGE", name="Minimum Age",
        value_type="INTEGER", integer_value=18,
        description="Minimum age requirement for partner applications",
        sort_order=10,
    )
    SystemParameter.objects.create(
        group=validation, code="INDIVIDUAL_REQUIRED_FIELDS", name="Individual Required Fields",
        value_type="JSON", json_value=[
            "identification_type", "identification_number", "first_name",
            "surname", "email", "mobile_number", "date_of_birth",
            "nationality", "gender",
        ],
        sort_order=20,
    )
    SystemParameter.objects.create(
        group=validation, code="CORPORATE_REQUIRED_FIELDS", name="Corporate Required Fields",
        value_type="JSON", json_value=[
            "company_name", "tin_number", "incorporation_date",
            "industry", "email", "mobile_number",
            "contact_person", "contact_person_phone",
            "contact_person_email", "physical_address",
        ],
        sort_order=30,
    )
    SystemParameter.objects.create(
        group=validation, code="EMAIL_UNIQUENESS_STATUSES", name="Email Uniqueness Exempt Statuses",
        value_type="JSON", json_value=[
            "SUBMITTED", "UNDER_REVIEW", "COMPLIANCE_CHECK", "APPROVED",
        ],
        sort_order=40,
    )
    SystemParameter.objects.create(
        group=numbering, code="INDIVIDUAL_APP_PREFIX", name="Individual Application Prefix",
        value_type="STRING", string_value="PA",
        sort_order=10,
    )
    SystemParameter.objects.create(
        group=numbering, code="CORPORATE_APP_PREFIX", name="Corporate Application Prefix",
        value_type="STRING", string_value="CO",
        sort_order=20,
    )
    SystemParameter.objects.create(
        group=numbering, code="PARTNER_PREFIX", name="Partner Number Prefix",
        value_type="STRING", string_value="PN",
        sort_order=30,
    )
    SystemParameter.objects.create(
        group=numbering, code="SEQUENCE_PADDING", name="Sequence Digit Padding",
        value_type="INTEGER", integer_value=6,
        description="Number of digits for the sequential portion of the number",
        sort_order=40,
    )
    SystemParameter.objects.create(
        group=numbering, code="INCLUDE_YEAR", name="Include Year in Number",
        value_type="BOOLEAN", boolean_value=True,
        sort_order=50,
    )
    SystemParameter.objects.create(
        group=schedules, code="DRAFT_CLEANUP_DAYS", name="Expired Draft Cleanup (days)",
        value_type="INTEGER", integer_value=30,
        sort_order=10,
    )
    SystemParameter.objects.create(
        group=schedules, code="PENDING_DOC_REMINDER_DAYS", name="Pending Document Reminder (days)",
        value_type="INTEGER", integer_value=7,
        sort_order=20,
    )
    SystemParameter.objects.create(
        group=schedules, code="COMPLIANCE_REPORT_DAYS", name="Compliance Report Window (days)",
        value_type="INTEGER", integer_value=7,
        sort_order=30,
    )

    # ------------------------------------------------------------------
    # 4. Create Choice Lists as DB-backed data
    # ------------------------------------------------------------------

    id_types = ChoiceList.objects.create(
        group=partner, code="IDENTIFICATION_TYPE_CHOICES", name="Identification Types",
    )
    for option in [
        ("NIN", "National ID"), ("PASSPORT", "Passport"), ("ZAN_ID", "Zanzibar ID"),
        ("DRIVING_LICENSE", "Driving License"), ("TIN", "TIN Certificate"),
        ("VOTER_ID", "Voter ID"), ("RESIDENT_PERMIT", "Resident Permit"),
        ("MILITARY_ID", "Military ID"), ("INCORPORATION_CERT", "Certificate of Incorporation"),
        ("MEMORANDUM", "Memorandum of Association"), ("BOARD_RESOLUTION", "Board Resolution"),
        ("OTHER", "Other"),
    ]:
        ChoiceOption.objects.create(choice_list=id_types, code=option[0], label=option[1])

    titles = ChoiceList.objects.create(
        group=partner, code="TITLE_CHOICES", name="Titles",
    )
    for code in ["Mr", "Mrs", "Miss", "Ms", "Dr", "Prof", "Hon", "Eng", "Rev"]:
        ChoiceOption.objects.create(choice_list=titles, code=code, label=code)

    genders = ChoiceList.objects.create(
        group=partner, code="GENDER_CHOICES", name="Genders",
    )
    ChoiceOption.objects.create(choice_list=genders, code="MALE", label="Male")
    ChoiceOption.objects.create(choice_list=genders, code="FEMALE", label="Female")

    marital = ChoiceList.objects.create(
        group=partner, code="MARITAL_STATUS_CHOICES", name="Marital Statuses",
    )
    for option in [("SINGLE", "Single"), ("MARRIED", "Married"), ("DIVORCED", "Divorced"),
                   ("WIDOWED", "Widowed"), ("SEPARATED", "Separated")]:
        ChoiceOption.objects.create(choice_list=marital, code=option[0], label=option[1])

    pol_risk = ChoiceList.objects.create(
        group=partner, code="POLITICAL_RISK_CHOICES", name="Political Risk Levels",
    )
    for option in [("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High"), ("PEP", "Politically Exposed Person")]:
        ChoiceOption.objects.create(choice_list=pol_risk, code=option[0], label=option[1])

    aml_risk = ChoiceList.objects.create(
        group=partner, code="AML_RISK_CHOICES", name="AML Risk Levels",
    )
    for option in [("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High")]:
        ChoiceOption.objects.create(choice_list=aml_risk, code=option[0], label=option[1])

    industries = ChoiceList.objects.create(
        group=partner, code="INDUSTRY_CHOICES", name="Industries",
    )
    for option in [
        ("TECHNOLOGY", "Technology"), ("HEALTHCARE", "Healthcare & Pharmaceuticals"),
        ("FINANCIAL_SERVICES", "Financial Services & Banking"),
        ("CONSUMER_GOODS", "Consumer Goods & Retail"), ("ENERGY", "Energy & Utilities"),
        ("MANUFACTURING", "Manufacturing & Industrial"),
        ("TELECOMMUNICATIONS", "Telecommunications"),
        ("TRANSPORTATION", "Transportation & Logistics"),
        ("REAL_ESTATE", "Real Estate & Construction"), ("AGRICULTURE", "Agriculture & Food Production"),
        ("INSURANCE", "Insurance"), ("OIL_GAS", "Oil & Gas"), ("FINTECH", "Fintech"),
    ]:
        ChoiceOption.objects.create(choice_list=industries, code=option[0], label=option[1])

    doc_types = ChoiceList.objects.create(
        group=partner, code="DOCUMENT_TYPE_CHOICES", name="Document Types",
    )
    for option in [
        ("NID", "National ID"), ("PASSPORT", "Passport"),
        ("TIN_CERTIFICATE", "TIN Certificate"),
        ("INCORPORATION_CERT", "Certificate of Incorporation"),
        ("MEMORANDUM", "Memorandum of Association"),
        ("BOARD_RESOLUTION", "Board Resolution"), ("OTHER", "Other"),
    ]:
        ChoiceOption.objects.create(choice_list=doc_types, code=option[0], label=option[1])

    task_types = ChoiceList.objects.create(
        group=partner, code="TASK_TYPE_CHOICES", name="Task Types",
    )
    for option in [
        ("DOCUMENT_REQUEST", "Document Request"), ("COMPLIANCE_CHECK", "Compliance Check"),
        ("REVIEW", "Review"), ("APPROVAL", "Approval"), ("OTHER", "Other"),
    ]:
        ChoiceOption.objects.create(choice_list=task_types, code=option[0], label=option[1])

    task_statuses = ChoiceList.objects.create(
        group=partner, code="TASK_STATUS_CHOICES", name="Task Statuses",
    )
    for option in [("PENDING", "Pending"), ("IN_PROGRESS", "In Progress"),
                   ("COMPLETED", "Completed"), ("CANCELLED", "Cancelled")]:
        ChoiceOption.objects.create(choice_list=task_statuses, code=option[0], label=option[1])

    task_priorities = ChoiceList.objects.create(
        group=partner, code="TASK_PRIORITY_CHOICES", name="Task Priorities",
    )
    for option in [("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High"), ("URGENT", "Urgent")]:
        ChoiceOption.objects.create(choice_list=task_priorities, code=option[0], label=option[1])

    contact_types = ChoiceList.objects.create(
        group=partner, code="CONTACT_TYPE_CHOICES", name="Contact Types",
    )
    for option in [("PRIMARY", "Primary"), ("SECONDARY", "Secondary"),
                   ("BILLING", "Billing"), ("TECHNICAL", "Technical"), ("OTHER", "Other")]:
        ChoiceOption.objects.create(choice_list=contact_types, code=option[0], label=option[1])

    app_statuses = ChoiceList.objects.create(
        group=partner, code="APPLICATION_STATUS_CHOICES", name="Application Statuses",
    )
    for option in [
        ("ACTIVE", "Active"), ("DRAFT", "Draft"), ("SUBMITTED", "Submitted"),
        ("UNDER_REVIEW", "Under Review"), ("PENDING_DOCUMENTS", "Pending Documents"),
        ("COMPLIANCE_CHECK", "Compliance Check"), ("APPROVED", "Approved"),
        ("CONVERTED", "Converted to Partner"), ("REJECTED", "Rejected"),
        ("SUSPENDED", "Suspended"),
    ]:
        ChoiceOption.objects.create(choice_list=app_statuses, code=option[0], label=option[1])


def reverse_seed(apps, schema_editor):
    """Remove all seeded data."""
    ParameterGroup = apps.get_model("system_parameters", "ParameterGroup")
    SystemParameter = apps.get_model("system_parameters", "SystemParameter")
    ChoiceList = apps.get_model("system_parameters", "ChoiceList")
    ChoiceOption = apps.get_model("system_parameters", "ChoiceOption")
    ChoiceOption.objects.all().delete()
    ChoiceList.objects.all().delete()
    SystemParameter.objects.all().delete()
    ParameterGroup.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("system_parameters", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(seed_initial_groups, reverse_seed),
    ]
