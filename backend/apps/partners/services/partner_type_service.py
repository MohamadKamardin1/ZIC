import logging

from django.db import transaction
from django.core.exceptions import ValidationError

from apps.partners.models import PartnerTypeAssignment, PartnerTypeAssignmentHistory
from apps.partners.services.setup_service import PartnerSetupService
from apps.governance.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class PartnerTypeAssignmentService:

    @staticmethod
    def _get_current_user():
        ctx = AuditService.get_context() if hasattr(AuditService, "get_context") else {}
        user = ctx.get("user") if isinstance(ctx, dict) else None
        return user if user and not user.is_anonymous else None

    @staticmethod
    @transaction.atomic
    def assign(partner, partner_type, branch=None, location=None, share_data_externally=False, effective_date=None):
        if location and branch and location.branch_id != branch.id:
            raise ValidationError(
                {"location": "Location branch must match the selected Branch."}
            )

        existing = PartnerTypeAssignment.objects.filter(
            partner=partner, partner_type=partner_type,
        ).first()
        previous_status = existing.status if existing else None

        assignment, created = PartnerTypeAssignment.objects.update_or_create(
            partner=partner,
            partner_type=partner_type,
            defaults={
                "branch": branch,
                "location": location,
                "share_data_externally": share_data_externally,
                "status": "ACTIVE",
                "effective_date": effective_date,
            },
        )

        if created:
            PartnerSetupService.generate_setup(assignment)
            PartnerTypeAssignmentHistory.objects.create(
                assignment=assignment,
                previous_status="",
                new_status="ACTIVE",
                reason="Partner type assigned.",
                changed_by=PartnerTypeAssignmentService._get_current_user(),
            )
        elif previous_status and previous_status != assignment.status:
            PartnerTypeAssignmentHistory.objects.create(
                assignment=assignment,
                previous_status=previous_status,
                new_status=assignment.status,
                reason="Partner type assignment updated.",
                changed_by=PartnerTypeAssignmentService._get_current_user(),
            )

        AuditService.log(
            action_type="ASSIGN",
            entity_type="PartnerTypeAssignment",
            entity_id=assignment.pk,
            entity_repr=str(assignment),
            description=f"{'Created' if created else 'Updated'} assignment for {partner.partner_number}",
        )

        logger.info(
            "%s PartnerTypeAssignment for %s — %s",
            "Created" if created else "Updated",
            partner.partner_number,
            partner_type.name,
        )
        return assignment

    @staticmethod
    @transaction.atomic
    def deactivate(assignment, reason=""):
        previous_status = assignment.status
        assignment.status = "INACTIVE"
        assignment.save(update_fields=["status", "updated_at"])

        PartnerTypeAssignmentHistory.objects.create(
            assignment=assignment,
            previous_status=previous_status,
            new_status="INACTIVE",
            reason=reason or "Assignment deactivated.",
            changed_by=PartnerTypeAssignmentService._get_current_user(),
        )

        AuditService.log(
            action_type="DEACTIVATE",
            entity_type="PartnerTypeAssignment",
            entity_id=assignment.pk,
            entity_repr=str(assignment),
            description=f"Deactivated assignment for {assignment.partner.partner_number}: {reason}",
        )

        logger.info(
            "Deactivated PartnerTypeAssignment: %s — %s",
            assignment.partner.partner_number,
            assignment.partner_type.name,
        )
        return assignment

    @staticmethod
    @transaction.atomic
    def reactivate(assignment, reason=""):
        previous_status = assignment.status
        assignment.status = "ACTIVE"
        assignment.save(update_fields=["status", "updated_at"])

        PartnerTypeAssignmentHistory.objects.create(
            assignment=assignment,
            previous_status=previous_status,
            new_status="ACTIVE",
            reason=reason or "Assignment reactivated.",
            changed_by=PartnerTypeAssignmentService._get_current_user(),
        )

        AuditService.log(
            action_type="ACTIVATE",
            entity_type="PartnerTypeAssignment",
            entity_id=assignment.pk,
            entity_repr=str(assignment),
            description=f"Reactivated assignment for {assignment.partner.partner_number}: {reason}",
        )
        return assignment

    @staticmethod
    def get_active_assignments(partner):
        return partner.type_assignments.filter(status="ACTIVE").select_related(
            "partner_type", "branch", "location"
        )

    @staticmethod
    def get_by_partner(partner):
        return partner.type_assignments.all().select_related(
            "partner_type", "branch", "location"
        )
