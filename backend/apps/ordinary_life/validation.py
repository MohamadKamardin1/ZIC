from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Sum

from apps.ordinary_life.models import (
    OLBeneficiaryAllocation,
    OLPaymentAllocation,
    OLPaymentObligation,
    OLPremiumInstallment,
    OLPremiumSchedule,
    OLProductVersion,
    OLRateBand,
    validate_policy_beneficiary_total,
)


def validate_product_version(version: OLProductVersion):
    errors = {}
    if version.effective_to and version.effective_to < version.effective_from:
        errors["effective_to"] = "Product version end date cannot precede its effective date."
    if version.min_entry_age > version.max_entry_age:
        errors["max_entry_age"] = "Maximum entry age must be greater than or equal to minimum entry age."
    if version.min_term_years > version.max_term_years:
        errors["max_term_years"] = "Maximum term must be greater than or equal to minimum term."
    if errors:
        raise ValidationError(errors)


def validate_rate_band(rate_band: OLRateBand):
    errors = {}
    if rate_band.min_age > rate_band.max_age:
        errors["max_age"] = "Rate-band maximum age must be greater than or equal to minimum age."
    if rate_band.min_term_years > rate_band.max_term_years:
        errors["max_term_years"] = "Rate-band maximum term must be greater than or equal to minimum term."
    if rate_band.rate < Decimal("0"):
        errors["rate"] = "Rate cannot be negative."
    if errors:
        raise ValidationError(errors)


def validate_payment_obligation(obligation: OLPaymentObligation):
    errors = {}
    if not obligation.proposal_id and not obligation.policy_id:
        errors["policy"] = "A payment obligation must belong to a proposal or policy."
    if obligation.proposal_id and obligation.policy_id:
        errors["policy"] = "A payment obligation cannot belong to both a proposal and policy."
    if obligation.amount <= 0:
        errors["amount"] = "Payment obligation amount must be positive."
    if obligation.allocated_amount < 0 or obligation.allocated_amount > obligation.amount:
        errors["allocated_amount"] = "Allocated amount must be between zero and the obligation amount."
    if errors:
        raise ValidationError(errors)


def validate_payment_allocation(allocation: OLPaymentAllocation):
    if allocation.amount <= 0:
        raise ValidationError({"amount": "Payment allocation amount must be positive."})
    if allocation.obligation_id:
        allocated = allocation.obligation.allocations.exclude(pk=allocation.pk).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        if allocated + allocation.amount > allocation.obligation.amount:
            raise ValidationError({"amount": "Allocations cannot exceed the obligation amount."})
        if allocation.currency != allocation.obligation.currency:
            raise ValidationError({"currency": "Allocation currency must match obligation currency."})


def validate_premium_schedule(schedule: OLPremiumSchedule):
    errors = {}
    if schedule.total_premium <= 0:
        errors["total_premium"] = "Total premium must be positive."
    if schedule.installment_count <= 0:
        errors["installment_count"] = "Installment count must be positive."
    if schedule.effective_to and schedule.effective_to <= schedule.effective_from:
        errors["effective_to"] = "Schedule end date must be after its start date."
    if errors:
        raise ValidationError(errors)


def validate_premium_installment(installment: OLPremiumInstallment):
    errors = {}
    if installment.amount <= 0:
        errors["amount"] = "Installment amount must be positive."
    if installment.allocated_amount < 0 or installment.allocated_amount > installment.amount:
        errors["allocated_amount"] = "Allocated amount must be between zero and the installment amount."
    if errors:
        raise ValidationError(errors)


def validate_beneficiary_allocation(allocation: OLBeneficiaryAllocation):
    allocation.full_clean(exclude=None, validate_unique=False)


def validate_policy_for_issuance(policy):
    validate_policy_beneficiary_total(policy)
    if not policy.product_version_id:
        raise ValidationError("Issued policy must reference a product version.")
    if not policy.product_snapshot:
        raise ValidationError("Issued policy must preserve a product snapshot.")
    if not policy.currency or len(policy.currency) != 3:
        raise ValidationError("Issued policy must have a three-letter currency code.")
    return True


def validate_reference_data():
    errors = []
    active_versions = OLProductVersion.objects.filter(is_active=True)
    if not active_versions.exists():
        errors.append("At least one active Ordinary Life product version is required.")
    for version in active_versions:
        try:
            validate_product_version(version)
        except ValidationError as exc:
            errors.append(f"{version}: {exc}")
        rate_bands = OLRateBand.objects.filter(product_version=version, is_active=True)
        if not rate_bands.exists():
            errors.append(f"{version}: at least one active rate band is required.")
        for band in rate_bands:
            try:
                validate_rate_band(band)
            except ValidationError as exc:
                errors.append(f"{band}: {exc}")
    if errors:
        raise ValidationError(errors)
    return True
