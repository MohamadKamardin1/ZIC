"""
Group Life — Business Services

Auto-numbering service for generating unique reference numbers
following the pattern: PREFIX-YYYY-NNNNNN (zero-padded sequential).
"""

import logging
from datetime import datetime

from django.db import models

logger = logging.getLogger(__name__)


class GLNumberingService:
    """
    Generates unique sequential reference numbers for Group Life entities.
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
        from apps.group_life.models import GLQuotation
        return cls._generate_number(GLQuotation, "quotation_number", "GLQ")

    @classmethod
    def generate_scheme_number(cls) -> str:
        from apps.group_life.models import GLScheme
        return cls._generate_number(GLScheme, "scheme_number", "GLS")

    @classmethod
    def generate_member_number(cls) -> str:
        from apps.group_life.models import GLSchemeMember
        return cls._generate_number(GLSchemeMember, "member_number", "GLM")

    @classmethod
    def generate_claim_number(cls) -> str:
        from apps.group_life.models import GLClaim
        return cls._generate_number(GLClaim, "claim_number", "GLC")

    @classmethod
    def generate_medical_case_number(cls) -> str:
        from apps.group_life.models import GLMedicalCase
        return cls._generate_number(GLMedicalCase, "case_number", "GLMC")

    @classmethod
    def generate_renewal_number(cls) -> str:
        from apps.group_life.models import GLSchemeRenewal
        return cls._generate_number(GLSchemeRenewal, "renewal_number", "GLR")
