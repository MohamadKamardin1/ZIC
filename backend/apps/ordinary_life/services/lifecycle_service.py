import logging
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.governance.services.audit_service import AuditContext, AuditService
from apps.system_parameters.services.numbering_service import NumberingEngine
from apps.ordinary_life.models import (
    OLClaim,
    OLCommitment,
    OLMaturityInstallment,
    OLPolicy,
    OLProposal,
    OLQuotation,
    OLLoan,
    OLWithdrawal,
    OLWorkflowEvent,
)

logger = logging.getLogger(__name__)


class OrdinaryLifeWorkflowService:
    """Transactional application service for Ordinary Life business workflows."""

    @staticmethod
    def _actor():
        user = AuditContext.get_context().get("user")
        return user if user and not user.is_anonymous else None

    @staticmethod
    def _event(entity, action, previous_status="", new_status="", reason="", metadata=None):
        OLWorkflowEvent.objects.create(
            entity_type=entity._meta.model_name,
            entity_id=entity.pk,
            action=action,
            previous_status=previous_status or "",
            new_status=new_status or "",
            reason=(reason or "").strip(),
            actor=OrdinaryLifeWorkflowService._actor(),
            metadata=metadata or {},
        )
        AuditService.log(
            action_type=action,
            entity_type=entity._meta.model_name,
            entity_id=entity.pk,
            entity_repr=str(entity),
            description=(reason or "").strip(),
            before_state={"status": previous_status} if previous_status else None,
            after_state={"status": new_status} if new_status else None,
        )

    @staticmethod
    def _set_status(entity, new_status, action, reason="", allowed=None, update_fields=None):
        previous = entity.status
        if allowed is not None and previous not in allowed:
            raise ValidationError({"status": f"Cannot {action.lower()} from status {previous}."})
        if previous == new_status:
            raise ValidationError({"status": f"Record is already {new_status}."})
        entity.status = new_status
        fields = update_fields or ["status", "updated_at"]
        entity.save(update_fields=fields)
        OrdinaryLifeWorkflowService._event(entity, action, previous, new_status, reason)
        return entity

    @staticmethod
    def _positive(value, field):
        if value is None or Decimal(str(value)) <= 0:
            raise ValidationError({field: "Value must be greater than zero."})

    @staticmethod
    def _policy_value(policy):
        return policy.sum_assured or policy.proposal.quotation.sum_assured

    @staticmethod
    def _parameter_decimal(code, default):
        from apps.ordinary_life.models import OLDefaultSystemParameter
        value = OLDefaultSystemParameter.objects.filter(code=code, is_active=True).values_list("value", flat=True).first()
        try:
            return Decimal(value) if value is not None else Decimal(str(default))
        except (TypeError, ValueError):
            return Decimal(str(default))

    @staticmethod
    def _add_years(value, years):
        try:
            return value.replace(year=value.year + years)
        except ValueError:
            return value.replace(month=2, day=28, year=value.year + years)

    @staticmethod
    @transaction.atomic
    def submit_quotation(quotation, reason=""):
        if quotation.product_id is None or not quotation.product.is_active:
            raise ValidationError({"product": "An active product is required before submission."})
        OrdinaryLifeWorkflowService._positive(quotation.sum_assured, "sum_assured")
        OrdinaryLifeWorkflowService._positive(quotation.premium_amount, "premium_amount")
        return OrdinaryLifeWorkflowService._set_status(
            quotation, "SUBMITTED", "SUBMIT_QUOTATION", reason, allowed={"DRAFT"}
        )

    @staticmethod
    @transaction.atomic
    def convert_quotation_to_proposal(quotation, medical_required=None, reason=""):
        if quotation.status != "SUBMITTED":
            raise ValidationError({"status": "Only submitted quotations can be converted to proposals."})
        if not quotation.product.is_active:
            raise ValidationError({"product": "The selected product is inactive."})
        if hasattr(quotation, "proposal"):
            return quotation.proposal
        if medical_required is None:
            threshold = OrdinaryLifeWorkflowService._parameter_decimal("OL_MEDICAL_SUM_ASSURED_LIMIT", "100000000")
            medical_required = quotation.sum_assured >= threshold
        proposal = OLProposal.objects.create(
            proposal_number=NumberingEngine.generate_number(
                "OL_PROPOSAL", OLProposal, field_name="proposal_number"
            ),
            quotation=quotation,
            medical_required=bool(medical_required),
            underwriting_status="PENDING",
            status="PENDING",
        )
        OrdinaryLifeWorkflowService._set_status(
            quotation, "CONVERTED", "CONVERT_QUOTATION", reason, allowed={"SUBMITTED"}
        )
        OrdinaryLifeWorkflowService._event(
            proposal,
            "CREATE_PROPOSAL",
            new_status=proposal.status,
            reason=reason,
            metadata={"quotation_id": str(quotation.pk)},
        )
        return proposal

    @staticmethod
    @transaction.atomic
    def complete_underwriting(proposal, decision, reason=""):
        decision = str(decision).upper()
        if proposal.status != "PENDING":
            raise ValidationError({"status": "Underwriting can only be completed for pending proposals."})
        if decision not in {"APPROVED", "DECLINED", "REFERRED"}:
            raise ValidationError({"decision": "Decision must be APPROVED, DECLINED, or REFERRED."})
        previous = proposal.underwriting_status
        proposal.underwriting_status = decision
        if decision == "DECLINED":
            proposal.status = "DECLINED"
        proposal.save(update_fields=["underwriting_status", "status", "updated_at"])
        OrdinaryLifeWorkflowService._event(
            proposal,
            "COMPLETE_UNDERWRITING",
            previous_status=previous,
            new_status=decision,
            reason=reason,
            metadata={"proposal_status": proposal.status},
        )
        return proposal

    @staticmethod
    @transaction.atomic
    def approve_proposal(proposal, reason=""):
        if proposal.status != "PENDING":
            raise ValidationError({"status": "Only pending proposals can be approved."})
        if proposal.underwriting_status != "APPROVED":
            raise ValidationError({"underwriting_status": "Proposal must have approved underwriting."})
        return OrdinaryLifeWorkflowService._set_status(
            proposal, "APPROVED", "APPROVE_PROPOSAL", reason, allowed={"PENDING"}
        )

    @staticmethod
    @transaction.atomic
    def decline_proposal(proposal, reason):
        if not reason or not reason.strip():
            raise ValidationError({"reason": "A decline reason is required."})
        return OrdinaryLifeWorkflowService._set_status(
            proposal, "DECLINED", "DECLINE_PROPOSAL", reason, allowed={"PENDING"}
        )

    @staticmethod
    @transaction.atomic
    def settle_commitment(commitment, amount_paid=None, reason=""):
        if commitment.proposal.status != "APPROVED":
            raise ValidationError({"proposal": "Commitments require an approved proposal."})
        if commitment.status not in {"PENDING", "PARTIALLY_PAID"}:
            raise ValidationError({"status": "Only pending commitments can be settled."})
        amount = Decimal(str(amount_paid if amount_paid is not None else commitment.amount_paid))
        OrdinaryLifeWorkflowService._positive(amount, "amount_paid")
        commitment.amount_paid = amount
        return OrdinaryLifeWorkflowService._set_status(
            commitment, "PAID", "SETTLE_COMMITMENT", reason,
            allowed={"PENDING", "PARTIALLY_PAID"},
            update_fields=["amount_paid", "status", "updated_at"],
        )

    @staticmethod
    @transaction.atomic
    def issue_policy(proposal, start_date=None, end_date=None, agent=None, reason=""):
        if proposal.status != "APPROVED":
            raise ValidationError({"proposal": "Policies require an approved proposal."})
        if hasattr(proposal, "policy"):
            return proposal.policy
        commitments = proposal.commitments.filter(status="PAID")
        if not commitments.exists() or sum((c.amount_paid for c in commitments), Decimal("0")) < proposal.quotation.premium_amount:
            raise ValidationError({"commitments": "At least one settled commitment covering the premium is required."})
        start_date = start_date or timezone.localdate()
        end_date = end_date or OrdinaryLifeWorkflowService._add_years(
            start_date, proposal.quotation.product.term_length_years or 1
        )
        if end_date <= start_date:
            raise ValidationError({"end_date": "End date must be after start date."})
        policy = OLPolicy.objects.create(
            policy_number=NumberingEngine.generate_number("OL_POLICY", OLPolicy, field_name="policy_number"),
            proposal=proposal,
            policyholder=proposal.quotation.client,
            life_assured=proposal.quotation.client,
            agent=agent,
            currency="TZS",
            sum_assured=proposal.quotation.sum_assured,
            premium_amount=proposal.quotation.premium_amount,
            start_date=start_date,
            end_date=end_date,
            status="ACTIVE",
        )
        OrdinaryLifeWorkflowService._event(
            policy, "ISSUE_POLICY", new_status=policy.status, reason=reason,
            metadata={"proposal_id": str(proposal.pk)},
        )
        return policy

    @staticmethod
    @transaction.atomic
    def request_loan(policy, loan_amount, interest_rate=None, reason=""):
        if policy.status != "ACTIVE":
            raise ValidationError({"policy": "Loans can only be requested on active policies."})
        amount = Decimal(str(loan_amount))
        OrdinaryLifeWorkflowService._positive(amount, "loan_amount")
        max_percentage = OrdinaryLifeWorkflowService._parameter_decimal("OL_MAX_LOAN_PERCENTAGE", "80")
        maximum = OrdinaryLifeWorkflowService._policy_value(policy) * max_percentage / Decimal("100")
        outstanding = sum((loan.outstanding_balance for loan in policy.loans.filter(status__in=["PENDING", "APPROVED"])), Decimal("0"))
        if amount + outstanding > maximum:
            raise ValidationError({"loan_amount": f"Requested amount exceeds the available loan limit of {maximum}."})
        loan = OLLoan.objects.create(
            loan_number=NumberingEngine.generate_number("OL_LOAN", OLLoan, field_name="loan_number"),
            policy=policy,
            loan_amount=amount,
            interest_rate=Decimal(str(interest_rate)) if interest_rate is not None else OrdinaryLifeWorkflowService._parameter_decimal("OL_LOAN_INTEREST_RATE", "10"),
            outstanding_balance=amount,
            status="PENDING",
        )
        OrdinaryLifeWorkflowService._event(loan, "REQUEST_LOAN", new_status=loan.status, reason=reason)
        return loan

    @staticmethod
    @transaction.atomic
    def approve_loan(loan, reason=""):
        if loan.policy.status != "ACTIVE":
            raise ValidationError({"policy": "Only active policies can have approved loans."})
        return OrdinaryLifeWorkflowService._set_status(loan, "APPROVED", "APPROVE_LOAN", reason, allowed={"PENDING"})

    @staticmethod
    @transaction.atomic
    def request_withdrawal(policy, amount, withdrawal_type="PARTIAL", reason=""):
        if policy.status != "ACTIVE":
            raise ValidationError({"policy": "Withdrawals require an active policy."})
        withdrawal_type = str(withdrawal_type).upper()
        if withdrawal_type not in {"PARTIAL", "FULL_SURRENDER"}:
            raise ValidationError({"withdrawal_type": "Withdrawal type must be PARTIAL or FULL_SURRENDER."})
        amount = Decimal(str(amount))
        OrdinaryLifeWorkflowService._positive(amount, "amount")
        maximum = OrdinaryLifeWorkflowService._policy_value(policy)
        existing = sum((w.amount for w in policy.withdrawals.filter(status="PENDING")), Decimal("0"))
        if amount + existing > maximum:
            raise ValidationError({"amount": f"Requested amount exceeds the available policy value of {maximum}."})
        withdrawal = OLWithdrawal.objects.create(
            withdrawal_number=NumberingEngine.generate_number("OL_WITHDRAWAL", OLWithdrawal, field_name="withdrawal_number"),
            policy=policy,
            amount=amount,
            withdrawal_type=withdrawal_type,
            status="PENDING",
        )
        OrdinaryLifeWorkflowService._event(withdrawal, "REQUEST_WITHDRAWAL", new_status=withdrawal.status, reason=reason)
        return withdrawal

    @staticmethod
    @transaction.atomic
    def pay_withdrawal(withdrawal, reason=""):
        return OrdinaryLifeWorkflowService._set_status(withdrawal, "PAID", "PAY_WITHDRAWAL", reason, allowed={"PENDING"})

    @staticmethod
    @transaction.atomic
    def submit_claim(claim, reason=""):
        if claim.policy.status not in {"ACTIVE", "MATURED", "SURRENDERED"}:
            raise ValidationError({"policy": "Claims cannot be submitted for a cancelled or lapsed policy."})
        OrdinaryLifeWorkflowService._positive(claim.claim_amount, "claim_amount")
        if claim.claim_amount > OrdinaryLifeWorkflowService._policy_value(claim.policy):
            raise ValidationError({"claim_amount": "Claim amount cannot exceed the policy benefit value."})
        return OrdinaryLifeWorkflowService._set_status(claim, "INVESTIGATING", "SUBMIT_CLAIM", reason, allowed={"REPORTED"})

    @staticmethod
    @transaction.atomic
    def approve_claim(claim, approved_amount=None, reason=""):
        if claim.status != "INVESTIGATING":
            raise ValidationError({"status": "Only investigating claims can be approved."})
        if approved_amount is not None:
            amount = Decimal(str(approved_amount))
            OrdinaryLifeWorkflowService._positive(amount, "approved_amount")
            if amount > claim.claim_amount:
                raise ValidationError({"approved_amount": "Approved amount cannot exceed the reported claim amount."})
            claim.claim_amount = amount
            claim.save(update_fields=["claim_amount", "updated_at"])
        return OrdinaryLifeWorkflowService._set_status(claim, "APPROVED", "APPROVE_CLAIM", reason, allowed={"INVESTIGATING"})

    @staticmethod
    @transaction.atomic
    def pay_claim(claim, reason=""):
        return OrdinaryLifeWorkflowService._set_status(claim, "PAID", "PAY_CLAIM", reason, allowed={"APPROVED"})

    @staticmethod
    @transaction.atomic
    def create_maturity_installment(policy, due_date, amount, reason=""):
        if policy.status not in {"ACTIVE", "MATURED"}:
            raise ValidationError({"policy": "Installments require an active or matured policy."})
        OrdinaryLifeWorkflowService._positive(amount, "amount")
        installment = OLMaturityInstallment.objects.create(
            installment_number=NumberingEngine.generate_number("OL_INSTALLMENT", OLMaturityInstallment, field_name="installment_number"),
            policy=policy,
            due_date=due_date,
            amount=amount,
            status="PENDING",
        )
        OrdinaryLifeWorkflowService._event(installment, "CREATE_MATURITY_INSTALLMENT", new_status=installment.status, reason=reason)
        return installment

    @staticmethod
    @transaction.atomic
    def pay_maturity_installment(installment, reason=""):
        return OrdinaryLifeWorkflowService._set_status(installment, "PAID", "PAY_MATURITY_INSTALLMENT", reason, allowed={"PENDING"})
