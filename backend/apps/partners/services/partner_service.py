import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.governance.services.audit_service import AuditContext, AuditService
from apps.partners.models import Partner, PartnerTypeAssignment, PartnerTypeAssignmentHistory

logger = logging.getLogger(__name__)


class PartnerLifecycleService:
    """Domain service for partner and partner-type-assignment lifecycle changes."""

    @staticmethod
    def _current_user():
        user = AuditContext.get_context().get("user")
        return user if user and not user.is_anonymous else None

    @staticmethod
    @transaction.atomic
    def deactivate_partner(partner: Partner, reason: str = "") -> Partner:
        if partner.status == "INACTIVE":
            raise ValidationError("Partner is already inactive.")

        now = timezone.now()
        partner.status = "INACTIVE"
        partner.deactivated_at = now
        partner.deactivation_reason = reason.strip()
        partner.save(update_fields=["status", "deactivated_at", "deactivation_reason", "updated_at"])

        AuditService.log(
            action_type="DEACTIVATE",
            entity_type="Partner",
            entity_id=partner.pk,
            entity_repr=partner.partner_number,
            description=f"Partner {partner.partner_number} deactivated: {reason.strip()}",
            after_state={"status": partner.status, "reason": partner.deactivation_reason},
        )
        logger.info("Partner %s deactivated", partner.partner_number)
        return partner

    @staticmethod
    @transaction.atomic
    def activate_partner(partner: Partner) -> Partner:
        if partner.status == "ACTIVE":
            raise ValidationError("Partner is already active.")

        now = timezone.now()
        partner.status = "ACTIVE"
        partner.activated_at = now
        partner.deactivated_at = None
        partner.deactivation_reason = ""
        partner.save(
            update_fields=[
                "status", "activated_at", "deactivated_at",
                "deactivation_reason", "updated_at",
            ],
        )

        AuditService.log(
            action_type="ACTIVATE",
            entity_type="Partner",
            entity_id=partner.pk,
            entity_repr=partner.partner_number,
            description=f"Partner {partner.partner_number} activated.",
            after_state={"status": partner.status},
        )
        logger.info("Partner %s activated", partner.partner_number)
        return partner

    @staticmethod
    @transaction.atomic
    def change_assignment_status(
        assignment: PartnerTypeAssignment,
        new_status: str,
        reason: str = "",
    ) -> PartnerTypeAssignment:
        allowed = {choice[0] for choice in PartnerTypeAssignment._meta.get_field("status").choices}
        if new_status not in allowed:
            raise ValidationError({"status": f"Unsupported assignment status: {new_status}."})
        if assignment.status == new_status:
            raise ValidationError(f"Assignment is already {new_status.lower()}.")

        previous_status = assignment.status
        assignment.status = new_status
        assignment.save(update_fields=["status", "updated_at"])
        PartnerTypeAssignmentHistory.objects.create(
            assignment=assignment,
            previous_status=previous_status,
            new_status=new_status,
            reason=reason.strip(),
            changed_by=PartnerLifecycleService._current_user(),
        )
        AuditService.log(
            action_type="ACTIVATE" if new_status == "ACTIVE" else "DEACTIVATE",
            entity_type="PartnerTypeAssignment",
            entity_id=assignment.pk,
            entity_repr=str(assignment),
            description=(
                f"Assignment {assignment.pk} changed from {previous_status} to {new_status}: "
                f"{reason.strip()}"
            ),
            before_state={"status": previous_status},
            after_state={"status": new_status, "reason": reason.strip()},
        )
        return assignment

    @staticmethod
    def deactivate_assignment(assignment: PartnerTypeAssignment, reason: str = ""):
        return PartnerLifecycleService.change_assignment_status(assignment, "INACTIVE", reason)

    @staticmethod
    def activate_assignment(assignment: PartnerTypeAssignment, reason: str = ""):
        return PartnerLifecycleService.change_assignment_status(assignment, "ACTIVE", reason)
