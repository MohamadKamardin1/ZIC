import threading
from contextlib import contextmanager

from django.db.models.signals import post_save, pre_save

from apps.governance.services.audit_service import AuditService

from .models import (
    OLAgentCommissionSetup,
    OLAnticipatedEndowmentInstallmentRate,
    OLBeneficialType,
    OLBonusRate,
    OLCashSurrenderValue,
    OLClaimReason,
    OLClaimStatus,
    OLClaimType,
    OLCommitmentStatus,
    OLComputationApproach,
    OLCorrespondentType,
    OLDefaultSystemParameter,
    OLDischargeType,
    OLGracePeriod,
    OLGracePeriodNotificationSchedule,
    OLHealthQuestion,
    OLHealthQuestionnaire,
    OLHealthQuestionnaireItem,
    OLInstallmentChargeRate,
    OLInvestmentFund,
    OLInvestmentFundType,
    OLJointLifeSetup,
    OLLoanInterestControl,
    OLLoanSystemSetup,
    OLMaturityClaimSetup,
    OLMedicalCode,
    OLMedicalFacility,
    OLMedicalHistory,
    OLMedicalLimit,
    OLMedicalPractitioner,
    OLMemberCoverConfiguration,
    OLMortalityRateRow,
    OLMortalityRateTable,
    OLMortgageInterestFactor,
    OLOverrideCommissionSetup,
    OLPaidUpRate,
    OLPaidUpSetup,
    OLParameterTableRegistry,
    OLPersonalHabit,
    OLPlanOccupationRiskLimit,
    OLPlanRiskCategory,
    OLPlanTargetMarket,
    OLPlanTaxConfiguration,
    OLPlanType,
    OLPolicyRenewalStatus,
    OLPolicyStatus,
    OLPremiumRateRow,
    OLPremiumRateTable,
    OLProduct,
    OLReinstatementInterestRate,
    OLReinstatementWindow,
    OLReserveLoading,
    OLRiderRateRow,
    OLRiderRateTable,
    OLRiderSetup,
    OLSurrenderSetup,
    OLSurrenderValueRate,
)

AUDITED_MODELS = (
    OLParameterTableRegistry,
    OLDefaultSystemParameter,
    OLAgentCommissionSetup,
    OLOverrideCommissionSetup,
    OLComputationApproach,
    OLMaturityClaimSetup,
    OLAnticipatedEndowmentInstallmentRate,
    OLGracePeriod,
    OLPolicyStatus,
    OLPolicyRenewalStatus,
    OLBeneficialType,
    OLMemberCoverConfiguration,
    OLSurrenderSetup,
    OLPaidUpSetup,
    OLSurrenderValueRate,
    OLPaidUpRate,
    OLCommitmentStatus,
    OLGracePeriodNotificationSchedule,
    OLHealthQuestion,
    OLHealthQuestionnaire,
    OLHealthQuestionnaireItem,
    OLReinstatementWindow,
    OLPlanType,
    OLProduct,
    OLPlanTaxConfiguration,
    OLPlanTargetMarket,
    OLPlanRiskCategory,
    OLPlanOccupationRiskLimit,
    OLInvestmentFundType,
    OLInvestmentFund,
    OLPremiumRateTable,
    OLPremiumRateRow,
    OLMortalityRateTable,
    OLMortalityRateRow,
    OLJointLifeSetup,
    OLReinstatementInterestRate,
    OLBonusRate,
    OLMortgageInterestFactor,
    OLInstallmentChargeRate,
    OLCashSurrenderValue,
    OLReserveLoading,
    OLRiderSetup,
    OLRiderRateTable,
    OLRiderRateRow,
    OLLoanSystemSetup,
    OLLoanInterestControl,
    OLMedicalCode,
    OLMedicalLimit,
    OLPersonalHabit,
    OLMedicalHistory,
    OLMedicalFacility,
    OLMedicalPractitioner,
    OLClaimType,
    OLClaimReason,
    OLClaimStatus,
    OLDischargeType,
    OLCorrespondentType,
)


_state = threading.local()


def _is_suppressed():
    return bool(getattr(_state, "suppressed", False))


@contextmanager
def audit_suppressed():
    previous = _is_suppressed()
    _state.suppressed = True
    try:
        yield
    finally:
        _state.suppressed = previous


def _capture_before_state(sender, instance, **kwargs):
    if _is_suppressed() or not instance.pk:
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        previous = None
    if previous is not None:
        instance._ol_parameters_before_state = AuditService.snapshot(previous)


def _audit_save(sender, instance, created, **kwargs):
    if _is_suppressed():
        return
    before = getattr(instance, "_ol_parameters_before_state", None)
    label = sender._meta.verbose_name.replace("_", " ")
    if created:
        AuditService.log_create(instance, reason=f"OL Parameters {label} created.")
    elif before is not None:
        after = AuditService.snapshot(instance)
        if before != after:
            AuditService.log_update(
                instance,
                before_state=before,
                changed_fields=AuditService.changed_fields(before, after),
                reason=f"OL Parameters {label} updated.",
            )
    if hasattr(instance, "_ol_parameters_before_state"):
        delattr(instance, "_ol_parameters_before_state")


for _model in AUDITED_MODELS:
    pre_save.connect(
        _capture_before_state,
        sender=_model,
        dispatch_uid=f"ol_parameters_{_model.__name__.lower()}_before_save",
    )
    post_save.connect(
        _audit_save,
        sender=_model,
        dispatch_uid=f"ol_parameters_{_model.__name__.lower()}_after_save",
    )


def register_receivers():
    """Signals are connected by decorators; retained as an explicit app hook."""
    return None
