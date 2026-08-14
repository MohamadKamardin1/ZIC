import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

# =============================================================================
# OL LOOKUP VALUE (Dropdown Configuration)
# =============================================================================

class OLLookupValue(models.Model):
    """
    Global configuration table for all dynamic dropdowns in the Ordinary Life module.
    Replaces hardcoded choices=() tuples.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=50, db_index=True, help_text=_("The dropdown parameter category (e.g., POLICY_STATUS)."))
    value = models.CharField(max_length=50, help_text=_("The stored value in the database."))
    label = models.CharField(max_length=100, help_text=_("The human-readable label displayed in the UI."))
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_lookup_value"
        ordering = ["category", "sort_order", "label"]
        unique_together = ("category", "value")

    def __str__(self):
        return f"{self.category} - {self.label}"


# =============================================================================
# OL DEFAULT SETUPS
# =============================================================================

class OLDefaultSystemParameter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_default_system_parameter"


class OLOverrideCommissionSetup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role_name = models.CharField(max_length=100)
    override_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage of base commission")
    effective_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_override_commission_setup"


class OLComputationApproach(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_computation_approach"


class OLMaturityClaimSetup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    notification_days_prior = models.PositiveIntegerField(help_text="Days prior to maturity to notify")
    requires_discharge_voucher = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_maturity_claim_setup"


# =============================================================================
# OL POLICY SETUP
# =============================================================================

class OLAnticipatedEndowmentInstallmentRate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy_year = models.PositiveIntegerField()
    percentage_payout = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_anticipated_endowment_rate"


class OLGracePeriod(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    days = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_grace_period"


class OLPolicyStatus(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    is_terminal = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_policy_status"


class OLPolicyRenewalStatus(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_policy_renewal_status"


class OLBeneficiaryType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_beneficiary_type"


class OLMemberCoverConfiguration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    max_dependents = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_member_cover_configuration"


class OLSurrenderSetup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    min_years_in_force = models.PositiveIntegerField()
    penalty_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_surrender_setup"


class OLPaidUpSetup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    min_years_in_force = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_paid_up_setup"


class OLSurrenderValueRate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy_year = models.PositiveIntegerField()
    rate_factor = models.DecimalField(max_digits=8, decimal_places=5)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_surrender_value_rate"


class OLPaidUpRate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy_year = models.PositiveIntegerField()
    rate_factor = models.DecimalField(max_digits=8, decimal_places=5)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_paid_up_rate"


class OLCommitmentStatus(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_commitment_status"


class OLHealthQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    question_text = models.TextField()
    category = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_health_question"


class OLHealthQuestionnaire(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    version = models.CharField(max_length=20, default="1.0")
    effective_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_health_questionnaire"


class OLGracePeriodNotificationSchedule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    days_past_due = models.PositiveIntegerField()
    notification_type = models.CharField(max_length=50) # e.g. SMS, EMAIL
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_grace_period_notification_schedule"


class OLReinstatementWindow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    max_months = models.PositiveIntegerField(help_text="Max months after lapse to allow reinstatement")
    requires_medical = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_reinstatement_window"

# =============================================================================
# OL OPERATIONAL CORE MODELS
# =============================================================================

class OLProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    business_area = models.CharField(max_length=50, default="ORDINARY_LIFE")
    min_age = models.PositiveIntegerField(null=True, blank=True)
    max_age = models.PositiveIntegerField(null=True, blank=True)
    term_length_years = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_product"
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class OLClient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner = models.ForeignKey(
        "partners.Partner", on_delete=models.PROTECT, related_name="ordinary_life_legacy_clients",
        null=True, blank=True,
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=20, null=True, blank=True)
    id_number = models.CharField(max_length=100, unique=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_client"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.id_number})"


class OLQuotation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quotation_number = models.CharField(max_length=100, unique=True)
    client = models.ForeignKey(OLClient, on_delete=models.CASCADE, related_name="quotations")
    partner = models.ForeignKey(
        "partners.Partner", on_delete=models.PROTECT, related_name="ordinary_life_quotations",
        null=True, blank=True,
    )
    product = models.ForeignKey(OLProduct, on_delete=models.CASCADE, related_name="quotations")
    product_version = models.ForeignKey(
        "OLProductVersion", on_delete=models.PROTECT, related_name="quotations",
        null=True, blank=True,
    )
    current_version = models.ForeignKey(
        "OLQuotationVersion", on_delete=models.PROTECT, related_name="current_for_quotations",
        null=True, blank=True,
    )
    sum_assured = models.DecimalField(max_digits=12, decimal_places=2)
    premium_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="TZS")
    payment_frequency = models.CharField(max_length=30, default="ANNUAL")
    expires_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, default="DRAFT") # DRAFT, SUBMITTED, EXPIRED, CONVERTED
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_quotation"
        ordering = ["-created_at"]

    def __str__(self):
        return self.quotation_number


class OLProposal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal_number = models.CharField(max_length=100, unique=True)
    quotation = models.OneToOneField(OLQuotation, on_delete=models.CASCADE, related_name="proposal")
    quotation_version = models.ForeignKey(
        "OLQuotationVersion", on_delete=models.PROTECT, related_name="proposals",
        null=True, blank=True,
    )
    underwriting_status = models.CharField(max_length=50, default="PENDING")
    medical_required = models.BooleanField(default=False)
    status = models.CharField(max_length=50, default="PENDING") # PENDING, APPROVED, DECLINED
    payment_required_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    payment_currency = models.CharField(max_length=3, default="TZS")
    approved_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_proposal"
        ordering = ["-created_at"]

    def __str__(self):
        return self.proposal_number


class OLCommitment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commitment_number = models.CharField(max_length=100, unique=True)
    proposal = models.ForeignKey(OLProposal, on_delete=models.CASCADE, related_name="commitments")
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=50, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_commitment"
        ordering = ["-created_at"]

    def __str__(self):
        return self.commitment_number


class OLPolicy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy_number = models.CharField(max_length=100, unique=True)
    proposal = models.OneToOneField(OLProposal, on_delete=models.CASCADE, related_name="policy")
    product_version = models.ForeignKey(
        "OLProductVersion", on_delete=models.PROTECT, related_name="policies",
        null=True, blank=True,
    )
    product_snapshot = models.JSONField(default=dict, blank=True)
    policyholder_partner = models.ForeignKey(
        "partners.Partner", on_delete=models.PROTECT, related_name="ordinary_life_policyholders",
        null=True, blank=True,
    )
    life_assured_partner = models.ForeignKey(
        "partners.Partner", on_delete=models.PROTECT, related_name="ordinary_life_assured_policies",
        null=True, blank=True,
    )
    version = models.PositiveIntegerField(default=1)
    policyholder = models.ForeignKey(
        "OLClient", on_delete=models.PROTECT, related_name="policyholder_policies",
        null=True, blank=True,
    )
    life_assured = models.ForeignKey(
        "OLClient", on_delete=models.PROTECT, related_name="life_assured_policies",
        null=True, blank=True,
    )
    agent = models.ForeignKey(
        "partners.Partner", on_delete=models.PROTECT, related_name="ordinary_life_policies",
        null=True, blank=True,
    )
    currency = models.CharField(max_length=3, default="TZS")
    sum_assured = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    premium_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=50, default="ACTIVE") # ACTIVE, LAPSED, SURRENDERED, MATURED, CANCELLED
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_policy"
        ordering = ["-created_at"]

    def __str__(self):
        return self.policy_number


class OLLoan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loan_number = models.CharField(max_length=100, unique=True)
    policy = models.ForeignKey(OLPolicy, on_delete=models.CASCADE, related_name="loans")
    loan_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    outstanding_balance = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=50, default="PENDING") # PENDING, APPROVED, REPAID
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_loan"
        ordering = ["-created_at"]

    def __str__(self):
        return self.loan_number


class OLWithdrawal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    withdrawal_number = models.CharField(max_length=100, unique=True)
    policy = models.ForeignKey(OLPolicy, on_delete=models.CASCADE, related_name="withdrawals")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    withdrawal_type = models.CharField(max_length=50) # PARTIAL, FULL_SURRENDER
    status = models.CharField(max_length=50, default="PENDING") # PENDING, PAID
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_withdrawal"
        ordering = ["-created_at"]

    def __str__(self):
        return self.withdrawal_number


class OLClaim(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim_number = models.CharField(max_length=100, unique=True)
    policy = models.ForeignKey(OLPolicy, on_delete=models.CASCADE, related_name="claims")
    date_of_event = models.DateField()
    cause = models.CharField(max_length=255)
    claim_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=50, default="REPORTED") # REPORTED, INVESTIGATING, APPROVED, PAID, REJECTED
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_claim"
        ordering = ["-created_at"]

    def __str__(self):
        return self.claim_number


class OLMaturityInstallment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    installment_number = models.CharField(max_length=100, unique=True)
    policy = models.ForeignKey(OLPolicy, on_delete=models.CASCADE, related_name="maturity_installments")
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=50, default="PENDING") # PENDING, PAID
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_maturity_installment"
        ordering = ["-created_at"]

    def __str__(self):
        return self.installment_number



class OLBeneficiary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(OLPolicy, on_delete=models.CASCADE, related_name="beneficiaries")
    beneficiary_type = models.ForeignKey(
        OLBeneficiaryType, on_delete=models.PROTECT, related_name="ordinary_life_beneficiaries",
        null=True, blank=True,
    )
    name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=100)
    id_number = models.CharField(max_length=100, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_beneficiary"
        ordering = ["name"]


class OLWorkflowEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_type = models.CharField(max_length=50, db_index=True)
    entity_id = models.UUIDField(db_index=True)
    action = models.CharField(max_length=80)
    previous_status = models.CharField(max_length=50, blank=True)
    new_status = models.CharField(max_length=50, blank=True)
    reason = models.TextField(blank=True)
    actor = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ordinary_life_workflow_events",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ol_workflow_event"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["entity_type", "entity_id", "created_at"])]

    def __str__(self):
        return f"{self.entity_type}:{self.entity_id}:{self.action}"


# =============================================================================
# PHASE 3: VERSIONED PRODUCT, APPLICATION, UNDERWRITING, PAYMENT, AND POLICY
# DOMAIN MODELS
# =============================================================================


class OLProductVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(OLProduct, on_delete=models.PROTECT, related_name="versions")
    version_number = models.PositiveIntegerField()
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="TZS")
    min_entry_age = models.PositiveIntegerField(default=18)
    max_entry_age = models.PositiveIntegerField(default=65)
    min_term_years = models.PositiveIntegerField(default=1)
    max_term_years = models.PositiveIntegerField(default=30)
    payment_frequencies = models.JSONField(default=list)
    calculation_approach = models.ForeignKey(
        OLComputationApproach, on_delete=models.PROTECT,
        related_name="product_versions", null=True, blank=True,
    )
    underwriting_rules = models.JSONField(default=dict, blank=True)
    servicing_rules = models.JSONField(default=dict, blank=True)
    snapshot = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_product_version"
        ordering = ["product", "-version_number"]
        constraints = [
            models.UniqueConstraint(fields=["product", "version_number"], name="ol_product_version_unique_number"),
            models.CheckConstraint(
                check=Q(effective_to__isnull=True) | Q(effective_to__gt=F("effective_from")),
                name="ol_product_version_valid_dates",
            ),
            models.CheckConstraint(
                check=Q(min_entry_age__lte=F("max_entry_age")),
                name="ol_product_version_valid_ages",
            ),
            models.CheckConstraint(
                check=Q(min_term_years__lte=F("max_term_years")) & Q(min_term_years__gt=0),
                name="ol_product_version_valid_terms",
            ),
        ]
        indexes = [
            models.Index(fields=["product", "effective_from", "effective_to"]),
            models.Index(fields=["is_active", "currency"]),
        ]

    def __str__(self):
        return f"{self.product.code} v{self.version_number}"


class OLPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_version = models.ForeignKey(OLProductVersion, on_delete=models.PROTECT, related_name="plans")
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    minimum_sum_assured = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    maximum_sum_assured = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_plan"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["product_version", "code"], name="ol_plan_unique_code_per_version"),
            models.CheckConstraint(
                check=Q(minimum_sum_assured__isnull=True)
                | Q(maximum_sum_assured__isnull=True)
                | Q(minimum_sum_assured__lte=F("maximum_sum_assured")),
                name="ol_plan_valid_sum_assured_range",
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class OLBenefit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    benefit_type = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_benefit"
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class OLProductBenefit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_version = models.ForeignKey(OLProductVersion, on_delete=models.PROTECT, related_name="benefits")
    benefit = models.ForeignKey(OLBenefit, on_delete=models.PROTECT, related_name="product_versions")
    is_mandatory = models.BooleanField(default=False)
    minimum_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    maximum_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    rules = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_product_benefit"
        constraints = [
            models.UniqueConstraint(fields=["product_version", "benefit"], name="ol_product_benefit_unique"),
            models.CheckConstraint(
                check=Q(minimum_amount__isnull=True)
                | Q(maximum_amount__isnull=True)
                | Q(minimum_amount__lte=F("maximum_amount")),
                name="ol_product_benefit_valid_amount_range",
            ),
        ]


class OLRider(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    eligibility_rules = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_rider"
        ordering = ["name"]


class OLProductRider(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_version = models.ForeignKey(OLProductVersion, on_delete=models.PROTECT, related_name="riders")
    rider = models.ForeignKey(OLRider, on_delete=models.PROTECT, related_name="product_versions")
    is_mandatory = models.BooleanField(default=False)
    premium_rate = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    rules = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_product_rider"
        constraints = [
            models.UniqueConstraint(fields=["product_version", "rider"], name="ol_product_rider_unique"),
            models.CheckConstraint(
                check=Q(premium_rate__isnull=True) | Q(premium_rate__gte=0),
                name="ol_product_rider_nonnegative_rate",
            ),
        ]


class OLRateBand(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_version = models.ForeignKey(OLProductVersion, on_delete=models.PROTECT, related_name="rate_bands")
    plan = models.ForeignKey(OLPlan, on_delete=models.PROTECT, related_name="rate_bands", null=True, blank=True)
    min_age = models.PositiveIntegerField()
    max_age = models.PositiveIntegerField()
    min_term_years = models.PositiveIntegerField()
    max_term_years = models.PositiveIntegerField()
    rate = models.DecimalField(max_digits=12, decimal_places=8)
    assumptions = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_rate_band"
        constraints = [
            models.CheckConstraint(check=Q(min_age__lte=F("max_age")), name="ol_rate_band_valid_ages"),
            models.CheckConstraint(check=Q(min_term_years__lte=F("max_term_years")), name="ol_rate_band_valid_terms"),
            models.CheckConstraint(check=Q(rate__gte=0), name="ol_rate_band_nonnegative_rate"),
        ]
        indexes = [models.Index(fields=["product_version", "min_age", "max_age"])]


class OLApplication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application_number = models.CharField(max_length=100, unique=True)
    proposal = models.OneToOneField(OLProposal, on_delete=models.PROTECT, related_name="application", null=True, blank=True)
    partner = models.ForeignKey("partners.Partner", on_delete=models.PROTECT, related_name="ordinary_life_applications")
    policyholder = models.ForeignKey("partners.Partner", on_delete=models.PROTECT, related_name="ordinary_life_policyholder_applications")
    life_assured = models.ForeignKey("partners.Partner", on_delete=models.PROTECT, related_name="ordinary_life_life_assured_applications")
    payer = models.ForeignKey("partners.Partner", on_delete=models.PROTECT, related_name="ordinary_life_payer_applications", null=True, blank=True)
    declarations = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=40, default="DRAFT")
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_application"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["partner", "status"]),
            models.Index(fields=["application_number"]),
        ]


class OLPartyRole(models.Model):
    ROLE_CHOICES = (
        ("POLICYHOLDER", "Policyholder"),
        ("LIFE_ASSURED", "Life assured"),
        ("PAYER", "Payer"),
        ("BENEFICIARY", "Beneficiary"),
        ("EMPLOYER", "Employer"),
        ("INTERMEDIARY", "Intermediary"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(OLApplication, on_delete=models.CASCADE, related_name="party_roles", null=True, blank=True)
    policy = models.ForeignKey("OLPolicy", on_delete=models.CASCADE, related_name="party_roles", null=True, blank=True)
    partner = models.ForeignKey("partners.Partner", on_delete=models.PROTECT, related_name="ordinary_life_party_roles")
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    is_primary = models.BooleanField(default=False)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    identity_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ol_party_role"
        constraints = [
            models.CheckConstraint(
                check=Q(application__isnull=False) | Q(policy__isnull=False),
                name="ol_party_role_has_parent",
            ),
            models.CheckConstraint(
                check=Q(effective_to__isnull=True) | Q(effective_from__isnull=True) | Q(effective_to__gte=F("effective_from")),
                name="ol_party_role_valid_dates",
            ),
            models.UniqueConstraint(
                fields=["application", "role"], condition=Q(is_primary=True), name="ol_party_role_one_primary_application",
            ),
            models.UniqueConstraint(
                fields=["policy", "role"], condition=Q(is_primary=True), name="ol_party_role_one_primary_policy",
            ),
        ]
        indexes = [models.Index(fields=["partner", "role"])]


class OLQuotationVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quotation = models.ForeignKey(OLQuotation, on_delete=models.PROTECT, related_name="versions")
    version_number = models.PositiveIntegerField()
    product_version = models.ForeignKey(OLProductVersion, on_delete=models.PROTECT, related_name="quotation_versions")
    inputs = models.JSONField(default=dict)
    calculated_outputs = models.JSONField(default=dict)
    product_version_snapshot = models.JSONField(default=dict)
    calculation_hash = models.CharField(max_length=128)
    calculated_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="ordinary_life_quotation_versions")

    class Meta:
        db_table = "ol_quotation_version"
        ordering = ["quotation", "-version_number"]
        constraints = [
            models.UniqueConstraint(fields=["quotation", "version_number"], name="ol_quotation_version_unique_number"),
            models.UniqueConstraint(fields=["quotation", "calculation_hash"], name="ol_quotation_version_unique_hash"),
        ]
        indexes = [models.Index(fields=["calculation_hash"])]


class OLUnderwritingCase(models.Model):
    DECISION_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REFERRED", "Referred"),
        ("DECLINED", "Declined"),
        ("POSTPONED", "Postponed"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.OneToOneField(OLProposal, on_delete=models.PROTECT, related_name="underwriting_case")
    risk_class = models.CharField(max_length=30, blank=True)
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES, default="PENDING")
    decision_reason = models.TextField(blank=True)
    reviewer = models.ForeignKey("users.User", on_delete=models.PROTECT, null=True, blank=True, related_name="ordinary_life_underwriting_cases")
    started_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    reopened_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_underwriting_case"
        indexes = [models.Index(fields=["decision", "created_at"])]


class OLUnderwritingDecisionEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    underwriting_case = models.ForeignKey(
        OLUnderwritingCase, on_delete=models.PROTECT, related_name="decision_events"
    )
    previous_decision = models.CharField(max_length=20, blank=True)
    decision = models.CharField(max_length=20)
    risk_class = models.CharField(max_length=30, blank=True)
    reason = models.TextField()
    actor = models.ForeignKey(
        "users.User", on_delete=models.PROTECT, null=True, blank=True,
        related_name="ordinary_life_underwriting_decision_events",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ol_underwriting_decision_event"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["underwriting_case", "created_at"])]


class OLHealthDeclaration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.ForeignKey(OLProposal, on_delete=models.PROTECT, related_name="health_declarations")
    questionnaire = models.ForeignKey(OLHealthQuestionnaire, on_delete=models.PROTECT, related_name="declarations")
    version_number = models.PositiveIntegerField(default=1)
    is_complete = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ol_health_declaration"
        constraints = [models.UniqueConstraint(fields=["proposal", "version_number"], name="ol_health_declaration_unique_version")]


class OLHealthResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    declaration = models.ForeignKey(OLHealthDeclaration, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(OLHealthQuestion, on_delete=models.PROTECT, related_name="health_responses")
    answer = models.JSONField(default=dict)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ol_health_response"
        constraints = [models.UniqueConstraint(fields=["declaration", "question"], name="ol_health_response_unique_question")]


class OLMedicalRequirement(models.Model):
    STATUS_CHOICES = (("PENDING", "Pending"), ("UPLOADED", "Uploaded"), ("VERIFIED", "Verified"), ("WAIVED", "Waived"), ("REJECTED", "Rejected"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    underwriting_case = models.ForeignKey(OLUnderwritingCase, on_delete=models.PROTECT, related_name="medical_requirements")
    requirement_type = models.CharField(max_length=80)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_medical_requirement"
        constraints = [models.UniqueConstraint(fields=["underwriting_case", "requirement_type"], name="ol_medical_requirement_unique_type")]


class OLMedicalResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requirement = models.OneToOneField(OLMedicalRequirement, on_delete=models.PROTECT, related_name="result")
    result = models.CharField(max_length=30)
    evidence_reference = models.CharField(max_length=255, blank=True)
    result_data = models.JSONField(default=dict, blank=True)
    verified_by = models.ForeignKey("users.User", on_delete=models.PROTECT, null=True, blank=True, related_name="ordinary_life_medical_results")
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ol_medical_result"


class OLPaymentObligation(models.Model):
    OBLIGATION_CHOICES = (("FIRST_PREMIUM", "First premium"), ("RENEWAL_PREMIUM", "Renewal premium"), ("INSTALMENT", "Instalment"), ("LOAN", "Loan"), ("WITHDRAWAL", "Withdrawal"))
    STATUS_CHOICES = (("DUE", "Due"), ("PARTIALLY_PAID", "Partially paid"), ("PAID", "Paid"), ("VOID", "Void"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.ForeignKey(OLProposal, on_delete=models.PROTECT, related_name="payment_obligations", null=True, blank=True)
    policy = models.ForeignKey(OLPolicy, on_delete=models.PROTECT, related_name="payment_obligations", null=True, blank=True)
    obligation_type = models.CharField(max_length=30, choices=OBLIGATION_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    allocated_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="TZS")
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DUE")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_payment_obligation"
        constraints = [
            models.CheckConstraint(check=Q(proposal__isnull=False) | Q(policy__isnull=False), name="ol_payment_obligation_has_parent"),
            models.CheckConstraint(check=Q(amount__gt=0), name="ol_payment_obligation_positive_amount"),
            models.CheckConstraint(check=Q(allocated_amount__gte=0) & Q(allocated_amount__lte=F("amount")), name="ol_payment_obligation_valid_allocation"),
        ]
        indexes = [models.Index(fields=["policy", "status", "due_date"])]


class OLPaymentAllocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    obligation = models.ForeignKey(OLPaymentObligation, on_delete=models.PROTECT, related_name="allocations")
    external_receipt_reference = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="TZS")
    allocated_at = models.DateTimeField(auto_now_add=True)
    allocated_by = models.ForeignKey("users.User", on_delete=models.PROTECT, null=True, blank=True, related_name="ordinary_life_payment_allocations")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ol_payment_allocation"
        constraints = [models.CheckConstraint(check=Q(amount__gt=0), name="ol_payment_allocation_positive_amount")]
        indexes = [models.Index(fields=["external_receipt_reference"])]


class OLPolicyParty(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(OLPolicy, on_delete=models.PROTECT, related_name="policy_parties")
    partner = models.ForeignKey("partners.Partner", on_delete=models.PROTECT, related_name="ordinary_life_policy_parties", null=True, blank=True)
    legacy_client = models.ForeignKey(OLClient, on_delete=models.PROTECT, related_name="policy_party_snapshots", null=True, blank=True)
    role = models.CharField(max_length=30, choices=OLPartyRole.ROLE_CHOICES)
    is_primary = models.BooleanField(default=False)
    identity_snapshot = models.JSONField(default=dict, blank=True)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ol_policy_party"
        constraints = [
            models.CheckConstraint(check=Q(partner__isnull=False) | Q(legacy_client__isnull=False), name="ol_policy_party_has_identity"),
            models.CheckConstraint(check=Q(effective_to__isnull=True) | Q(effective_to__gte=F("effective_from")), name="ol_policy_party_valid_dates"),
            models.UniqueConstraint(fields=["policy", "role"], condition=Q(is_primary=True, effective_to__isnull=True), name="ol_policy_party_one_current_primary"),
        ]


class OLPremiumSchedule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(OLPolicy, on_delete=models.PROTECT, related_name="premium_schedules")
    frequency = models.CharField(max_length=30)
    currency = models.CharField(max_length=3, default="TZS")
    total_premium = models.DecimalField(max_digits=14, decimal_places=2)
    installment_count = models.PositiveIntegerField(default=1)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ol_premium_schedule"
        constraints = [
            models.CheckConstraint(check=Q(total_premium__gt=0), name="ol_premium_schedule_positive_total"),
            models.CheckConstraint(check=Q(installment_count__gt=0), name="ol_premium_schedule_positive_count"),
            models.CheckConstraint(check=Q(effective_to__isnull=True) | Q(effective_to__gt=F("effective_from")), name="ol_premium_schedule_valid_dates"),
            models.UniqueConstraint(fields=["policy"], condition=Q(is_current=True), name="ol_premium_schedule_one_current"),
        ]


class OLPremiumInstallment(models.Model):
    STATUS_CHOICES = (("DUE", "Due"), ("PARTIALLY_PAID", "Partially paid"), ("PAID", "Paid"), ("WAIVED", "Waived"), ("OVERDUE", "Overdue"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule = models.ForeignKey(OLPremiumSchedule, on_delete=models.PROTECT, related_name="installments")
    sequence = models.PositiveIntegerField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    allocated_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DUE")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ol_premium_installment"
        constraints = [
            models.UniqueConstraint(fields=["schedule", "sequence"], name="ol_premium_installment_unique_sequence"),
            models.CheckConstraint(check=Q(sequence__gt=0), name="ol_premium_installment_positive_sequence"),
            models.CheckConstraint(check=Q(amount__gt=0), name="ol_premium_installment_positive_amount"),
            models.CheckConstraint(check=Q(allocated_amount__gte=0) & Q(allocated_amount__lte=F("amount")), name="ol_premium_installment_valid_allocation"),
        ]


class OLPolicyTransaction(models.Model):
    TYPE_CHOICES = (("ISSUANCE", "Issuance"), ("ENDORSEMENT", "Endorsement"), ("PAYMENT", "Payment"), ("LOAN", "Loan"), ("WITHDRAWAL", "Withdrawal"), ("SURRENDER", "Surrender"), ("PAID_UP", "Paid up"), ("REINSTATEMENT", "Reinstatement"), ("RENEWAL", "Renewal"), ("MATURITY", "Maturity"), ("CANCELLATION", "Cancellation"))
    STATUS_CHOICES = (("PENDING", "Pending"), ("APPROVED", "Approved"), ("POSTED", "Posted"), ("REVERSED", "Reversed"), ("CANCELLED", "Cancelled"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_number = models.CharField(max_length=100, unique=True)
    policy = models.ForeignKey(OLPolicy, on_delete=models.PROTECT, related_name="transactions")
    transaction_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    effective_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="TZS")
    reason = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=120, null=True, blank=True, unique=True)
    before_snapshot = models.JSONField(default=dict, blank=True)
    after_snapshot = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey("users.User", on_delete=models.PROTECT, null=True, blank=True, related_name="ordinary_life_policy_transactions")
    created_at = models.DateTimeField(auto_now_add=True)
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ol_policy_transaction"
        ordering = ["-effective_date", "-created_at"]
        constraints = [models.CheckConstraint(check=Q(amount__isnull=True) | Q(amount__gte=0), name="ol_policy_transaction_nonnegative_amount")]
        indexes = [
            models.Index(fields=["policy", "transaction_type", "effective_date"]),
            models.Index(fields=["status", "created_at"]),
        ]


class OLEndorsement(models.Model):
    STATUS_CHOICES = (("DRAFT", "Draft"), ("PENDING_APPROVAL", "Pending approval"), ("APPROVED", "Approved"), ("APPLIED", "Applied"), ("DECLINED", "Declined"), ("CANCELLED", "Cancelled"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    endorsement_number = models.CharField(max_length=100, unique=True)
    policy = models.ForeignKey(OLPolicy, on_delete=models.PROTECT, related_name="endorsements")
    endorsement_type = models.CharField(max_length=50)
    requested_effective_date = models.DateField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="DRAFT")
    requested_changes = models.JSONField(default=dict)
    reason = models.TextField(blank=True)
    approved_by = models.ForeignKey("users.User", on_delete=models.PROTECT, null=True, blank=True, related_name="approved_ordinary_life_endorsements")
    approved_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey("users.User", on_delete=models.PROTECT, null=True, blank=True, related_name="created_ordinary_life_endorsements")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ol_endorsement"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["policy", "status"])]


class OLPolicyStatusHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(OLPolicy, on_delete=models.PROTECT, related_name="status_history")
    previous_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30)
    reason = models.TextField(blank=True)
    actor = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="ordinary_life_policy_status_changes")
    correlation_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ol_policy_status_history"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["policy", "created_at"])]


class OLDocumentRecord(models.Model):
    STATUS_CHOICES = (("PENDING", "Pending"), ("UPLOADED", "Uploaded"), ("VERIFIED", "Verified"), ("REJECTED", "Rejected"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.ForeignKey(OLProposal, on_delete=models.PROTECT, related_name="document_records", null=True, blank=True)
    policy = models.ForeignKey(OLPolicy, on_delete=models.PROTECT, related_name="document_records", null=True, blank=True)
    document_type = models.CharField(max_length=80)
    file_reference = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    metadata = models.JSONField(default=dict, blank=True)
    uploaded_by = models.ForeignKey("users.User", on_delete=models.PROTECT, null=True, blank=True, related_name="ordinary_life_documents")
    verified_by = models.ForeignKey("users.User", on_delete=models.PROTECT, null=True, blank=True, related_name="verified_ordinary_life_documents")
    uploaded_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ol_document_record"
        constraints = [
            models.CheckConstraint(check=Q(proposal__isnull=False) | Q(policy__isnull=False), name="ol_document_has_parent"),
            models.UniqueConstraint(fields=["proposal", "document_type"], condition=Q(proposal__isnull=False), name="ol_document_one_proposal_type"),
        ]
        indexes = [models.Index(fields=["policy", "status"])]


class OLNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.ForeignKey(OLProposal, on_delete=models.PROTECT, related_name="notes", null=True, blank=True)
    policy = models.ForeignKey(OLPolicy, on_delete=models.PROTECT, related_name="notes", null=True, blank=True)
    content = models.TextField()
    is_internal = models.BooleanField(default=True)
    created_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="ordinary_life_notes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ol_note"
        constraints = [models.CheckConstraint(check=Q(proposal__isnull=False) | Q(policy__isnull=False), name="ol_note_has_parent")]
        ordering = ["-created_at"]


class OLBeneficiaryAllocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(OLPolicy, on_delete=models.PROTECT, related_name="beneficiary_allocations")
    beneficiary = models.ForeignKey(OLBeneficiary, on_delete=models.PROTECT, related_name="allocations")
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_beneficiary_allocation"
        constraints = [
            models.CheckConstraint(check=Q(percentage__gt=0) & Q(percentage__lte=100), name="ol_beneficiary_allocation_valid_percentage"),
            models.CheckConstraint(check=Q(effective_to__isnull=True) | Q(effective_to__gte=F("effective_from")), name="ol_beneficiary_allocation_valid_dates"),
        ]
        indexes = [models.Index(fields=["policy", "is_active"])]

    def clean(self):
        super().clean()
        if self.beneficiary_id and self.policy_id and self.beneficiary.policy_id != self.policy_id:
            raise ValidationError("Beneficiary must belong to the same policy as the allocation.")
        if self.is_active and self.policy_id:
            active_total = OLBeneficiaryAllocation.objects.filter(policy_id=self.policy_id, is_active=True).exclude(pk=self.pk).aggregate(total=models.Sum("percentage"))["total"] or 0
            if active_total + self.percentage > 100:
                raise ValidationError("Active beneficiary allocations cannot exceed 100%.")


class OLStateTransitionGuard(models.Model):
    entity_type = models.CharField(max_length=50)
    from_status = models.CharField(max_length=50)
    to_status = models.CharField(max_length=50)
    action = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ol_state_transition_guard"
        constraints = [models.UniqueConstraint(fields=["entity_type", "from_status", "to_status", "action"], name="ol_transition_guard_unique")]
        indexes = [models.Index(fields=["entity_type", "from_status", "is_active"])]

    def __str__(self):
        return f"{self.entity_type}: {self.from_status} -> {self.to_status}"


class OLVersionedRecordMixin:
    """Documentation mixin marker for aggregates that require service-owned updates."""
    pass


# Python-level validation for cross-row invariants that database constraints cannot express.
def validate_policy_beneficiary_total(policy):
    total = policy.beneficiary_allocations.filter(is_active=True).aggregate(total=models.Sum("percentage"))["total"] or 0
    if total != 100:
        raise ValidationError("Active beneficiary allocations must total exactly 100% before policy issuance.")
    return total
