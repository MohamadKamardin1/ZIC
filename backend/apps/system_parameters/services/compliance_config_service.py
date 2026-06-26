import logging

from .config_service import ConfigurationService

logger = logging.getLogger(__name__)


class ComplianceConfigService:
    """Configuration-driven compliance rules engine.

    Reads risk weights, thresholds, and high-risk indicators from
    System Parameters. All values are configurable by administrators.
    """

    @staticmethod
    def get_political_risk_weights() -> dict:
        return ConfigurationService.get_json_parameter(
            "RISK_WEIGHTS_POLITICAL",
            {"LOW": 0, "MEDIUM": 10, "HIGH": 25, "PEP": 40},
        )

    @staticmethod
    def get_aml_risk_weights() -> dict:
        return ConfigurationService.get_json_parameter(
            "RISK_WEIGHTS_AML",
            {"LOW": 0, "MEDIUM": 10, "HIGH": 25},
        )

    @staticmethod
    def get_high_risk_thresholds() -> dict:
        return ConfigurationService.get_json_parameter(
            "HIGH_RISK_THRESHOLDS",
            {"INDIVIDUAL": 50, "CORPORATE": 60},
        )

    @staticmethod
    def get_high_risk_industries() -> list:
        return ConfigurationService.get_json_parameter(
            "HIGH_RISK_INDUSTRIES",
            ["FINANCIAL_SERVICES", "OIL_GAS", "MINING", "CHEMICALS", "REAL_ESTATE"],
        )

    @staticmethod
    def get_industry_risk_bonus() -> int:
        return ConfigurationService.get_int_parameter("INDUSTRY_RISK_BONUS", 15)

    @staticmethod
    def get_pep_individual_bonus() -> int:
        return ConfigurationService.get_int_parameter("PEP_INDIVIDUAL_BONUS", 10)

    @staticmethod
    def get_max_risk_score() -> int:
        return ConfigurationService.get_int_parameter("MAX_RISK_SCORE", 100)

    @staticmethod
    def get_risk_threshold_for(partner_type: str) -> int:
        thresholds = ComplianceConfigService.get_high_risk_thresholds()
        return thresholds.get(partner_type, 50)

    @staticmethod
    def calculate_risk_score(application) -> int:
        """Calculate a risk score for an application using configured rules."""
        score = 0

        political_weights = ComplianceConfigService.get_political_risk_weights()
        score += political_weights.get(application.political_risk, 0)

        aml_weights = ComplianceConfigService.get_aml_risk_weights()
        score += aml_weights.get(application.aml_risk, 0)

        high_risk_industries = ComplianceConfigService.get_high_risk_industries()
        if application.industry in high_risk_industries:
            score += ComplianceConfigService.get_industry_risk_bonus()

        if (
            application.political_risk == "PEP"
            and application.partner_type == "INDIVIDUAL"
        ):
            score += ComplianceConfigService.get_pep_individual_bonus()

        max_score = ComplianceConfigService.get_max_risk_score()
        return min(score, max_score)

    @staticmethod
    def is_high_risk(application) -> bool:
        """Determine if an application is high-risk based on configured thresholds."""
        score = ComplianceConfigService.calculate_risk_score(application)
        threshold = ComplianceConfigService.get_risk_threshold_for(
            application.partner_type
        )
        return score >= threshold


compliance_config = ComplianceConfigService
