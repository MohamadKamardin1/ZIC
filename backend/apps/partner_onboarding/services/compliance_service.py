import logging

from apps.partner_onboarding.models import PartnerApplication

logger = logging.getLogger(__name__)

RISK_WEIGHTS = {
    "political_risk": {"LOW": 0, "MEDIUM": 10, "HIGH": 25, "PEP": 40},
    "aml_risk": {"LOW": 0, "MEDIUM": 10, "HIGH": 25},
}

HIGH_RISK_THRESHOLDS = {
    "INDIVIDUAL": 50,
    "CORPORATE": 60,
}

HIGH_RISK_INDUSTRIES = [
    "FINANCIAL_SERVICES",
    "OIL_GAS",
    "MINING",
    "CHEMICALS",
    "REAL_ESTATE",
]


class ComplianceService:

    @staticmethod
    def calculate_risk_score(application):
        score = 0

        political_weight = RISK_WEIGHTS["political_risk"].get(
            application.political_risk, 0
        )
        score += political_weight

        aml_weight = RISK_WEIGHTS["aml_risk"].get(
            application.aml_risk, 0
        )
        score += aml_weight

        if application.industry in HIGH_RISK_INDUSTRIES:
            score += 15

        if (
            application.political_risk == "PEP"
            and application.partner_type == "INDIVIDUAL"
        ):
            score += 10

        return min(score, 100)

    @staticmethod
    def flag_high_risk(application):
        score = ComplianceService.calculate_risk_score(application)
        threshold = HIGH_RISK_THRESHOLDS.get(application.partner_type, 50)
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
