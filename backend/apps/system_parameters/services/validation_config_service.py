import logging

from .config_service import ConfigurationService

logger = logging.getLogger(__name__)


class ValidationConfigService:
    """Configuration-driven field validation rules.

    Reads required fields, age limits, and other validation rules
    from System Parameters.
    """

    @staticmethod
    def get_minimum_age() -> int:
        return ConfigurationService.get_int_parameter("MINIMUM_AGE", 18)

    @staticmethod
    def get_required_fields(partner_type: str) -> list:
        param_code = f"{partner_type}_REQUIRED_FIELDS"
        return ConfigurationService.get_json_parameter(param_code, [])

    @staticmethod
    def get_individual_required_fields() -> list:
        return ValidationConfigService.get_required_fields("INDIVIDUAL")

    @staticmethod
    def get_corporate_required_fields() -> list:
        return ValidationConfigService.get_required_fields("CORPORATE")

    @staticmethod
    def get_email_uniqueness_statuses() -> list:
        """Return statuses considered 'active' for email uniqueness checks."""
        return ConfigurationService.get_json_parameter(
            "EMAIL_UNIQUENESS_STATUSES",
            ["SUBMITTED", "UNDER_REVIEW", "COMPLIANCE_CHECK", "APPROVED"],
        )


validation_config = ValidationConfigService
