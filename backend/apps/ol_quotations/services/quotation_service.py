from datetime import date
from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.common.models import DomainEvent
from apps.governance.services.audit_service import AuditService
from apps.system_parameters.services.config_service import ConfigurationService
from apps.system_parameters.services.numbering_service import NumberingEngine

from apps.ol_quotations.models import (
    OLQuotation,
    OLQuotationEvent,
    OLQuotationFinancialSummary,
    OLQuotationVersion,
    QuotationStatus,
)


class QuotationServiceError(ValidationError):
    """A domain validation or lifecycle error for quotation workflows."""


class QuotationService:
    MODULE = "ol_quotations"

    @staticmethod
    def actor(user):
        return user if user and not getattr(user, "is_anonymous", False) else None

    @staticmethod
    def default_currency():
        value = ConfigurationService.get_str_parameter("DEFAULT_CURRENCY", "TZS")
        value = (value or "TZS").strip().upper()
        return value if len(value) == 3 and value.isalpha() else "TZS"

    @staticmethod
    def generate_quote_number():
        return NumberingEngine.generate_number(
            numbering_code="OL_QUOTATION",
            model_class=OLQuotation,
            field_name="quote_number",
        )

    @staticmethod
    def snapshot(quotation):
        return {
            "id": str(quotation.pk),
            "quote_number": quotation.quote_number,
            "quote_name": quotation.quote_name,
            "quote_date": quotation.quote_date.isoformat() if quotation.quote_date else None,
            "status": quotation.status,
            "partner_id": str(quotation.partner_id) if quotation.partner_id else None,
            "linked_partner_id": str(quotation.linked_partner_id) if quotation.linked_partner_id else None,
            "product_id": str(quotation.product_id) if quotation.product_id else None,
            "product_version_id": str(quotation.product_version_id) if quotation.product_version_id else None,
            "product_selection_ids": [str(pk) for pk in quotation.products.filter(is_selected=True).values_list("pk", flat=True)],
            "currency": quotation.currency,
            "current_version_number": quotation.current_version_number,
            "wizard_step_completion": quotation.wizard_step_completion or {},
            "identity_type": quotation.identity_type,
            "identity_number": quotation.identity_number,
            "date_of_birth": quotation.date_of_birth.isoformat() if quotation.date_of_birth else None,
            "age_at_quote": quotation.age_at_quote,
            "gender": quotation.gender,
            "smoker_status": quotation.smoker_status,
            "location": quotation.location,
            "agent_id": str(quotation.agent_id) if quotation.agent_id else None,
            "address": quotation.address,
            "partner_verified": quotation.partner_verified,
            "approval_required": quotation.approval_required,
            "expiry_date": quotation.expiry_date.isoformat() if quotation.expiry_date else None,
            "total_sum_assured": str(quotation.total_sum_assured) if quotation.total_sum_assured is not None else None,
            "total_premium": str(quotation.total_premium) if quotation.total_premium is not None else None,
            "calculation_snapshot": quotation.calculation_snapshot or {},
        }

    @staticmethod
    def wizard_completion(quotation):
        selected_plan = (
            quotation.plan_configurations.filter(is_selected=True).exists()
            or quotation.products.filter(is_selected=True).exists()
        )
        members = quotation.members.exists()
        selected_installments = quotation.installment_configurations.filter(is_selected=True).exists()
        funds = quotation.fund_allocations.filter(is_selected=True)
        fund_complete = not funds.exists() or funds.aggregate(total=models.Sum("allocation_percentage"))["total"] == Decimal("100")
        riders_or_benefits = not quotation.rider_selections.filter(is_selected=True).exists() and not quotation.benefits.filter(is_selected=True).exists()
        if quotation.rider_selections.filter(is_selected=True).exists() or quotation.benefits.filter(is_selected=True).exists():
            riders_or_benefits = True
        payment = hasattr(quotation, "payment_detail")
        underwriting = hasattr(quotation, "underwriting_detail")
        personal_details = bool(
            quotation.quote_name
            or quotation.identity_type
            or quotation.identity_number
            or quotation.date_of_birth
            or quotation.partner_id
            or quotation.linked_partner_id
            or quotation.agent_id
            or quotation.address
            or quotation.location
        )
        return {
            "1_personal_details": personal_details,
            "2_plan_and_sub_products": selected_plan,
            "3_member_coverage": members,
            "4_installments": selected_installments,
            "5_investment_funds": fund_complete,
            "6_riders_and_benefits": riders_or_benefits,
            "7_financial_details": payment and underwriting,
        }

    @staticmethod
    def _record_version(quotation, actor=None, reason=""):
        snapshot = QuotationService.snapshot(quotation)
        return OLQuotationVersion.objects.create(
            quotation=quotation,
            version_number=quotation.current_version_number,
            status=quotation.status,
            snapshot=snapshot,
            change_reason=reason or "Quotation version captured.",
            created_by=QuotationService.actor(actor),
            updated_by=QuotationService.actor(actor),
        )

    @staticmethod
    def _record_event(
        quotation,
        event_type,
        actor=None,
        from_status="",
        to_status="",
        notes="",
        metadata=None,
        before_state=None,
        after_state=None,
        request=None,
    ):
        event = OLQuotationEvent.objects.create(
            quotation=quotation,
            event_type=event_type,
            from_status=from_status or "",
            to_status=to_status or "",
            actor=QuotationService.actor(actor),
            notes=notes or "",
            metadata=metadata or {},
        )
        AuditService.log_action(
            action=event_type,
            instance=quotation,
            actor=actor,
            request=request,
            before_state=before_state,
            after_state=after_state,
            changed_fields=AuditService.changed_fields(before_state or {}, after_state or {}),
            reason=notes or event_type.replace("_", " ").title(),
        )
        DomainEvent.objects.create(
            event_type=f"Quotation{event_type.title().replace('_', '')}",
            aggregate_type="OLQuotation",
            aggregate_id=str(quotation.pk),
            payload={
                "quote_number": quotation.quote_number,
                "quotation_id": str(quotation.pk),
                "actor_id": str(actor.pk) if actor and getattr(actor, "pk", None) else None,
                "from_status": from_status or "",
                "to_status": to_status or "",
                "metadata": metadata or {},
            },
        )
        return event

    @staticmethod
    def validate_wizard(quotation):
        errors = {}
        if not (
            quotation.plan_configurations.filter(is_selected=True).exists()
            or quotation.products.filter(is_selected=True).exists()
        ):
            errors["plan_configuration"] = "At least one selected product or plan configuration is required."
        if not quotation.members.exists():
            errors["members"] = "At least one quotation member is required."
        elif not quotation.members.filter(member_type="LIFE_ASSURED").exists():
            errors["life_assured"] = "At least one life assured member is required."
        if not quotation.installment_configurations.filter(is_selected=True).exists():
            errors["installments"] = "At least one selected installment configuration is required."
        if quotation.fund_allocations.filter(is_selected=True).exists():
            total_allocated = quotation.fund_allocations.filter(is_selected=True).aggregate(
                total=models.Sum("allocation_percentage")
            )["total"] or Decimal("0")
            if total_allocated != Decimal("100"):
                errors["fund_allocations"] = "Selected fund allocation percentages must total exactly 100."
        if quotation.beneficiaries.exists():
            beneficiary_total = quotation.beneficiaries.aggregate(
                total=models.Sum("percentage")
            )["total"] or Decimal("0")
            if beneficiary_total != Decimal("100"):
                errors["beneficiaries"] = "Beneficiary percentages must total exactly 100."
        underwriting = getattr(quotation, "underwriting_detail", None)
        if underwriting is None:
            errors["underwriting"] = "Underwriting answers must be captured before finalization."
        payment = getattr(quotation, "payment_detail", None)
        if payment is None:
            errors["payment_detail"] = "Payment details must be captured before finalization."
        if errors:
            raise QuotationServiceError({"detail": "Quotation wizard is incomplete.", "errors": errors})
        return True

    @staticmethod
    def calculate_totals(quotation):
        sum_assured = sum(
            (item.base_sum_assured for item in quotation.plan_configurations.filter(is_selected=True)),
            Decimal("0"),
        )
        premium = sum(
            (item.premium_amount or Decimal("0") for item in quotation.plan_configurations.filter(is_selected=True)),
            Decimal("0"),
        )
        premium += sum(
            (item.premium_amount or Decimal("0") for item in quotation.rider_selections.filter(is_selected=True)),
            Decimal("0"),
        )
        premium += sum(
            (item.premium_amount or Decimal("0") for item in quotation.benefits.filter(is_selected=True)),
            Decimal("0"),
        )
        return sum_assured, premium

    @staticmethod
    @transaction.atomic
    def create_draft(*, actor, validated_data, request=None):
        payload = dict(validated_data)
        payload.pop("quote_number", None)
        payload["status"] = QuotationStatus.DRAFT
        payload["currency"] = (payload.get("currency") or QuotationService.default_currency()).upper()
        if payload.get("linked_partner") and not payload.get("partner"):
            payload["partner"] = payload["linked_partner"]
        payload["created_by"] = QuotationService.actor(actor)
        payload["updated_by"] = QuotationService.actor(actor)
        payload["quote_number"] = QuotationService.generate_quote_number()
        quotation = OLQuotation.objects.create(**payload)
        quotation.wizard_step_completion = QuotationService.wizard_completion(quotation)
        quotation.save(update_fields=["wizard_step_completion", "updated_at"])
        after = QuotationService.snapshot(quotation)
        QuotationService._record_version(quotation, actor=actor, reason="Initial quotation draft version.")
        QuotationService._record_event(
            quotation,
            "CREATED",
            actor=actor,
            to_status=QuotationStatus.DRAFT,
            notes="Ordinary Life quotation draft created.",
            after_state=after,
            request=request,
        )
        return quotation

    @staticmethod
    @transaction.atomic
    def update_draft(*, quotation, actor, validated_data, request=None):
        locked = OLQuotation.objects.select_for_update().get(pk=quotation.pk)
        if locked.status != QuotationStatus.DRAFT:
            raise QuotationServiceError("Only draft quotations can be updated.")
        before = QuotationService.snapshot(locked)
        for field, value in validated_data.items():
            setattr(locked, field, value)
        locked.updated_by = QuotationService.actor(actor)
        locked.full_clean(exclude=["quote_number"])
        locked.wizard_step_completion = QuotationService.wizard_completion(locked)
        locked.save()
        after = QuotationService.snapshot(locked)
        if before != after:
            locked.current_version_number += 1
            locked.save(update_fields=["current_version_number", "wizard_step_completion", "updated_at"])
            after = QuotationService.snapshot(locked)
            QuotationService._record_version(locked, actor=actor, reason="Quotation draft updated.")
            QuotationService._record_event(
                locked,
                "UPDATED",
                actor=actor,
                from_status=locked.status,
                to_status=locked.status,
                notes="Ordinary Life quotation draft updated.",
                before_state=before,
                after_state=after,
                request=request,
            )
        return locked

    @staticmethod
    @transaction.atomic
    def transition(*, quotation, target_status, actor, notes="", request=None):
        allowed = {
            QuotationStatus.DRAFT: {QuotationStatus.FINALIZED, QuotationStatus.EXPIRED},
            QuotationStatus.FINALIZED: {QuotationStatus.CONVERTED, QuotationStatus.EXPIRED},
            QuotationStatus.CONVERTED: set(),
            QuotationStatus.EXPIRED: set(),
        }
        locked = OLQuotation.objects.select_for_update().get(pk=quotation.pk)
        if target_status not in allowed.get(locked.status, set()):
            raise QuotationServiceError(
                {
                    "detail": "Quotation status transition is not allowed.",
                    "current_status": locked.status,
                    "requested_status": target_status,
                    "allowed_statuses": sorted(allowed.get(locked.status, set())),
                }
            )
        if target_status == QuotationStatus.FINALIZED:
            QuotationService.validate_wizard(locked)
            total_sum_assured, total_premium = QuotationService.calculate_totals(locked)
            locked.total_sum_assured = total_sum_assured
            locked.total_premium = total_premium
            locked.calculation_snapshot = {
                "calculated_at": timezone.now().isoformat(),
                "currency": locked.currency,
                "total_sum_assured": str(total_sum_assured),
                "total_premium": str(total_premium),
                "plan_configuration_ids": [str(pk) for pk in locked.plan_configurations.filter(is_selected=True).values_list("pk", flat=True)],
                "rider_selection_ids": [str(pk) for pk in locked.rider_selections.filter(is_selected=True).values_list("pk", flat=True)],
                "benefit_ids": [str(pk) for pk in locked.benefits.filter(is_selected=True).values_list("pk", flat=True)],
                "version_number": locked.current_version_number,
            }
        if target_status == QuotationStatus.EXPIRED and locked.expiry_date and locked.expiry_date > date.today():
            raise QuotationServiceError("A quotation cannot be expired before its configured expiry date.")
        before = QuotationService.snapshot(locked)
        locked.status = target_status
        locked.wizard_step_completion = QuotationService.wizard_completion(locked)
        locked.current_version_number += 1
        locked.updated_by = QuotationService.actor(actor)
        locked.save(update_fields=["status", "total_sum_assured", "total_premium", "calculation_snapshot", "wizard_step_completion", "current_version_number", "updated_by", "updated_at"])
        after = QuotationService.snapshot(locked)
        QuotationService._record_version(locked, actor=actor, reason=f"Quotation transitioned to {target_status}.")
        if target_status == QuotationStatus.FINALIZED:
            OLQuotationFinancialSummary.objects.update_or_create(
                quotation=locked,
                defaults={
                    "total_sum_assured": locked.total_sum_assured or Decimal("0"),
                    "total_premium": locked.total_premium or Decimal("0"),
                    "total_rider_premium": sum((item.premium_amount or Decimal("0") for item in locked.rider_selections.filter(is_selected=True)), Decimal("0")),
                    "total_benefit_premium": sum((item.premium_amount or Decimal("0") for item in locked.benefits.filter(is_selected=True)), Decimal("0")),
                    "currency": locked.currency,
                    "calculation_snapshot": locked.calculation_snapshot or {},
                    "created_by": QuotationService.actor(actor),
                    "updated_by": QuotationService.actor(actor),
                },
            )
        QuotationService._record_event(
            locked,
            target_status,
            actor=actor,
            from_status=before["status"],
            to_status=target_status,
            notes=notes or f"Quotation transitioned to {target_status}.",
            before_state=before,
            after_state=after,
            request=request,
        )
        return locked

    @staticmethod
    def ensure_expired(quotation):
        return bool(
            quotation.status in {QuotationStatus.DRAFT, QuotationStatus.FINALIZED}
            and quotation.expiry_date
            and quotation.expiry_date < date.today()
        )
