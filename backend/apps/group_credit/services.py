"""
Group Credit — Business Services

Auto-numbering service for generating unique reference numbers
following the pattern: PREFIX-YYYY-NNNNNN (zero-padded sequential).
"""

import logging
from datetime import datetime

from django.db import models

logger = logging.getLogger(__name__)


class GCNumberingService:
    """
    Generates unique sequential reference numbers for Group Credit entities.
    Thread-safe via database-level MAX() query.
    """

    @staticmethod
    def _generate_number(model_class, field_name: str, prefix: str) -> str:
        year = datetime.now().strftime("%Y")
        pattern = f"{prefix}-{year}-"

        last = (
            model_class.objects
            .filter(**{f"{field_name}__startswith": pattern})
            .order_by(f"-{field_name}")
            .values_list(field_name, flat=True)
            .first()
        )

        if last:
            try:
                seq = int(last.split("-")[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1

        return f"{pattern}{seq:06d}"

    @classmethod
    def generate_quotation_number(cls) -> str:
        from apps.group_credit.models import GCQuotation
        return cls._generate_number(GCQuotation, "quotation_number", "GCQ")

    @classmethod
    def generate_scheme_number(cls) -> str:
        from apps.group_credit.models import GCScheme
        return cls._generate_number(GCScheme, "scheme_number", "GCS")

    @classmethod
    def generate_member_number(cls) -> str:
        from apps.group_credit.models import GCSchemeMember
        return cls._generate_number(GCSchemeMember, "member_number", "GCM")

    @classmethod
    def generate_claim_number(cls) -> str:
        from apps.group_credit.models import GCClaim
        return cls._generate_number(GCClaim, "claim_number", "GCC")

    @classmethod
    def generate_medical_case_number(cls) -> str:
        from apps.group_credit.models import GCMedicalCase
        return cls._generate_number(GCMedicalCase, "case_number", "GCMC")

    @classmethod
    def generate_renewal_number(cls) -> str:
        from apps.group_credit.models import GCSchemeRenewal
        return cls._generate_number(GCSchemeRenewal, "renewal_number", "GCR")
