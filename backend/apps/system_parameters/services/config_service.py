import logging
from functools import lru_cache
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutes


class ConfigurationError(Exception):
    pass


FALLBACK_DEFAULTS = {
    "STATE_MACHINE": {
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
    "TERMINAL_STATUSES": ["REJECTED", "CONVERTED"],
    "ALLOWED_MIME_TYPES": [
        "application/pdf", "image/jpeg", "image/png", "image/jpg",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ],
    "MAX_FILE_SIZE_MB": 10,
    "EXCEL_EXTENSIONS": [".xlsx", ".xls"],
    "RISK_WEIGHTS_POLITICAL": {"LOW": 0, "MEDIUM": 10, "HIGH": 25, "PEP": 40},
    "RISK_WEIGHTS_AML": {"LOW": 0, "MEDIUM": 10, "HIGH": 25},
    "HIGH_RISK_THRESHOLDS": {"INDIVIDUAL": 50, "CORPORATE": 60},
    "HIGH_RISK_INDUSTRIES": [
        "FINANCIAL_SERVICES", "OIL_GAS", "MINING", "CHEMICALS", "REAL_ESTATE",
    ],
    "INDUSTRY_RISK_BONUS": 15,
    "PEP_INDIVIDUAL_BONUS": 10,
    "MAX_RISK_SCORE": 100,
    "MINIMUM_AGE": 18,
    "INDIVIDUAL_REQUIRED_FIELDS": [
        "identification_type", "identification_number", "first_name",
        "surname", "email", "mobile_number", "date_of_birth",
        "nationality", "gender",
    ],
    "CORPORATE_REQUIRED_FIELDS": [
        "company_name", "tin_number", "incorporation_date",
        "industry", "email", "mobile_number",
        "contact_person", "contact_person_phone",
        "contact_person_email", "physical_address",
    ],
    "EMAIL_UNIQUENESS_STATUSES": [
        "SUBMITTED", "UNDER_REVIEW", "COMPLIANCE_CHECK", "APPROVED",
    ],
    "INDIVIDUAL_APP_PREFIX": "PA",
    "CORPORATE_APP_PREFIX": "CO",
    "PARTNER_PREFIX": "PN",
    "SEQUENCE_PADDING": 6,
    "INCLUDE_YEAR": True,
}

FALLBACK_CHOICE_LISTS = {
    "APPLICATION_STATUS_CHOICES": [
        {"value": "CREATED", "label": "Created"},
        {"value": "MODIFIED", "label": "Modified"},
        {"value": "ACTIVE", "label": "Active"},
        {"value": "DRAFT", "label": "Draft"},
        {"value": "SUBMITTED", "label": "Submitted"},
        {"value": "UNDER_REVIEW", "label": "Under Review"},
        {"value": "PENDING_DOCUMENTS", "label": "Pending Documents"},
        {"value": "COMPLIANCE_CHECK", "label": "Compliance Check"},
        {"value": "APPROVED", "label": "Approved"},
        {"value": "CONVERTED", "label": "Converted to Partner"},
        {"value": "REJECTED", "label": "Rejected"},
        {"value": "SUSPENDED", "label": "Suspended"},
    ],
    "IDENTIFICATION_TYPE_CHOICES": [
        {"value": "NIN", "label": "National ID"},
        {"value": "PASSPORT", "label": "Passport"},
        {"value": "ZAN_ID", "label": "Zanzibar ID"},
        {"value": "DRIVING_LICENSE", "label": "Driving License"},
        {"value": "TIN", "label": "TIN Certificate"},
        {"value": "VOTER_ID", "label": "Voter ID"},
        {"value": "RESIDENT_PERMIT", "label": "Resident Permit"},
        {"value": "MILITARY_ID", "label": "Military ID"},
        {"value": "INCORPORATION_CERT", "label": "Certificate of Incorporation"},
        {"value": "MEMORANDUM", "label": "Memorandum of Association"},
        {"value": "BOARD_RESOLUTION", "label": "Board Resolution"},
        {"value": "OTHER", "label": "Other"},
    ],
    "TITLE_CHOICES": [
        {"value": code, "label": code}
        for code in ["Mr", "Mrs", "Miss", "Ms", "Dr", "Prof", "Hon", "Eng", "Rev"]
    ],
    "GENDER_CHOICES": [
        {"value": "MALE", "label": "Male"},
        {"value": "FEMALE", "label": "Female"},
    ],
    "MARITAL_STATUS_CHOICES": [
        {"value": "SINGLE", "label": "Single"},
        {"value": "MARRIED", "label": "Married"},
        {"value": "DIVORCED", "label": "Divorced"},
        {"value": "WIDOWED", "label": "Widowed"},
        {"value": "SEPARATED", "label": "Separated"},
    ],
    "POLITICAL_RISK_CHOICES": [
        {"value": "LOW", "label": "Low"},
        {"value": "MEDIUM", "label": "Medium"},
        {"value": "HIGH", "label": "High"},
        {"value": "PEP", "label": "Politically Exposed Person"},
    ],
    "AML_RISK_CHOICES": [
        {"value": "LOW", "label": "Low"},
        {"value": "MEDIUM", "label": "Medium"},
        {"value": "HIGH", "label": "High"},
    ],
    "INDUSTRY_CHOICES": [
        {"value": "TECHNOLOGY", "label": "Technology"},
        {"value": "HEALTHCARE", "label": "Healthcare & Pharmaceuticals"},
        {"value": "FINANCIAL_SERVICES", "label": "Financial Services & Banking"},
        {"value": "CONSUMER_GOODS", "label": "Consumer Goods & Retail"},
        {"value": "ENERGY", "label": "Energy & Utilities"},
        {"value": "MANUFACTURING", "label": "Manufacturing & Industrial"},
        {"value": "TELECOMMUNICATIONS", "label": "Telecommunications"},
        {"value": "TRANSPORTATION", "label": "Transportation & Logistics"},
        {"value": "REAL_ESTATE", "label": "Real Estate & Construction"},
        {"value": "AGRICULTURE", "label": "Agriculture & Food Production"},
        {"value": "INSURANCE", "label": "Insurance"},
        {"value": "OIL_GAS", "label": "Oil & Gas"},
        {"value": "FINTECH", "label": "Fintech"},
    ],
    "DOCUMENT_TYPE_CHOICES": [
        {"value": "NID", "label": "National ID"},
        {"value": "PASSPORT", "label": "Passport"},
        {"value": "TIN_CERTIFICATE", "label": "TIN Certificate"},
        {"value": "INCORPORATION_CERT", "label": "Certificate of Incorporation"},
        {"value": "MEMORANDUM", "label": "Memorandum of Association"},
        {"value": "BOARD_RESOLUTION", "label": "Board Resolution"},
        {"value": "OTHER", "label": "Other"},
    ],
    "TASK_TYPE_CHOICES": [
        {"value": "DOCUMENT_REQUEST", "label": "Document Request"},
        {"value": "COMPLIANCE_CHECK", "label": "Compliance Check"},
        {"value": "REVIEW", "label": "Review"},
        {"value": "APPROVAL", "label": "Approval"},
        {"value": "OTHER", "label": "Other"},
    ],
    "TASK_STATUS_CHOICES": [
        {"value": "PENDING", "label": "Pending"},
        {"value": "IN_PROGRESS", "label": "In Progress"},
        {"value": "COMPLETED", "label": "Completed"},
        {"value": "CANCELLED", "label": "Cancelled"},
    ],
    "TASK_PRIORITY_CHOICES": [
        {"value": "LOW", "label": "Low"},
        {"value": "MEDIUM", "label": "Medium"},
        {"value": "HIGH", "label": "High"},
        {"value": "URGENT", "label": "Urgent"},
    ],
    "CONTACT_TYPE_CHOICES": [
        {"value": "PRIMARY", "label": "Primary"},
        {"value": "SECONDARY", "label": "Secondary"},
        {"value": "BILLING", "label": "Billing"},
        {"value": "TECHNICAL", "label": "Technical"},
        {"value": "OTHER", "label": "Other"},
    ],
}


class ConfigurationService:
    """Central configuration service that reads from System Parameters and Choice Lists.

    All business configuration flows through this service. It provides:
    - Choice list options (dropdown values)
    - System parameter values (key-value config)
    - Workflow definitions
    - Numbering formats
    - Compliance rules
    - Document upload rules

    Results are cached with a configurable TTL and invalidated on config changes.
    """

    # ------------------------------------------------------------------
    # Choice List access
    # ------------------------------------------------------------------

    @staticmethod
    def _get_dynamic_choice_list(code: str) -> list[dict] | None:
        """Return a choice list from model data for codes that aren't in ChoiceList table."""
        if code == "SYSTEM_PARTNER_TYPES":
            from apps.partners.models import PartnerType
            return [
                {"value": str(pt.id), "label": pt.name}
                for pt in PartnerType.objects.filter(is_active=True).order_by("name")
            ]
        if code == "BRANCHES":
            from apps.partner_onboarding.models import Branch
            return [
                {"value": str(b.id), "label": b.name}
                for b in Branch.objects.filter(is_active=True).order_by("name")
            ]
        if code == "LOCATIONS":
            from apps.partner_onboarding.models import Location
            return [
                {"value": str(l.id), "label": l.name, "branchId": str(l.branch_id)}
                for l in Location.objects.filter(is_active=True).order_by("name")
            ]
        if code == "REGIONS":
            return [
                {"value": "arusha", "label": "Arusha"},
                {"value": "dar-es-salaam", "label": "Dar es Salaam"},
                {"value": "dodoma", "label": "Dodoma"},
                {"value": "geita", "label": "Geita"},
                {"value": "iringa", "label": "Iringa"},
                {"value": "kagera", "label": "Kagera"},
                {"value": "katavi", "label": "Katavi"},
                {"value": "kigoma", "label": "Kigoma"},
                {"value": "kilimanjaro", "label": "Kilimanjaro"},
                {"value": "lindi", "label": "Lindi"},
                {"value": "manyara", "label": "Manyara"},
                {"value": "mara", "label": "Mara"},
                {"value": "mbeya", "label": "Mbeya"},
                {"value": "morogoro", "label": "Morogoro"},
                {"value": "mtwara", "label": "Mtwara"},
                {"value": "mwanza", "label": "Mwanza"},
                {"value": "njombe", "label": "Njombe"},
                {"value": "pemba-north", "label": "Pemba North"},
                {"value": "pemba-south", "label": "Pemba South"},
                {"value": "pwani", "label": "Pwani"},
                {"value": "rukwa", "label": "Rukwa"},
                {"value": "ruvuma", "label": "Ruvuma"},
                {"value": "shinyanga", "label": "Shinyanga"},
                {"value": "simiyu", "label": "Simiyu"},
                {"value": "singida", "label": "Singida"},
                {"value": "songwe", "label": "Songwe"},
                {"value": "tabora", "label": "Tabora"},
                {"value": "tanga", "label": "Tanga"},
                {"value": "unga-north", "label": "Unguja North"},
                {"value": "unga-south", "label": "Unguja South"},
                {"value": "urban-west", "label": "Urban West (Zanzibar City)"},
            ]
        return None

    @staticmethod
    def get_choice_list(code: str, active_only: bool = True) -> list[dict]:
        """Return a choice list as a list of {value, label} dicts."""
        from apps.system_parameters.models import ChoiceList, ChoiceOption

        cache_key = f"config:choice_list:{code}:active={active_only}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Check dynamic (model-based) choice lists first
        dynamic = ConfigurationService._get_dynamic_choice_list(code)
        if dynamic is not None:
            cache.set(cache_key, dynamic, CACHE_TTL)
            return dynamic

        try:
            cl = ChoiceList.objects.get(code=code, is_active=True)
        except Exception:
            if code in FALLBACK_CHOICE_LISTS:
                return FALLBACK_CHOICE_LISTS[code]
            logger.error("Choice list '%s' not found in database.", code)
            raise ConfigurationError(f"Choice list '{code}' is not configured.")

        qs = ChoiceOption.objects.filter(choice_list=cl)
        if active_only:
            qs = qs.filter(is_active=True)
        qs = qs.order_by("sort_order", "label")

        result = [{"value": o.code, "label": o.label} for o in qs]
        cache.set(cache_key, result, CACHE_TTL)
        return result

    @staticmethod
    def get_choice_options(code: str, active_only: bool = True) -> list:
        """Return raw ChoiceOption queryset evaluated as list."""
        from apps.system_parameters.models import ChoiceList, ChoiceOption

        cache_key = f"config:choice_options:{code}:active={active_only}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            cl = ChoiceList.objects.get(code=code, is_active=True)
        except ChoiceList.DoesNotExist:
            raise ConfigurationError(f"Choice list '{code}' is not configured.")

        qs = ChoiceOption.objects.filter(choice_list=cl)
        if active_only:
            qs = qs.filter(is_active=True)
        qs = qs.order_by("sort_order", "label")
        result = list(qs)
        cache.set(cache_key, result, CACHE_TTL)
        return result

    @staticmethod
    def get_default_choice(code: str) -> str | None:
        """Return the default option code for a choice list, or None."""
        from apps.system_parameters.models import ChoiceList, ChoiceOption

        try:
            cl = ChoiceList.objects.get(code=code, is_active=True)
        except ChoiceList.DoesNotExist:
            return None

        default = ChoiceOption.objects.filter(
            choice_list=cl, is_active=True, is_default=True
        ).first()
        return default.code if default else None

    @staticmethod
    def choice_list_exists(code: str) -> bool:
        from apps.system_parameters.models import ChoiceList
        return ChoiceList.objects.filter(code=code, is_active=True).exists()

    @staticmethod
    def validate_choice(code: str, value: str) -> bool:
        """Check whether a value is valid for a given choice list."""
        from apps.system_parameters.models import ChoiceList, ChoiceOption

        try:
            cl = ChoiceList.objects.get(code=code, is_active=True)
        except ChoiceList.DoesNotExist:
            return False
        return ChoiceOption.objects.filter(
            choice_list=cl, code=value, is_active=True
        ).exists()

    # ------------------------------------------------------------------
    # System Parameter access
    # ------------------------------------------------------------------

    @staticmethod
    def get_parameter(code: str, default=None):
        """Return the value of a system parameter by code."""
        from apps.system_parameters.models import SystemParameter

        cache_key = f"config:parameter:{code}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            param = SystemParameter.objects.get(code=code, is_active=True)
            result = param.value
        except Exception:
            if code in FALLBACK_DEFAULTS:
                result = FALLBACK_DEFAULTS[code]
            else:
                logger.warning("System parameter '%s' not found, returning default=%s", code, default)
                return default

        cache.set(cache_key, result, CACHE_TTL)
        return result

    @staticmethod
    def get_parameter_or_raise(code: str):
        """Return value or raise ConfigurationError."""
        from apps.system_parameters.models import SystemParameter

        try:
            param = SystemParameter.objects.get(code=code, is_active=True)
            return param.value
        except Exception:
            if code in FALLBACK_DEFAULTS:
                return FALLBACK_DEFAULTS[code]
            raise ConfigurationError(f"Required system parameter '{code}' is not configured.")

    @staticmethod
    def get_json_parameter(code: str, default=None) -> dict | list | None:
        """Convenience: get a JSON-typed parameter."""
        val = ConfigurationService.get_parameter(code, default)
        if val is None:
            return default
        return val

    @staticmethod
    def get_int_parameter(code: str, default: int = 0) -> int:
        val = ConfigurationService.get_parameter(code, default)
        return int(val) if val is not None else default

    @staticmethod
    def get_bool_parameter(code: str, default: bool = False) -> bool:
        val = ConfigurationService.get_parameter(code, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        return bool(val) if val is not None else default

    @staticmethod
    def get_str_parameter(code: str, default: str = "") -> str:
        val = ConfigurationService.get_parameter(code, default)
        return str(val) if val is not None else default

    # ------------------------------------------------------------------
    # Cache invalidation
    # ------------------------------------------------------------------

    @staticmethod
    def invalidate_cache(pattern: str | None = None):
        """Invalidate configuration cache.

        If pattern is None, uses a global version counter approach.
        For simplicity, we clear the entire cache.
        """
        cache.clear()
        logger.info("Configuration cache invalidated.")

    @staticmethod
    def invalidate_choice_list(code: str):
        cache_key_active = f"config:choice_list:{code}:active=True"
        cache_key_all = f"config:choice_list:{code}:active=False"
        cache.delete(cache_key_active)
        cache.delete(cache_key_all)
        logger.info("Choice list cache invalidated for '%s'", code)

    @staticmethod
    def invalidate_parameter(code: str):
        cache_key = f"config:parameter:{code}"
        cache.delete(cache_key)
        logger.info("Parameter cache invalidated for '%s'", code)


# Module-level convenience
config = ConfigurationService
