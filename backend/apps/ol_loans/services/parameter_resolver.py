from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Q

from apps.governance.services.audit_service import AuditContext, AuditService
from apps.ol_parameters.models import OLLoanInterestControl, OLLoanSystemSetup

from .parameter_cache import parameter_cache_revision
from ..errors import parameter_missing


@dataclass(frozen=True)
class LoanConfig:
    """Resolved, immutable runtime configuration for one policy loan decision."""

    as_of: date
    system_setup_id: str
    interest_control_id: str
    allow_policy_loans: bool
    loan_basis: str
    max_loan_percentage: Decimal
    min_loan_amount: Decimal | None
    max_loan_amount: Decimal | None
    loan_currency: str
    repayment_options: tuple
    auto_deduct_from_benefits: bool
    effect_on_claim: str
    effect_on_surrender: str
    effect_on_maturity: str
    require_approval: bool
    interest_rate: Decimal
    compounding_frequency: str
    interest_calculation_basis: str
    grace_days: int
    penalty_rate: Decimal
    interest_suspension_rule: str
    capitalize_interest: bool

    def as_dict(self):
        return {
            "as_of": self.as_of.isoformat(),
            "system_setup_id": self.system_setup_id,
            "interest_control_id": self.interest_control_id,
            "allow_policy_loans": self.allow_policy_loans,
            "loan_basis": self.loan_basis,
            "max_loan_percentage": str(self.max_loan_percentage),
            "min_loan_amount": str(self.min_loan_amount) if self.min_loan_amount is not None else None,
            "max_loan_amount": str(self.max_loan_amount) if self.max_loan_amount is not None else None,
            "loan_currency": self.loan_currency,
            "repayment_options": list(self.repayment_options),
            "auto_deduct_from_benefits": self.auto_deduct_from_benefits,
            "effect_on_claim": self.effect_on_claim,
            "effect_on_surrender": self.effect_on_surrender,
            "effect_on_maturity": self.effect_on_maturity,
            "require_approval": self.require_approval,
            "interest_rate": str(self.interest_rate),
            "compounding_frequency": self.compounding_frequency,
            "interest_calculation_basis": self.interest_calculation_basis,
            "grace_days": self.grace_days,
            "penalty_rate": str(self.penalty_rate),
            "interest_suspension_rule": self.interest_suspension_rule,
            "capitalize_interest": self.capitalize_interest,
        }


CACHE_TIMEOUT_SECONDS = 300


def _as_of(value):
    return value or date.today()


def _within_effect(queryset, as_of):
    return queryset.filter(
        Q(effective_from__isnull=True) | Q(effective_from__lte=as_of),
        Q(effective_to__isnull=True) | Q(effective_to__gte=as_of),
        is_active=True,
    )


def _related_scope(policy):
    product = getattr(policy, "product", None) or getattr(policy, "product_ref", None)
    plan = getattr(policy, "plan", None) or getattr(policy, "plan_ref", None)
    snapshot = getattr(policy, "contract_snapshot", None) or {}
    if not isinstance(snapshot, dict):
        snapshot = {}
    product_id = getattr(product, "pk", None) or snapshot.get("product_id")
    plan_id = getattr(plan, "pk", None) or snapshot.get("plan_id")
    product_code = getattr(product, "code", None) or snapshot.get("product_code")
    plan_code = getattr(plan, "code", None) or snapshot.get("plan_code")
    product_plan_ref = getattr(policy, "product_plan_ref", "") or ""
    return product_id, plan_id, product_code, plan_code, product_plan_ref


def _scope_score(row, product_id, plan_id):
    return (
        0 if product_id and row.product_id == product_id else 1 if row.product_id is None else 2,
        0 if plan_id and row.plan_id == plan_id else 1 if row.plan_id is None else 2,
        -(row.effective_from.toordinal() if row.effective_from else 0),
        row.code,
    )


def _pick_setup(queryset, product_id=None, plan_id=None, product_code="", plan_code="", product_plan_ref=""):
    scoped = []
    for row in queryset:
        if row.product_id and product_id and str(row.product_id) != str(product_id):
            continue
        if row.plan_id and plan_id and str(row.plan_id) != str(plan_id):
            continue
        if row.product_id and not product_id:
            if product_code and getattr(row.product, "code", "").upper() != str(product_code).upper():
                continue
            if product_plan_ref and getattr(row.product, "code", "").upper() not in str(product_plan_ref).upper():
                continue
        if row.plan_id and not plan_id:
            if plan_code and getattr(row.plan, "code", "").upper() != str(plan_code).upper():
                continue
            if product_plan_ref and getattr(row.plan, "code", "").upper() not in str(product_plan_ref).upper():
                continue
        scoped.append(row)
    if not scoped:
        return None
    scoped.sort(key=lambda row: _scope_score(row, product_id, plan_id))
    return scoped[0]


def _audit_parameter_read(policy, system_setup, interest_control, *, actor=None, source_channel=None, request=None):
    actor = actor or AuditContext.get_context().get("user")
    channel = source_channel or AuditContext.get_context().get("source_channel")
    reference = getattr(policy, "policy_number", None) or str(getattr(policy, "pk", "policy"))
    AuditService.log(
        "READ",
        "ol_loans.loan_configuration",
        getattr(policy, "pk", None),
        entity_repr=reference,
        description="OL Loan parameter configuration resolved.",
        actor=actor,
        action="READ_CONFIGURATION",
        app_label="ol_loans",
        model_name="loanconfiguration",
        object_id=str(getattr(policy, "pk", "") or ""),
        object_repr=reference,
        reason="Loan configuration read for policy decision.",
        source_channel=channel,
        request=request,
        after_state={
            "system_setup_id": str(system_setup.pk) if system_setup else None,
            "interest_control_id": str(interest_control.pk) if interest_control else None,
        },
    )


def _build_config(as_of, system_setup, interest_control):
    if system_setup is None or interest_control is None:
        return None
    repayment_options = system_setup.repayment_options
    if isinstance(repayment_options, dict):
        repayment_options = tuple(
            {"code": str(key).upper(), **(value if isinstance(value, dict) else {"enabled": bool(value)})}
            for key, value in repayment_options.items()
        )
    elif isinstance(repayment_options, list):
        repayment_options = tuple(repayment_options)
    else:
        repayment_options = tuple()
    return LoanConfig(
        as_of=as_of,
        system_setup_id=str(system_setup.pk),
        interest_control_id=str(interest_control.pk),
        allow_policy_loans=bool(system_setup.allow_policy_loans),
        loan_basis=system_setup.loan_basis,
        max_loan_percentage=Decimal(system_setup.max_loan_percentage_of_cash_value),
        min_loan_amount=Decimal(system_setup.min_loan_amount) if system_setup.min_loan_amount is not None else None,
        max_loan_amount=Decimal(system_setup.max_loan_amount) if system_setup.max_loan_amount is not None else None,
        loan_currency=(system_setup.loan_currency or "").upper(),
        repayment_options=repayment_options,
        auto_deduct_from_benefits=bool(system_setup.auto_deduct_from_benefits),
        effect_on_claim=system_setup.effect_on_claim,
        effect_on_surrender=system_setup.effect_on_surrender,
        effect_on_maturity=system_setup.effect_on_maturity,
        require_approval=bool(system_setup.require_approval),
        interest_rate=Decimal(interest_control.interest_rate),
        compounding_frequency=interest_control.compounding_frequency,
        interest_calculation_basis=interest_control.interest_calculation_basis,
        grace_days=int(interest_control.grace_period_days or 0),
        penalty_rate=Decimal(interest_control.penalty_interest_rate or 0),
        interest_suspension_rule=interest_control.interest_suspension_rule,
        capitalize_interest=bool(interest_control.capitalize_interest),
    )


def get_loan_config(policy, as_of=None, *, actor=None, source_channel=None, request=None):
    """Resolve the most specific active setup and interest-control rows for a policy.

    Product + plan rows win over product-only, plan-only, and global rows. Both
    rows must exist and be effective on ``as_of``; callers should translate a
    missing result into ``LOAN_PARAMETER_MISSING``.
    """
    day = _as_of(as_of)
    product_id, plan_id, product_code, plan_code, product_plan_ref = _related_scope(policy)
    key = "ol_loans:config:{revision}:{product}:{plan}:{as_of}".format(
        revision=parameter_cache_revision(),
        product=product_id or product_code or product_plan_ref or "global",
        plan=plan_id or plan_code or "global",
        as_of=day.isoformat(),
    )
    config = cache.get(key)
    if config is None:
        system_queryset = _within_effect(
            OLLoanSystemSetup.objects.select_related("product", "plan"), day
        )
        interest_queryset = _within_effect(
            OLLoanInterestControl.objects.select_related("product", "plan"), day
        )
        system_setup = _pick_setup(system_queryset, product_id, plan_id, product_code, plan_code, product_plan_ref)
        interest_control = _pick_setup(interest_queryset, product_id, plan_id, product_code, plan_code, product_plan_ref)
        config = _build_config(day, system_setup, interest_control)
        if config is not None:
            cache.set(key, config, timeout=CACHE_TIMEOUT_SECONDS)
    else:
        system_setup = OLLoanSystemSetup.objects.filter(pk=config.system_setup_id).first()
        interest_control = OLLoanInterestControl.objects.filter(pk=config.interest_control_id).first()
    _audit_parameter_read(
        policy,
        system_setup,
        interest_control,
        actor=actor,
        source_channel=source_channel,
        request=request,
    )
    if config is None:
        raise parameter_missing(
            "OL Loan System Setup and OL Loan Interest Control",
            "Ordinary Life Parameters > Loan Setup / Interest Control",
        )
    return config
