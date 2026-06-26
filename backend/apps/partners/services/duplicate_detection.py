import logging

from django.db.models import Q

from apps.partners.models import Partner
from apps.partner_onboarding.models import PartnerApplication

logger = logging.getLogger(__name__)


class DuplicateCheckResult:
    def __init__(self, is_duplicate=False, matches=None, details=None):
        self.is_duplicate = is_duplicate
        self.matches = matches or []
        self.details = details or {}


class PartnerDuplicateDetectionService:
    CRITERIA_WEIGHTS = {
        "email": 1.0,
        "identification": 0.95,
        "mobile": 0.9,
        "tin": 0.95,
        "company_registration": 0.85,
    }

    @classmethod
    def check_against_partners(cls, partner_type, **fields):
        query = Q()
        reasons = []

        email = fields.get("email")
        if email:
            query |= Q(email__iexact=email)
            reasons.append("email")

        identification_number = fields.get("identification_number")
        if identification_number:
            query |= Q(
                identification_number__iexact=identification_number,
                identification_number__gt="",
            )
            reasons.append("identification")

        mobile = fields.get("mobile_number")
        if mobile:
            query |= Q(mobile_number=mobile)
            reasons.append("mobile")

        tin = fields.get("tin_number")
        if tin:
            query |= Q(tin_number__iexact=tin, tin_number__gt="")
            reasons.append("tin")

        if not query:
            return DuplicateCheckResult()

        matches = Partner.objects.filter(query)
        if matches.exists():
            return DuplicateCheckResult(
                is_duplicate=True,
                matches=list(matches),
                details={"matched_on": reasons, "count": matches.count()},
            )
        return DuplicateCheckResult()

    @classmethod
    def check_against_active_applications(cls, **fields):
        query = Q()
        reasons = []

        email = fields.get("email")
        if email:
            query |= Q(email__iexact=email)
            reasons.append("email")

        identification_number = fields.get("identification_number")
        if identification_number:
            query |= Q(
                identification_number__iexact=identification_number,
                identification_number__gt="",
            )
            reasons.append("identification")

        mobile = fields.get("mobile_number")
        if mobile:
            query |= Q(mobile_number=mobile)
            reasons.append("mobile")

        if not query:
            return DuplicateCheckResult()

        active_statuses = ["SUBMITTED", "UNDER_REVIEW", "COMPLIANCE_CHECK", "APPROVED"]
        matches = PartnerApplication.objects.filter(query, status__in=active_statuses)
        if matches.exists():
            return DuplicateCheckResult(
                is_duplicate=True,
                matches=list(matches),
                details={"matched_on": reasons, "count": matches.count()},
            )
        return DuplicateCheckResult()

    @classmethod
    def comprehensive_check(cls, partner_type, exclude_partner_id=None, **fields):
        partner_result = cls.check_against_partners(partner_type, **fields)
        application_result = cls.check_against_active_applications(**fields)

        all_matches = partner_result.matches + application_result.matches
        all_reasons = list(
            set(
                partner_result.details.get("matched_on", [])
                + application_result.details.get("matched_on", [])
            )
        )

        if exclude_partner_id:
            all_matches = [m for m in all_matches if getattr(m, "id", None) != exclude_partner_id]

        return DuplicateCheckResult(
            is_duplicate=len(all_matches) > 0,
            matches=all_matches,
            details={"matched_on": all_reasons, "count": len(all_matches)},
        )
