import uuid
from django.db import models
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
    product = models.ForeignKey(OLProduct, on_delete=models.CASCADE, related_name="quotations")
    sum_assured = models.DecimalField(max_digits=12, decimal_places=2)
    premium_amount = models.DecimalField(max_digits=12, decimal_places=2)
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
    underwriting_status = models.CharField(max_length=50, default="PENDING")
    medical_required = models.BooleanField(default=False)
    status = models.CharField(max_length=50, default="PENDING") # PENDING, APPROVED, DECLINED
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

