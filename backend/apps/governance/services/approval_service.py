import logging

from django.db import transaction
from django.utils import timezone

from apps.governance.models import ApprovalRequest, APPROVAL_STATUS_CHOICES
from apps.governance.services.audit_service import AuditService
from apps.governance.signals import approval_status_changed

logger = logging.getLogger(__name__)


class ApprovalService:

    @staticmethod
    @transaction.atomic
    def submit(
        module, entity_type, entity_id, action,
        requested_data=None, current_data=None,
        entity_repr="", submitted_by=None, comments="",
    ):
        approval = ApprovalRequest.objects.create(
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_repr=str(entity_repr)[:255] if entity_repr else "",
            action=action,
            requested_data=requested_data,
            current_data=current_data,
            status="PENDING",
            submitted_by=submitted_by,
            comments=comments,
        )
        AuditService.log(
            action_type="SUBMIT",
            entity_type="ApprovalRequest",
            entity_id=approval.pk,
            entity_repr=str(approval),
            after_state={"status": "PENDING", "module": module, "action": action},
            description=f"Approval submitted for {entity_type}[{entity_id}]: {action}",
        )
        logger.info(
            "Approval %s submitted for %s[%s]: %s by %s",
            approval.pk, entity_type, entity_id, action,
            submitted_by.email if submitted_by else "system",
        )
        return approval

    @staticmethod
    @transaction.atomic
    def approve(approval_id, reviewed_by, comments=""):
        approval = ApprovalRequest.objects.select_for_update().get(pk=approval_id)
        if approval.status != "PENDING":
            raise ValueError(f"Cannot approve: current status is {approval.status}")

        approval.status = "APPROVED"
        approval.reviewed_by = reviewed_by
        approval.reviewed_at = timezone.now()
        if comments:
            approval.comments = comments
        approval.save()

        AuditService.log(
            action_type="APPROVE",
            entity_type="ApprovalRequest",
            entity_id=approval.pk,
            entity_repr=str(approval),
            before_state={"status": "PENDING"},
            after_state={"status": "APPROVED"},
            description=f"Approval {approval.pk} approved by {reviewed_by.email}",
        )
        approval_status_changed.send(sender=ApprovalRequest, approval_request=approval)
        logger.info("Approval %s approved by %s", approval.pk, reviewed_by.email)
        return approval

    @staticmethod
    @transaction.atomic
    def reject(approval_id, reviewed_by, comments=""):
        approval = ApprovalRequest.objects.select_for_update().get(pk=approval_id)
        if approval.status != "PENDING":
            raise ValueError(f"Cannot reject: current status is {approval.status}")

        approval.status = "REJECTED"
        approval.reviewed_by = reviewed_by
        approval.reviewed_at = timezone.now()
        approval.comments = comments
        approval.save()

        AuditService.log(
            action_type="REJECT",
            entity_type="ApprovalRequest",
            entity_id=approval.pk,
            entity_repr=str(approval),
            before_state={"status": "PENDING"},
            after_state={"status": "REJECTED"},
            description=f"Approval {approval.pk} rejected by {reviewed_by.email}: {comments}",
        )
        approval_status_changed.send(sender=ApprovalRequest, approval_request=approval)
        logger.info("Approval %s rejected by %s", approval.pk, reviewed_by.email)
        return approval

    @staticmethod
    @transaction.atomic
    def cancel(approval_id, user, comments=""):
        approval = ApprovalRequest.objects.select_for_update().get(pk=approval_id)
        if approval.status != "PENDING":
            raise ValueError(f"Cannot cancel: current status is {approval.status}")

        approval.status = "CANCELLED"
        approval.reviewed_by = user
        approval.reviewed_at = timezone.now()
        approval.comments = comments
        approval.save()

        AuditService.log(
            action_type="DEACTIVATE",
            entity_type="ApprovalRequest",
            entity_id=approval.pk,
            entity_repr=str(approval),
            before_state={"status": "PENDING"},
            after_state={"status": "CANCELLED"},
            description=f"Approval {approval.pk} cancelled",
        )
        return approval

    @staticmethod
    def get_pending(module=None, entity_type=None):
        qs = ApprovalRequest.objects.filter(status="PENDING")
        if module:
            qs = qs.filter(module=module)
        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        return qs.select_related("submitted_by", "reviewed_by").order_by("-submitted_at")

    @staticmethod
    def requires_approval(module, entity_type, action):
        from apps.system_parameters.services.config_service import ConfigurationService
        key = f"APPROVAL_REQUIRED_{module.upper()}_{entity_type.upper()}_{action.upper()}"
        param = ConfigurationService.get_parameter(key)
        if param is not None:
            return param.lower() in ("yes", "true", "1")
        key_generic = f"APPROVAL_REQUIRED_{module.upper()}_{entity_type.upper()}"
        param = ConfigurationService.get_parameter(key_generic)
        if param is not None:
            return param.lower() in ("yes", "true", "1")
        return False
