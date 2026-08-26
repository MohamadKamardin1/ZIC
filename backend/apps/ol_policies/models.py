import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.common.models import AuditedModel, TimeStampedModel, UUIDModel

POLICY_DOC_REF = "docs/OL_POLICIES_DESIGN.md"


class PolicyStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    LAPSED = "LAPSED", "Lapsed"
    PAID_UP = "PAID_UP", "Paid-up"
    SURRENDER_PENDING = "SURRENDER_PENDING", "Surrender pending"
    SURRENDERED = "SURRENDERED", "Surrendered"
    MATURED_PENDING_PAYMENT = "MATURED_PENDING_PAYMENT", "Matured pending payment"
    MATURED = "MATURED", "Matured"
    EXPIRED = "EXPIRED", "Expired"
    CANCELLED = "CANCELLED", "Cancelled"
    CLAIM_SETTLED = "CLAIM_SETTLED", "Claim settled"
    TERMINATED = "TERMINATED", "Terminated"


class EndorsementType(models.TextChoices):
    PREMIUM_CHANGE = "PREMIUM_CHANGE", "Premium change"
    TERM_CHANGE = "TERM_CHANGE", "Term change"
    MEMBER_ADD = "MEMBER_ADD", "Member add"
    MEMBER_REMOVE = "MEMBER_REMOVE", "Member remove"
    BENEFICIARY_CHANGE = "BENEFICIARY_CHANGE", "Beneficiary change"
    ADDRESS_CHANGE = "ADDRESS_CHANGE", "Address change"
    CHANGE_BENEFIT = "CHANGE_BENEFIT", "Change benefit"
    SURRENDER = "SURRENDER", "Surrender"
    OTHER = "OTHER", "Other"


class EndorsementStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PENDING_APPROVAL = "PENDING_APPROVAL", "Pending approval"
    APPROVED = "APPROVED", "Approved"
    APPLIED = "APPLIED", "Applied"
    DECLINED = "DECLINED", "Declined"
    CANCELLED = "CANCELLED", "Cancelled"


class PolicySourceChannel(models.TextChoices):
    WEB = "WEB", "Web"
    API = "API", "API"
    ADMIN = "ADMIN", "Admin"
    SYSTEM = "SYSTEM", "System"
    BATCH = "BATCH", "Batch"
    PORTAL = "PORTAL", "Portal"
    IMPORT = "IMPORT", "Import"


def generate_policy_number():
    """Generate a collision-resistant policy number when issuance has no rule yet."""
    return f"POL-{timezone.localdate():%Y%m%d}-{uuid.uuid4().hex[:10].upper()}"


def generate_endorsement_number():
    return f"END-{timezone.localdate():%Y%m%d}-{uuid.uuid4().hex[:10].upper()}"


class Policy(UUIDModel, AuditedModel):
    """The definitive issued OL contract snapshot used for servicing.

    References to proposal and partner records provide traceability, while the
    contract fields and optional ``contract_snapshot`` preserve the terms agreed
    at issuance even if upstream records later change.
    """

    policy_number = models.CharField(max_length=40, unique=True, db_index=True, blank=True)
    proposal_ref = models.OneToOneField(
        "ol_proposals.OLProposal",
        on_delete=models.PROTECT,
        related_name="issued_policy_snapshot",
        db_column="proposal_ref_id",
    )
    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="ol_policyholders",
    )
    agent = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        related_name="ol_policy_agents",
        null=True,
        blank=True,
    )
    product_plan_ref = models.CharField(
        max_length=160,
        help_text="Immutable product/plan code or reference captured at issuance.",
    )
    currency = models.CharField(max_length=3, default="TZS")
    sum_assured = models.DecimalField(max_digits=18, decimal_places=2)
    premium_amount = models.DecimalField(max_digits=18, decimal_places=2)
    premium_frequency = models.CharField(max_length=30)
    term_years = models.PositiveIntegerField()
    risk_commencement_date = models.DateField()
    maturity_date = models.DateField()
    status = models.CharField(
        max_length=35,
        choices=PolicyStatus.choices,
        default=PolicyStatus.ACTIVE,
        db_index=True,
    )
    first_premium_receipt_ref = models.CharField(max_length=160, blank=True, default="")
    contract_snapshot = models.JSONField(default=dict, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "ol_policies_policy"
        ordering = ["-created_at", "policy_number"]
        indexes = [
            models.Index(fields=["status", "maturity_date"], name="ol_policy_status_maturity_idx"),
            models.Index(fields=["partner", "status"], name="ol_policy_partner_status_idx"),
            models.Index(fields=["agent", "status"], name="ol_policy_agent_status_idx"),
            models.Index(fields=["currency", "status"], name="ol_policy_currency_status_idx"),
        ]

    def __str__(self):
        return self.policy_number or "Unnumbered policy"

    def clean(self):
        errors = {}
        if self.sum_assured is not None and self.sum_assured <= 0:
            errors["sum_assured"] = "Sum assured must be greater than zero."
        if self.premium_amount is not None and self.premium_amount <= 0:
            errors["premium_amount"] = "Premium amount must be greater than zero."
        if self.term_years is not None and self.term_years <= 0:
            errors["term_years"] = "Term must be at least one year."
        if self.risk_commencement_date and self.maturity_date:
            if self.maturity_date <= self.risk_commencement_date:
                errors["maturity_date"] = "Maturity date must be after risk commencement date."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.policy_number:
            self.policy_number = generate_policy_number()
        super().save(*args, **kwargs)


class PolicyMember(UUIDModel, AuditedModel):
    policy = models.ForeignKey(Policy, on_delete=models.PROTECT, related_name="members")
    member_relation = models.CharField(max_length=80)
    name = models.CharField(max_length=255)
    dob = models.DateField()
    gender = models.CharField(max_length=30)
    benefit_amount = models.DecimalField(max_digits=18, decimal_places=2)
    is_active = models.BooleanField(default=True, db_index=True)
    ended_at = models.DateField(null=True, blank=True)
    class Meta:
        db_table = "ol_policies_policy_member"
        ordering = ["name", "created_at"]
        indexes = [
            models.Index(fields=["policy", "member_relation"], name="ol_policy_member_relation_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.member_relation})"


class PolicyRider(UUIDModel, AuditedModel):
    policy = models.ForeignKey(Policy, on_delete=models.PROTECT, related_name="riders")
    rider_code = models.CharField(max_length=100)
    sum_assured = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    premium = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        db_table = "ol_policies_policy_rider"
        ordering = ["rider_code", "created_at"]
        indexes = [models.Index(fields=["policy", "rider_code"], name="ol_policy_rider_code_idx")]

    def __str__(self):
        return self.rider_code


class PolicyBenefit(UUIDModel, AuditedModel):
    policy = models.ForeignKey(Policy, on_delete=models.PROTECT, related_name="benefits")
    benefit_type = models.CharField(max_length=100)
    calculation_basis = models.CharField(max_length=40)
    amount = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        db_table = "ol_policies_policy_benefit"
        ordering = ["benefit_type", "created_at"]
        indexes = [models.Index(fields=["policy", "benefit_type"], name="ol_policy_benefit_type_idx")]

    def __str__(self):
        return f"{self.benefit_type} ({self.calculation_basis})"


class PolicyEndorsement(UUIDModel, AuditedModel):
    policy = models.ForeignKey(Policy, on_delete=models.PROTECT, related_name="endorsements")
    endorsement_number = models.CharField(max_length=45, unique=True, db_index=True, blank=True)
    endorsement_type = models.CharField(max_length=40, choices=EndorsementType.choices)
    effective_date = models.DateField()
    description = models.TextField()
    status = models.CharField(
        max_length=25,
        choices=EndorsementStatus.choices,
        default=EndorsementStatus.DRAFT,
        db_index=True,
    )
    before_snapshot = models.JSONField(default=dict, blank=True)
    after_snapshot = models.JSONField(default=dict, blank=True)
    reason = models.TextField(blank=True, default="")
    source_channel = models.CharField(
        max_length=20,
        choices=PolicySourceChannel.choices,
        default=PolicySourceChannel.API,
    )

    class Meta:
        db_table = "ol_policies_policy_endorsement"
        ordering = ["-effective_date", "-created_at"]
        indexes = [
            models.Index(fields=["policy", "status"], name="ol_pol_endorse_st_idx"),
        ]

    def __str__(self):
        return self.endorsement_number or "Unnumbered endorsement"

    def save(self, *args, **kwargs):
        if not self.endorsement_number:
            self.endorsement_number = generate_endorsement_number()
        super().save(*args, **kwargs)


class PolicyAuditLog(UUIDModel, TimeStampedModel):
    """Immutable, queryable policy state-change and material-change audit row."""

    policy = models.ForeignKey(Policy, on_delete=models.PROTECT, related_name="audit_logs")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ol_policy_audit_actions",
    )
    event_type = models.CharField(max_length=100, db_index=True)
    from_status = models.CharField(max_length=35, blank=True, default="")
    to_status = models.CharField(max_length=35, blank=True, default="")
    before_snapshot = models.JSONField(default=dict, blank=True)
    after_snapshot = models.JSONField(default=dict, blank=True)
    reason = models.TextField(blank=True, default="")
    source_channel = models.CharField(
        max_length=20,
        choices=PolicySourceChannel.choices,
        default=PolicySourceChannel.SYSTEM,
    )
    correlation_id = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        db_table = "ol_policies_policy_audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["policy", "created_at"], name="ol_pol_audit_pol_ct_idx"),
            models.Index(fields=["event_type", "created_at"], name="ol_pol_audit_evt_ct_idx"),
        ]

    def __str__(self):
        return f"{self.policy.policy_number}: {self.event_type}"
