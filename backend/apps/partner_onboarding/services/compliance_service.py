import logging

from apps.partner_onboarding.models import PartnerApplication
from apps.system_parameters.services.compliance_config_service import (
    ComplianceConfigService,
)

logger = logging.getLogger(__name__)


class ComplianceService:

    @staticmethod
    def calculate_risk_score(application):
        return ComplianceConfigService.calculate_risk_score(application)

    @staticmethod
    def flag_high_risk(application):
        score = ComplianceService.calculate_risk_score(application)
        threshold = ComplianceConfigService.get_risk_threshold_for(
            application.partner_type
        )
        is_high_risk = score >= threshold

        if is_high_risk:
            application.compliance_notes = (
                f"{application.compliance_notes}\n"
                f"[COMPLIANCE] High risk flagged. Score: {score}/100. "
                f"Threshold: {threshold}."
            ).strip()
            application.save(update_fields=["compliance_notes", "updated_at"])
            logger.warning(
                "High risk flagged for application %s: score=%d",
                application.application_number,
                score,
            )

        return {
            "risk_score": score,
            "threshold": threshold,
            "is_high_risk": is_high_risk,
        }
