"""
Group Credit — Business Services

Auto-numbering service for generating unique reference numbers
following the pattern: PREFIX-YYYY-NNNNNN (zero-padded sequential).
"""

import logging
from datetime import datetime
from decimal import Decimal

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


def _windows_overlap(from_a, to_a, from_b, to_b):
    """Return True when two (possibly open-ended) date windows overlap."""

    # A None bound means the window is open-ended in that direction.
    if from_a is None and to_a is None:
        return True
    if from_b is None and to_b is None:
        return True
    if from_a is None and from_b is None:
        return True
    if to_a is not None and from_b is not None and to_a < from_b:
        return False
    if to_b is not None and from_a is not None and to_b < from_a:
        return False
    return True


class SchemeRateValidator:
    """Ensures premium-rate effective windows do not overlap for a scheme scope."""

    @classmethod
    def validate(
        cls,
        *,
        scheme_type_id,
        product_id=None,
        rate_type=None,
        effective_from=None,
        effective_to=None,
        exclude_id=None,
    ):
        from apps.group_credit.models import GCSchemePremiumRate

        queryset = GCSchemePremiumRate.objects.filter(scheme_type_id=scheme_type_id)
        if product_id:
            queryset = queryset.filter(product_ref_id=product_id)
        if rate_type:
            queryset = queryset.filter(rate_type=rate_type)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)

        for existing in queryset:
            if _windows_overlap(effective_from, effective_to, existing.effective_from, existing.effective_to):
                from apps.group_credit.errors import scheme_rate_overlap

                raise scheme_rate_overlap(
                    details={
                        "scheme_type_id": str(scheme_type_id),
                        "conflicting_rate_id": str(existing.id),
                        "conflicting_window": {
                            "effective_from": existing.effective_from.isoformat() if existing.effective_from else None,
                            "effective_to": existing.effective_to.isoformat() if existing.effective_to else None,
                        },
                    }
                )
        return True


class ProductValidator:
    """Ensures a product's entry-age band and free-cover limit are consistent."""

    @classmethod
    def validate(
        cls,
        *,
        min_entry_age=None,
        max_entry_age=None,
        free_cover_limit=None,
        max_loan_amount=None,
    ):
        from apps.group_credit.errors import product_invalid_limits

        def _to_decimal(value):
            if value is None:
                return None
            return Decimal(value) if not isinstance(value, Decimal) else value

        problems = []
        if min_entry_age is not None and max_entry_age is not None and min_entry_age > max_entry_age:
            problems.append("min_entry_age must not exceed max_entry_age.")
        free_cover = _to_decimal(free_cover_limit)
        max_loan = _to_decimal(max_loan_amount)
        if free_cover is not None and free_cover < 0:
            problems.append("free_cover_limit cannot be negative.")
        if free_cover is not None and max_loan is not None and free_cover > max_loan:
            problems.append("free_cover_limit must not exceed max_loan_amount.")
        if problems:
            raise product_invalid_limits(details={"problems": problems})
        return True


class ClaimTypeValidator:
    """Ensures duplicate active claim types are not created."""

    @classmethod
    def validate(cls, *, name=None, code=None, category=None, exclude_id=None):
        from apps.group_credit.models import GCClaimType

        if not name:
            return True
        queryset = GCClaimType.objects.filter(is_active=True, name__iexact=name.strip())
        if category:
            queryset = queryset.filter(category=category)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)

        existing = queryset.first()
        if existing is not None:
            from apps.group_credit.errors import claim_type_duplicate

            raise claim_type_duplicate(
                details={
                    "duplicate_id": str(existing.id),
                    "name": existing.name,
                    "category": existing.category,
                }
            )
        return True
