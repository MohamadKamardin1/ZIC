import calendar
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.governance.services.audit_service import AuditContext, AuditService
from apps.ordinary_life.models import (
    OLBeneficiary,
    OLBeneficiaryAllocation,
    OLEndorsement,
    OLPaymentAllocation,
    OLPaymentObligation,
    OLPolicy,
    OLPolicyParty,
    OLPolicyRenewal,
    OLPolicyStatusHistory,
    OLPolicyTransaction,
    OLPremiumInstallment,
    OLPremiumSchedule,
    OLReinstatementRequest,
    OLWorkflowEvent,
    validate_policy_beneficiary_total,
)
from apps.ordinary_life.services.application_service import OrdinaryLifeApplicationService
from apps.system_parameters.services.numbering_service import NumberingEngine

MONEY_QUANTUM = Decimal("0.01")
FREQUENCY_DIVISORS = {
    "MONTHLY": 12,
    "QUARTERLY": 4,
    "SEMI_ANNUAL": 2,
    "ANNUAL": 1,
}


class OrdinaryLifePolicyService:
    """Service-owned Ordinary Life issuance and post-issuance lifecycle operations."""

    @staticmethod
    def _actor(actor=None):
        actor = actor or AuditContext.get_context().get("user")
        return actor if actor and not getattr(actor, "is_anonymous", False) else None

    @classmethod
    def _require_actor(cls, actor):
        actor = cls._actor(actor)
        if actor is None:
            raise ValidationError({"actor": "An authenticated decision actor is required."})
        return actor

    @staticmethod
    def _reason(reason, required=False):
        value = str(reason or "").strip()
        if required and not value:
            raise ValidationError({"reason": "A business reason is required for this operation."})
        return value

    @staticmethod
    def _source_metadata():
        context = AuditContext.get_context()
        return {
            "source_channel": context.get("source_channel") or "SYSTEM",
            "correlation_id": str(context.get("request_id") or "")[:100],
        }

    @staticmethod
    def _money(value, field, positive=True):
        try:
            amount = Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        except (TypeError, ValueError, ArithmeticError):
            raise ValidationError({field: "Enter a valid monetary amount."}) from None
        if positive and amount <= 0:
            raise ValidationError({field: "Amount must be greater than zero."})
        if not positive and amount < 0:
            raise ValidationError({field: "Amount cannot be negative."})
        return amount

    @staticmethod
    def _add_years(value, years):
        try:
            return value.replace(year=value.year + int(years))
        except ValueError:
            return value.replace(year=value.year + int(years), day=28)

    @staticmethod
    def _add_months(value, months):
        month_index = value.month - 1 + int(months)
        year = value.year + month_index // 12
        month = month_index % 12 + 1
        day = min(value.day, calendar.monthrange(year, month)[1])
        return value.replace(year=year, month=month, day=day)

    @classmethod
    def _event(cls, entity, action, actor=None, previous_status="", new_status="", reason="", metadata=None, before_state=None, after_state=None):
        actor = cls._actor(actor)
        reason = str(reason or "").strip()
        metadata = metadata or {}
        OLWorkflowEvent.objects.create(
            entity_type=entity._meta.model_name,
            entity_id=entity.pk,
            action=action,
            previous_status=previous_status or "",
            new_status=new_status or "",
            reason=reason,
            actor=actor,
            metadata=metadata,
        )
        AuditService.log(
            action_type=action,
            entity_type=entity._meta.model_name,
            entity_id=entity.pk,
            entity_repr=str(entity),
            actor=actor,
            action=action,
            reason=reason,
            before_state=before_state or ({"status": previous_status} if previous_status else {}),
            after_state=after_state or ({"status": new_status} if new_status else metadata),
            changed_fields=["status"] if previous_status or new_status else [],
            request_id=cls._source_metadata()["correlation_id"],
            source_channel=cls._source_metadata()["source_channel"],
        )

    @classmethod
    def _policy_snapshot(cls, policy):
        return {
            "policy_id": str(policy.pk),
            "policy_number": policy.policy_number,
            "status": policy.status,
            "product_version_id": str(policy.product_version_id) if policy.product_version_id else None,
            "product_snapshot": policy.product_snapshot or {},
            "policyholder_partner_id": str(policy.policyholder_partner_id) if policy.policyholder_partner_id else None,
            "life_assured_partner_id": str(policy.life_assured_partner_id) if policy.life_assured_partner_id else None,
            "currency": policy.currency,
            "sum_assured": str(policy.sum_assured) if policy.sum_assured is not None else None,
            "premium_amount": str(policy.premium_amount) if policy.premium_amount is not None else None,
            "start_date": str(policy.start_date),
            "end_date": str(policy.end_date),
        }

    @classmethod
    def _transaction(cls, policy, transaction_type, actor, reason="", amount=None, effective_date=None, before_state=None, after_state=None, idempotency_key=None, external_reference=""):
        if idempotency_key:
            existing = OLPolicyTransaction.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                if existing.policy_id != policy.pk or existing.transaction_type != transaction_type:
                    raise ValidationError({"idempotency_key": "The idempotency key belongs to another policy transaction."})
                return existing
        metadata = cls._source_metadata()
        return OLPolicyTransaction.objects.create(
            transaction_number=NumberingEngine.generate_number("OL_POLICY_TRANSACTION", OLPolicyTransaction, field_name="transaction_number"),
            policy=policy,
            transaction_type=transaction_type,
            status="POSTED",
            effective_date=effective_date or timezone.localdate(),
            amount=amount,
            currency=policy.currency,
            reason=cls._reason(reason),
            idempotency_key=idempotency_key,
            before_snapshot=before_state or {},
            after_snapshot=after_state or {},
            source_channel=metadata["source_channel"],
            correlation_id=metadata["correlation_id"],
            external_reference=str(external_reference or "")[:120],
            created_by=actor,
            posted_at=timezone.now(),
        )

    @classmethod
    def _transition(cls, policy, new_status, action, actor, reason="", allowed=None, effective_date=None, transaction_type=None, idempotency_key=None):
        previous_status = policy.status
        if allowed is not None and previous_status not in allowed:
            raise ValidationError({"status": f"Cannot {action.lower()} from status {previous_status}."})
        if previous_status == new_status:
            return policy, None
        before = cls._policy_snapshot(policy)
        policy.status = new_status
        policy.save(update_fields=["status", "updated_at"])
        correlation_id = cls._source_metadata()["correlation_id"]
        OLPolicyStatusHistory.objects.create(
            policy=policy,
            previous_status=previous_status,
            new_status=new_status,
            reason=cls._reason(reason),
            actor=actor,
            correlation_id=correlation_id,
        )
        after = cls._policy_snapshot(policy)
        cls._event(
            policy,
            action,
            actor=actor,
            previous_status=previous_status,
            new_status=new_status,
            reason=reason,
            before_state=before,
            after_state=after,
        )
        posted_transaction = None
        if transaction_type:
            posted_transaction = cls._transaction(
                policy,
                transaction_type,
                actor,
                reason=reason,
                effective_date=effective_date,
                before_state=before,
                after_state=after,
                idempotency_key=idempotency_key,
            )
        return policy, posted_transaction

    @classmethod
    def _application_parties(cls, proposal):
        application = getattr(proposal, "application", None)
        if application is None:
            quotation = proposal.quotation
            if not quotation.partner_id:
                raise ValidationError({"application": "An application with canonical policy parties is required for issuance."})
            return {
                "policyholder": quotation.partner,
                "life_assured": quotation.partner,
                "payer": quotation.partner,
                "intermediary": quotation.partner,
            }
        return {
            "policyholder": application.policyholder,
            "life_assured": application.life_assured,
            "payer": application.payer or application.policyholder,
            "intermediary": application.partner,
        }

    @classmethod
    def _create_policy_parties(cls, policy, parties, start_date):
        role_map = (
            ("POLICYHOLDER", parties["policyholder"]),
            ("LIFE_ASSURED", parties["life_assured"]),
            ("PAYER", parties["payer"]),
            ("INTERMEDIARY", parties["intermediary"]),
        )
        for role, partner in role_map:
            legacy_client = OrdinaryLifeApplicationService._client_projection(partner)
            OLPolicyParty.objects.create(
                policy=policy,
                partner=partner,
                legacy_client=legacy_client,
                role=role,
                is_primary=True,
                identity_snapshot=OrdinaryLifeApplicationService._partner_snapshot(partner),
                effective_from=start_date,
            )

    @classmethod
    def _create_beneficiaries(cls, policy, beneficiary_allocations, start_date):
        if not beneficiary_allocations:
            raise ValidationError({"beneficiaries": "At least one beneficiary allocation is required for issuance."})
        total = Decimal("0.00")
        for item in beneficiary_allocations:
            if not isinstance(item, dict):
                raise ValidationError({"beneficiaries": "Each beneficiary must be an object."})
            percentage = cls._money(item.get("percentage"), "beneficiaries.percentage")
            if percentage > 100:
                raise ValidationError({"beneficiaries.percentage": "A beneficiary allocation cannot exceed 100%."})
            name = str(item.get("name") or "").strip()
            relationship = str(item.get("relationship") or "").strip()
            if not name or not relationship:
                raise ValidationError({"beneficiaries": "Beneficiary name and relationship are required."})
            beneficiary = OLBeneficiary.objects.create(
                policy=policy,
                name=name,
                relationship=relationship,
                id_number=str(item.get("id_number") or ""),
                percentage=percentage,
                beneficiary_type=item.get("beneficiary_type"),
            )
            OLBeneficiaryAllocation.objects.create(
                policy=policy,
                beneficiary=beneficiary,
                percentage=percentage,
                effective_from=start_date,
                is_active=True,
            )
            total += percentage
        if total != Decimal("100.00"):
            raise ValidationError({"beneficiaries": "Active beneficiary allocations must total exactly 100%."})

    @classmethod
    def _annual_premium(cls, proposal):
        version = proposal.quotation_version
        outputs = version.calculated_outputs or {}
        annual = outputs.get("annual_premium")
        if annual is not None:
            return cls._money(annual, "annual_premium")
        divisor = FREQUENCY_DIVISORS.get(proposal.quotation.payment_frequency.upper(), 1)
        return (cls._money(proposal.quotation.premium_amount, "premium_amount") * divisor).quantize(MONEY_QUANTUM)

    @classmethod
    def _term_years(cls, proposal):
        term = (proposal.quotation_version.inputs or {}).get("term_years")
        try:
            term = int(term)
        except (TypeError, ValueError):
            raise ValidationError({"term_years": "The immutable quotation version must contain a valid term."}) from None
        if term <= 0:
            raise ValidationError({"term_years": "The policy term must be positive."})
        return term

    @classmethod
    def _create_schedule(cls, policy, proposal, start_date):
        frequency = str(proposal.quotation.payment_frequency or "ANNUAL").upper()
        divisor = FREQUENCY_DIVISORS.get(frequency)
        if divisor is None:
            raise ValidationError({"payment_frequency": f"Unsupported payment frequency: {frequency}."})
        term = cls._term_years(proposal)
        annual_premium = cls._annual_premium(proposal)
        installment_count = term * divisor
        total_premium = (annual_premium * term).quantize(MONEY_QUANTUM)
        schedule = OLPremiumSchedule.objects.create(
            policy=policy,
            frequency=frequency,
            currency=policy.currency,
            total_premium=total_premium,
            installment_count=installment_count,
            effective_from=start_date,
            effective_to=policy.end_date,
            is_current=True,
        )
        installment_amount = (annual_premium / Decimal(divisor)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        for sequence in range(1, installment_count + 1):
            due_date = cls._add_months(start_date, (sequence - 1) * (12 // divisor))
            if sequence == installment_count:
                due_date = min(due_date, policy.end_date)
            installment = OLPremiumInstallment.objects.create(
                schedule=schedule,
                sequence=sequence,
                due_date=due_date,
                amount=installment_amount,
                status="DUE",
            )
            OLPaymentObligation.objects.create(
                policy=policy,
                installment=installment,
                obligation_type="INSTALMENT",
                amount=installment_amount,
                currency=policy.currency,
                due_date=due_date,
                status="DUE",
            )
        return schedule

    @classmethod
    @transaction.atomic
    def issue_policy(cls, proposal, actor=None, start_date=None, beneficiary_allocations=None, reason="", idempotency_key=None):
        actor = cls._require_actor(actor)
        proposal = (
            proposal.__class__.objects.select_for_update()
            .select_related("quotation", "quotation_version", "quotation_version__product_version")
            .get(pk=proposal.pk)
        )
        existing = OLPolicy.objects.filter(proposal=proposal).first()
        if existing:
            return existing
        if proposal.status not in {"READY_FOR_ISSUANCE"}:
            raise ValidationError({"status": "Only proposals ready for issuance can create a policy."})
        if proposal.underwriting_status != "APPROVED":
            raise ValidationError({"underwriting_status": "Approved underwriting is required for issuance."})
        first_premium = proposal.payment_obligations.filter(obligation_type="FIRST_PREMIUM").first()
        if not first_premium or first_premium.status != "PAID":
            raise ValidationError({"payment": "The first premium must be fully paid before issuance."})
        start_date = start_date or timezone.localdate()
        version = proposal.quotation_version
        term_years = cls._term_years(proposal)
        end_date = cls._add_years(start_date, term_years) - timedelta(days=1)
        parties = cls._application_parties(proposal)
        policy = OLPolicy.objects.create(
            policy_number=NumberingEngine.generate_number("OL_POLICY", OLPolicy, field_name="policy_number"),
            proposal=proposal,
            product_version=version.product_version,
            product_snapshot=version.product_version_snapshot,
            policyholder_partner=parties["policyholder"],
            life_assured_partner=parties["life_assured"],
            policyholder=OrdinaryLifeApplicationService._client_projection(parties["policyholder"]),
            life_assured=OrdinaryLifeApplicationService._client_projection(parties["life_assured"]),
            agent=parties["intermediary"],
            currency=proposal.quotation.currency,
            sum_assured=proposal.quotation.sum_assured,
            premium_amount=proposal.quotation.premium_amount,
            start_date=start_date,
            end_date=end_date,
            status="ACTIVE",
        )
        cls._create_policy_parties(policy, parties, start_date)
        cls._create_beneficiaries(policy, beneficiary_allocations, start_date)
        validate_policy_beneficiary_total(policy)
        cls._create_schedule(policy, proposal, start_date)
        before = {"status": proposal.status}
        proposal.status = "ISSUED"
        proposal.save(update_fields=["status", "updated_at"])
        cls._event(proposal, "ISSUE_POLICY", actor=actor, previous_status="READY_FOR_ISSUANCE", new_status="ISSUED", reason=cls._reason(reason), metadata={"policy_id": str(policy.pk)})
        after = cls._policy_snapshot(policy)
        cls._transaction(
            policy,
            "ISSUANCE",
            actor,
            reason=reason or "Policy issued",
            amount=policy.premium_amount,
            effective_date=start_date,
            before_state=before,
            after_state=after,
            idempotency_key=idempotency_key,
        )
        OLPolicyStatusHistory.objects.create(
            policy=policy,
            previous_status="PENDING_ISSUANCE",
            new_status="ACTIVE",
            reason=cls._reason(reason or "Policy issued"),
            actor=actor,
            correlation_id=cls._source_metadata()["correlation_id"],
        )
        cls._event(policy, "ISSUE_POLICY", actor=actor, previous_status="PENDING_ISSUANCE", new_status="ACTIVE", reason=cls._reason(reason or "Policy issued"), before_state={"status": "PENDING_ISSUANCE"}, after_state=after)
        return policy

    @classmethod
    @transaction.atomic
    def allocate_payment(cls, obligation, amount, external_receipt_reference, actor=None, reason="", metadata=None):
        actor = cls._require_actor(actor)
        obligation = OLPaymentObligation.objects.select_for_update().select_related("proposal", "policy", "installment").get(pk=obligation.pk)
        reference = str(external_receipt_reference or "").strip()
        if not reference:
            raise ValidationError({"external_receipt_reference": "A receipt reference is required."})
        existing = obligation.allocations.filter(external_receipt_reference=reference).first()
        if existing:
            return existing
        if OLPaymentAllocation.objects.filter(external_receipt_reference=reference).exists():
            raise ValidationError({"external_receipt_reference": "This receipt reference is already allocated."})
        allocation_amount = cls._money(amount, "amount")
        remaining = obligation.amount - obligation.allocated_amount
        if allocation_amount > remaining:
            raise ValidationError({"amount": "Payment allocation exceeds the outstanding obligation."})
        allocation = OLPaymentAllocation.objects.create(
            obligation=obligation,
            external_receipt_reference=reference,
            amount=allocation_amount,
            currency=obligation.currency,
            allocated_by=actor,
            metadata=metadata or {},
        )
        new_allocated = (obligation.allocated_amount + allocation_amount).quantize(MONEY_QUANTUM)
        obligation.allocated_amount = new_allocated
        obligation.status = "PAID" if new_allocated == obligation.amount else "PARTIALLY_PAID"
        obligation.save(update_fields=["allocated_amount", "status", "updated_at"])
        if obligation.installment_id:
            installment = obligation.installment
            installment.allocated_amount = new_allocated
            installment.status = "PAID" if new_allocated == installment.amount else "PARTIALLY_PAID"
            installment.save(update_fields=["allocated_amount", "status"])
        cls._event(obligation, "ALLOCATE_PAYMENT", actor=actor, new_status=obligation.status, reason=cls._reason(reason or "Payment allocated"), metadata={"allocation_id": str(allocation.pk), "receipt_reference": reference, "amount": str(allocation_amount)})
        proposal = obligation.proposal
        if proposal and obligation.obligation_type == "FIRST_PREMIUM" and obligation.status == "PAID" and proposal.status == "APPROVED":
            previous = proposal.status
            proposal.status = "READY_FOR_ISSUANCE"
            proposal.save(update_fields=["status", "updated_at"])
            cls._event(proposal, "FIRST_PREMIUM_PAID", actor=actor, previous_status=previous, new_status=proposal.status, reason="First premium fully allocated", metadata={"obligation_id": str(obligation.pk)})
        return allocation

    @classmethod
    @transaction.atomic
    def mark_overdue_installments(cls, as_of=None, actor=None):
        actor = cls._require_actor(actor)
        as_of = as_of or timezone.localdate()
        count = 0
        for installment in OLPremiumInstallment.objects.select_for_update().select_related("schedule__policy").filter(
            due_date__lt=as_of,
            status__in=["DUE", "PARTIALLY_PAID"],
            schedule__policy__status="ACTIVE",
        ):
            installment.status = "OVERDUE"
            installment.save(update_fields=["status"])
            count += 1
            cls._event(installment, "MARK_INSTALLMENT_OVERDUE", actor=actor, previous_status="DUE", new_status="OVERDUE", reason="Installment passed its due date", metadata={"due_date": str(installment.due_date)})
        return count

    @classmethod
    @transaction.atomic
    def lapse_policy(cls, policy, actor=None, as_of=None, reason="", idempotency_key=None):
        actor = cls._require_actor(actor)
        policy = OLPolicy.objects.select_for_update().get(pk=policy.pk)
        as_of = as_of or timezone.localdate()
        if as_of <= policy.start_date:
            raise ValidationError({"as_of": "A policy cannot lapse before its effective date."})
        overdue = policy.payment_obligations.filter(due_date__lt=as_of, status__in=["DUE", "PARTIALLY_PAID"]).exists()
        if not overdue:
            raise ValidationError({"payment": "The policy has no overdue unpaid premium obligation."})
        policy, _posted = cls._transition(policy, "LAPSED", "LAPSE_POLICY", actor, reason=cls._reason(reason, required=True), allowed={"ACTIVE", "GRACE"}, effective_date=as_of, transaction_type="STATUS_CHANGE", idempotency_key=idempotency_key)
        return policy

    @classmethod
    @transaction.atomic
    def cancel_policy(cls, policy, actor=None, effective_date=None, reason="", idempotency_key=None):
        actor = cls._require_actor(actor)
        policy = OLPolicy.objects.select_for_update().get(pk=policy.pk)
        effective_date = effective_date or timezone.localdate()
        if effective_date < policy.start_date:
            raise ValidationError({"effective_date": "Cancellation cannot precede policy commencement."})
        policy, _posted = cls._transition(policy, "CANCELLED", "CANCEL_POLICY", actor, reason=cls._reason(reason, required=True), allowed={"ACTIVE", "GRACE", "LAPSED"}, effective_date=effective_date, transaction_type="CANCELLATION", idempotency_key=idempotency_key)
        return policy

    @classmethod
    @transaction.atomic
    def request_endorsement(cls, policy, endorsement_type, requested_changes, requested_effective_date=None, actor=None, reason=""):
        actor = cls._require_actor(actor)
        policy = OLPolicy.objects.select_for_update().get(pk=policy.pk)
        if policy.status not in {"ACTIVE", "GRACE"}:
            raise ValidationError({"status": "Only active policies can receive endorsements."})
        changes = requested_changes if isinstance(requested_changes, dict) else {}
        if not changes:
            raise ValidationError({"requested_changes": "At least one controlled policy change is required."})
        effective_date = requested_effective_date or timezone.localdate()
        if effective_date < policy.start_date:
            raise ValidationError({"requested_effective_date": "The endorsement date cannot precede policy commencement."})
        endorsement = OLEndorsement.objects.create(
            endorsement_number=NumberingEngine.generate_number("OL_ENDORSEMENT", OLEndorsement, field_name="endorsement_number"),
            policy=policy,
            endorsement_type=str(endorsement_type or "GENERAL").upper(),
            requested_effective_date=effective_date,
            requested_changes=changes,
            reason=cls._reason(reason, required=True),
            before_snapshot=cls._policy_snapshot(policy),
            created_by=actor,
        )
        cls._event(endorsement, "CREATE_ENDORSEMENT", actor=actor, new_status=endorsement.status, reason=endorsement.reason, metadata={"policy_id": str(policy.pk)})
        return endorsement

    @classmethod
    @transaction.atomic
    def submit_endorsement(cls, endorsement, actor=None, reason=""):
        actor = cls._require_actor(actor)
        endorsement = OLEndorsement.objects.select_for_update().get(pk=endorsement.pk)
        if endorsement.status != "DRAFT":
            raise ValidationError({"status": "Only draft endorsements can be submitted."})
        previous = endorsement.status
        endorsement.status = "PENDING_APPROVAL"
        endorsement.save(update_fields=["status", "updated_at"])
        cls._event(endorsement, "SUBMIT_ENDORSEMENT", actor=actor, previous_status=previous, new_status=endorsement.status, reason=cls._reason(reason or endorsement.reason))
        return endorsement

    @classmethod
    @transaction.atomic
    def approve_endorsement(cls, endorsement, actor=None, reason=""):
        actor = cls._require_actor(actor)
        endorsement = OLEndorsement.objects.select_for_update().get(pk=endorsement.pk)
        if endorsement.status != "PENDING_APPROVAL":
            raise ValidationError({"status": "Only pending endorsements can be approved."})
        endorsement.status = "APPROVED"
        endorsement.approved_by = actor
        endorsement.approved_at = timezone.now()
        endorsement.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        cls._event(endorsement, "APPROVE_ENDORSEMENT", actor=actor, previous_status="PENDING_APPROVAL", new_status="APPROVED", reason=cls._reason(reason, required=True))
        return endorsement

    @classmethod
    @transaction.atomic
    def apply_endorsement(cls, endorsement, actor=None, reason="", idempotency_key=None):
        actor = cls._require_actor(actor)
        endorsement = OLEndorsement.objects.select_for_update().select_related("policy").get(pk=endorsement.pk)
        if endorsement.status == "APPLIED":
            return endorsement
        if endorsement.status != "APPROVED":
            raise ValidationError({"status": "Only approved endorsements can be applied."})
        policy = OLPolicy.objects.select_for_update().get(pk=endorsement.policy_id)
        if policy.status not in {"ACTIVE", "GRACE"}:
            raise ValidationError({"policy": "The policy must be active or in grace for endorsement application."})
        allowed = {"sum_assured", "premium_amount", "end_date", "currency"}
        unknown = sorted(set(endorsement.requested_changes) - allowed)
        if unknown:
            raise ValidationError({"requested_changes": f"Unsupported endorsement fields: {', '.join(unknown)}."})
        before = cls._policy_snapshot(policy)
        changed_fields = []
        for field, value in endorsement.requested_changes.items():
            if field in {"sum_assured", "premium_amount"}:
                value = cls._money(value, field)
            elif field == "end_date":
                try:
                    value = date.fromisoformat(str(value))
                except ValueError:
                    raise ValidationError({"end_date": "End date must be an ISO date."}) from None
                if value <= policy.start_date:
                    raise ValidationError({"end_date": "End date must follow policy commencement."})
            elif field == "currency":
                value = str(value).upper()
                if len(value) != 3:
                    raise ValidationError({"currency": "Currency must be a three-letter code."})
            setattr(policy, field, value)
            changed_fields.append(field)
        policy.save(update_fields=changed_fields + ["updated_at"])
        after = cls._policy_snapshot(policy)
        posted = cls._transaction(policy, "ENDORSEMENT", actor, reason=reason or endorsement.reason, effective_date=endorsement.requested_effective_date, before_state=before, after_state=after, idempotency_key=idempotency_key)
        endorsement.status = "APPLIED"
        endorsement.applied_at = timezone.now()
        endorsement.applied_transaction = posted
        endorsement.before_snapshot = before
        endorsement.after_snapshot = after
        endorsement.save(update_fields=["status", "applied_at", "applied_transaction", "before_snapshot", "after_snapshot", "updated_at"])
        cls._event(endorsement, "APPLY_ENDORSEMENT", actor=actor, previous_status="APPROVED", new_status="APPLIED", reason=cls._reason(reason or endorsement.reason), metadata={"transaction_id": str(posted.pk), "changed_fields": changed_fields}, before_state=before, after_state=after)
        return endorsement

    @classmethod
    @transaction.atomic
    def request_renewal(cls, policy, requested_effective_date=None, new_end_date=None, actor=None, reason=""):
        actor = cls._require_actor(actor)
        policy = OLPolicy.objects.select_for_update().get(pk=policy.pk)
        if policy.status not in {"ACTIVE", "MATURED"}:
            raise ValidationError({"status": "Only active or matured policies can be renewed."})
        effective = requested_effective_date or policy.end_date + timedelta(days=1)
        new_end = new_end_date or cls._add_years(effective, max((policy.end_date - policy.start_date).days // 365, 1)) - timedelta(days=1)
        if effective <= policy.end_date or new_end <= effective:
            raise ValidationError({"requested_effective_date": "Renewal must begin after the current policy term and have a later end date."})
        renewal = OLPolicyRenewal.objects.create(
            renewal_number=NumberingEngine.generate_number("OL_RENEWAL", OLPolicyRenewal, field_name="renewal_number"),
            policy=policy,
            requested_effective_date=effective,
            new_end_date=new_end,
            premium_amount=cls._money(policy.premium_amount, "premium_amount"),
            currency=policy.currency,
            reason=cls._reason(reason, required=True),
            before_snapshot=cls._policy_snapshot(policy),
            created_by=actor,
        )
        cls._event(renewal, "CREATE_RENEWAL", actor=actor, new_status=renewal.status, reason=renewal.reason, metadata={"policy_id": str(policy.pk)})
        return renewal

    @classmethod
    @transaction.atomic
    def submit_renewal(cls, renewal, actor=None, reason=""):
        actor = cls._require_actor(actor)
        renewal = OLPolicyRenewal.objects.select_for_update().get(pk=renewal.pk)
        if renewal.status != "DRAFT":
            raise ValidationError({"status": "Only draft renewals can be submitted."})
        renewal.status = "SUBMITTED"
        renewal.save(update_fields=["status", "updated_at"])
        cls._event(renewal, "SUBMIT_RENEWAL", actor=actor, previous_status="DRAFT", new_status="SUBMITTED", reason=cls._reason(reason or renewal.reason))
        return renewal

    @classmethod
    @transaction.atomic
    def approve_renewal(cls, renewal, actor=None, reason=""):
        actor = cls._require_actor(actor)
        renewal = OLPolicyRenewal.objects.select_for_update().select_related("policy").get(pk=renewal.pk)
        if renewal.status != "SUBMITTED":
            raise ValidationError({"status": "Only submitted renewals can be approved."})
        obligation = renewal.payment_obligation
        if obligation is None:
            obligation = OLPaymentObligation.objects.create(
                policy=renewal.policy,
                obligation_type="RENEWAL_PREMIUM",
                amount=renewal.premium_amount,
                currency=renewal.currency,
                due_date=renewal.requested_effective_date,
                status="DUE",
            )
        renewal.payment_obligation = obligation
        renewal.status = "APPROVED"
        renewal.approved_by = actor
        renewal.approved_at = timezone.now()
        renewal.save(update_fields=["payment_obligation", "status", "approved_by", "approved_at", "updated_at"])
        cls._event(renewal, "APPROVE_RENEWAL", actor=actor, previous_status="SUBMITTED", new_status="APPROVED", reason=cls._reason(reason, required=True), metadata={"payment_obligation_id": str(obligation.pk)})
        return renewal

    @classmethod
    @transaction.atomic
    def apply_renewal(cls, renewal, actor=None, reason="", idempotency_key=None):
        actor = cls._require_actor(actor)
        renewal = OLPolicyRenewal.objects.select_for_update().select_related("policy", "payment_obligation").get(pk=renewal.pk)
        if renewal.status == "APPLIED":
            return renewal
        if renewal.status != "APPROVED":
            raise ValidationError({"status": "Only approved renewals can be applied."})
        if not renewal.payment_obligation_id or renewal.payment_obligation.status != "PAID":
            raise ValidationError({"payment": "The renewal premium must be fully paid before application."})
        policy = OLPolicy.objects.select_for_update().get(pk=renewal.policy_id)
        before = cls._policy_snapshot(policy)
        policy.end_date = renewal.new_end_date
        if policy.status == "MATURED":
            policy.status = "ACTIVE"
        policy.save(update_fields=["end_date", "status", "updated_at"])
        after = cls._policy_snapshot(policy)
        posted = cls._transaction(policy, "RENEWAL", actor, reason=reason or renewal.reason, amount=renewal.premium_amount, effective_date=renewal.requested_effective_date, before_state=before, after_state=after, idempotency_key=idempotency_key)
        renewal.status = "APPLIED"
        renewal.applied_at = timezone.now()
        renewal.applied_transaction = posted
        renewal.after_snapshot = after
        renewal.save(update_fields=["status", "applied_at", "applied_transaction", "after_snapshot", "updated_at"])
        cls._event(renewal, "APPLY_RENEWAL", actor=actor, previous_status="APPROVED", new_status="APPLIED", reason=cls._reason(reason or renewal.reason), metadata={"transaction_id": str(posted.pk)}, before_state=before, after_state=after)
        return renewal

    @classmethod
    @transaction.atomic
    def request_reinstatement(cls, policy, requested_effective_date=None, actor=None, reason=""):
        actor = cls._require_actor(actor)
        policy = OLPolicy.objects.select_for_update().get(pk=policy.pk)
        if policy.status not in {"LAPSED", "CANCELLED"}:
            raise ValidationError({"status": "Only lapsed or eligible cancelled policies can be reinstated."})
        as_of = requested_effective_date or timezone.localdate()
        arrears = policy.payment_obligations.filter(status__in=["DUE", "PARTIALLY_PAID"], due_date__lte=as_of).aggregate(total=Sum("amount"), allocated=Sum("allocated_amount"))
        arrears_amount = (arrears["total"] or Decimal("0")) - (arrears["allocated"] or Decimal("0"))
        if arrears_amount <= 0:
            raise ValidationError({"arrears": "No outstanding premium arrears require reinstatement."})
        request = OLReinstatementRequest.objects.create(
            request_number=NumberingEngine.generate_number("OL_REINSTATEMENT", OLReinstatementRequest, field_name="request_number"),
            policy=policy,
            requested_effective_date=as_of,
            arrears_amount=arrears_amount.quantize(MONEY_QUANTUM),
            currency=policy.currency,
            reason=cls._reason(reason, required=True),
            before_snapshot=cls._policy_snapshot(policy),
            created_by=actor,
        )
        cls._event(request, "CREATE_REINSTATEMENT", actor=actor, new_status=request.status, reason=request.reason, metadata={"policy_id": str(policy.pk), "arrears_amount": str(request.arrears_amount)})
        return request

    @classmethod
    @transaction.atomic
    def submit_reinstatement(cls, request, actor=None, reason=""):
        actor = cls._require_actor(actor)
        request = OLReinstatementRequest.objects.select_for_update().get(pk=request.pk)
        if request.status != "DRAFT":
            raise ValidationError({"status": "Only draft reinstatement requests can be submitted."})
        request.status = "SUBMITTED"
        request.save(update_fields=["status", "updated_at"])
        cls._event(request, "SUBMIT_REINSTATEMENT", actor=actor, previous_status="DRAFT", new_status="SUBMITTED", reason=cls._reason(reason or request.reason))
        return request

    @classmethod
    @transaction.atomic
    def approve_reinstatement(cls, request, actor=None, reason=""):
        actor = cls._require_actor(actor)
        request = OLReinstatementRequest.objects.select_for_update().select_related("policy").get(pk=request.pk)
        if request.status != "SUBMITTED":
            raise ValidationError({"status": "Only submitted reinstatement requests can be approved."})
        obligation = request.payment_obligation
        if obligation is None:
            obligation = OLPaymentObligation.objects.create(
                policy=request.policy,
                obligation_type="INSTALMENT",
                amount=request.arrears_amount,
                currency=request.currency,
                due_date=request.requested_effective_date,
                status="DUE",
            )
        request.payment_obligation = obligation
        request.status = "APPROVED"
        request.approved_by = actor
        request.approved_at = timezone.now()
        request.save(update_fields=["payment_obligation", "status", "approved_by", "approved_at", "updated_at"])
        cls._event(request, "APPROVE_REINSTATEMENT", actor=actor, previous_status="SUBMITTED", new_status="APPROVED", reason=cls._reason(reason, required=True), metadata={"payment_obligation_id": str(obligation.pk)})
        return request

    @classmethod
    @transaction.atomic
    def apply_reinstatement(cls, request, actor=None, reason="", idempotency_key=None):
        actor = cls._require_actor(actor)
        request = OLReinstatementRequest.objects.select_for_update().select_related("policy", "payment_obligation").get(pk=request.pk)
        if request.status == "APPLIED":
            return request
        if request.status != "APPROVED":
            raise ValidationError({"status": "Only approved reinstatement requests can be applied."})
        if not request.payment_obligation_id or request.payment_obligation.status != "PAID":
            raise ValidationError({"payment": "Reinstatement arrears must be fully paid before application."})
        policy = OLPolicy.objects.select_for_update().get(pk=request.policy_id)
        if policy.status not in {"LAPSED", "CANCELLED"}:
            raise ValidationError({"policy": "The policy is no longer eligible for reinstatement."})
        before = cls._policy_snapshot(policy)
        policy.status = "ACTIVE"
        policy.save(update_fields=["status", "updated_at"])
        after = cls._policy_snapshot(policy)
        posted = cls._transaction(policy, "REINSTATEMENT", actor, reason=reason or request.reason, amount=request.arrears_amount, effective_date=request.requested_effective_date, before_state=before, after_state=after, idempotency_key=idempotency_key)
        request.status = "APPLIED"
        request.applied_at = timezone.now()
        request.applied_transaction = posted
        request.after_snapshot = after
        request.save(update_fields=["status", "applied_at", "applied_transaction", "after_snapshot", "updated_at"])
        cls._event(request, "APPLY_REINSTATEMENT", actor=actor, previous_status="APPROVED", new_status="APPLIED", reason=cls._reason(reason or request.reason), metadata={"transaction_id": str(posted.pk)}, before_state=before, after_state=after)
        return request

    @classmethod
    @transaction.atomic
    def mature_policy(cls, policy, actor=None, as_of=None, reason="", idempotency_key=None):
        actor = cls._require_actor(actor)
        policy = OLPolicy.objects.select_for_update().get(pk=policy.pk)
        as_of = as_of or timezone.localdate()
        if as_of < policy.end_date:
            raise ValidationError({"as_of": "A policy cannot mature before its contractual end date."})
        policy, _posted = cls._transition(policy, "MATURED", "MATURE_POLICY", actor, reason=cls._reason(reason or "Policy reached contractual maturity", required=True), allowed={"ACTIVE"}, effective_date=as_of, transaction_type="MATURITY", idempotency_key=idempotency_key)
        return policy

    @classmethod
    @transaction.atomic
    def grace_policy(cls, policy, actor=None, reason="", idempotency_key=None):
        actor = cls._require_actor(actor)
        policy = OLPolicy.objects.select_for_update().get(pk=policy.pk)
        policy, _posted = cls._transition(policy, "GRACE", "ENTER_GRACE", actor, reason=cls._reason(reason, required=True), allowed={"ACTIVE"}, transaction_type="STATUS_CHANGE", idempotency_key=idempotency_key)
        return policy

    @classmethod
    @transaction.atomic
    def reactivate_policy(cls, policy, actor=None, reason="", idempotency_key=None):
        actor = cls._require_actor(actor)
        policy = OLPolicy.objects.select_for_update().get(pk=policy.pk)
        if policy.status not in {"GRACE", "LAPSED"}:
            raise ValidationError({"status": "Only grace or lapsed policies can be reactivated through this operation."})
        if policy.payment_obligations.filter(due_date__lte=timezone.localdate(), status__in=["DUE", "PARTIALLY_PAID"]).exists():
            raise ValidationError({"payment": "Outstanding due obligations must be resolved before reactivation."})
        policy, _posted = cls._transition(policy, "ACTIVE", "REACTIVATE_POLICY", actor, reason=cls._reason(reason, required=True), allowed={"GRACE", "LAPSED"}, transaction_type="STATUS_CHANGE", idempotency_key=idempotency_key)
        return policy


# Public alias used by views and future modules.
OrdinaryLifeWorkflowService = OrdinaryLifePolicyService
