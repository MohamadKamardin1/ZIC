from __future__ import annotations

from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.dashboard.models import DashboardAlert, DashboardNotification, DashboardTask
from apps.governance.models import ApprovalRequest, AuditLog
from apps.governance.services.approval_service import ApprovalService
from apps.governance.services.audit_service import AuditContext, AuditService
from apps.ordinary_life.models import (
    OLDocumentRecord,
    OLNote,
    OLPolicyRenewal,
    OLReinstatementRequest,
    OLWorkflowEvent,
)


class OrdinaryLifeOperationsService:
    """Service-owned operational workflows for Ordinary Life evidence and work management."""

    MODULE = "ORDINARY_LIFE"

    @staticmethod
    def _require_actor(actor):
        if actor is None or not getattr(actor, "is_authenticated", False):
            raise PermissionDenied("An authenticated actor is required for Ordinary Life operations.")
        return actor

    @classmethod
    def _require_any_permission(cls, actor, *actions):
        actor = cls._require_actor(actor)
        if getattr(actor, "is_superuser", False) or any(actor.has_module_permission(cls.MODULE, action) for action in actions):
            return actor
        raise PermissionDenied(f"One of the Ordinary Life permissions {', '.join(actions)} is required.")

    @staticmethod
    def _reason(reason, required=False):
        value = str(reason or "").strip()
        if required and not value:
            raise ValidationError({"reason": "A reason is required for this operation."})
        return value

    @classmethod
    def _require_permission(cls, actor, action):
        actor = cls._require_actor(actor)
        if getattr(actor, "is_superuser", False) or actor.has_module_permission(cls.MODULE, action):
            return actor
        raise PermissionDenied(f"Ordinary Life permission {action} is required.")

    @staticmethod
    def _source_metadata():
        context = AuditContext.get_context()
        return {
            "request_id": context.get("request_id", ""),
            "source_channel": context.get("source_channel", AuditLog.SourceChannel.SYSTEM),
        }

    @classmethod
    def _event(cls, instance, action, actor, *, previous_status="", new_status="", reason="", before=None, after=None, metadata=None):
        metadata = metadata or {}
        event = OLWorkflowEvent.objects.create(
            entity_type=instance._meta.label,
            entity_id=instance.pk,
            action=action,
            previous_status=previous_status,
            new_status=new_status,
            reason=reason,
            actor=actor,
            metadata=metadata,
        )
        source = cls._source_metadata()
        AuditService.log(
            action_type=action,
            entity_type=instance._meta.label,
            entity_id=instance.pk,
            entity_repr=str(instance),
            before_state=before or ({"status": previous_status} if previous_status else {}),
            after_state=after or ({"status": new_status} if new_status else metadata),
            description=reason,
            actor=actor,
            action=action,
            app_label=instance._meta.app_label,
            model_name=instance._meta.model_name,
            object_id=instance.pk,
            object_repr=str(instance),
            changed_fields=list(metadata.get("changed_fields", [])),
            reason=reason,
            request_id=source["request_id"],
            source_channel=source["source_channel"],
        )
        return event

    @staticmethod
    def _parent(proposal=None, policy=None):
        if (proposal is None) == (policy is None):
            raise ValidationError({"parent": "Exactly one proposal or policy parent is required."})
        return proposal, policy

    @staticmethod
    def _route(entity_type, entity_id):
        route_map = {
            "OLProposal": f"/ordinary-life/proposals/{entity_id}",
            "OLPolicy": f"/ordinary-life/policies/{entity_id}",
            "OLDocumentRecord": f"/ordinary-life/documents/{entity_id}",
            "OLEndorsement": f"/ordinary-life/policies/{entity_id}?tab=endorsements",
        }
        return route_map.get(entity_type, "/ordinary-life")

    @classmethod
    def _notification(cls, owner, external_key, *, kind, title, message, status="", entity_type="", entity_id="", route=""):
        if owner is None:
            return None
        notification, _created = DashboardNotification.objects.update_or_create(
            owner=owner,
            external_key=external_key,
            defaults={
                "kind": kind,
                "title": title,
                "message": message,
                "status": status,
                "route": route,
                "entity_type": entity_type,
                "entity_id": str(entity_id or ""),
            },
        )
        return notification

    @classmethod
    def _task(cls, owner, actor, *, title, description, entity_type, entity_id, route, priority="MEDIUM", due_at=None):
        if owner is None:
            return None
        task = DashboardTask.objects.filter(
            owner=owner,
            title=title,
            entity_type=entity_type,
            entity_id=str(entity_id),
            status__in=[DashboardTask.Status.TODO, DashboardTask.Status.IN_PROGRESS],
        ).first()
        if task is None:
            task = DashboardTask.objects.create(
                owner=owner,
                created_by=actor,
                title=title,
                description=description,
                priority=priority,
                due_at=due_at,
                route=route,
                entity_type=entity_type,
                entity_id=str(entity_id),
            )
        return task

    @classmethod
    def _alert(cls, owner, *, title, message, entity_type, entity_id, route, severity="WARNING"):
        if owner is None:
            return None
        alert = DashboardAlert.objects.filter(
            owner=owner,
            title=title,
            entity_type=entity_type,
            entity_id=str(entity_id),
            status__in=[DashboardAlert.Status.OPEN, DashboardAlert.Status.ACKNOWLEDGED],
        ).first()
        if alert is None:
            alert = DashboardAlert.objects.create(
                owner=owner,
                title=title,
                message=message,
                severity=severity,
                route=route,
                entity_type=entity_type,
                entity_id=str(entity_id),
            )
        return alert

    @classmethod
    @transaction.atomic
    def create_document(
        cls,
        *,
        proposal=None,
        policy=None,
        document_type,
        actor=None,
        file_reference="",
        metadata=None,
        idempotency_key=None,
        reason="",
        task_owner=None,
    ):
        actor = cls._require_permission(actor, "CREATE")
        proposal, policy = cls._parent(proposal, policy)
        document_type = str(document_type or "").strip().upper()
        if not document_type:
            raise ValidationError({"document_type": "Document type is required."})
        if idempotency_key:
            existing = OLDocumentRecord.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                if existing.document_type != document_type or existing.proposal_id != getattr(proposal, "pk", None) or existing.policy_id != getattr(policy, "pk", None):
                    raise ValidationError({"idempotency_key": "The key is already used for another document."})
                return existing
        if proposal is not None:
            existing = OLDocumentRecord.objects.filter(proposal=proposal, document_type=document_type).first()
            if existing:
                raise ValidationError({"document_type": "A document of this type already exists for the proposal."})
        now = timezone.now()
        file_reference = str(file_reference or "").strip()
        document = OLDocumentRecord.objects.create(
            proposal=proposal,
            policy=policy,
            document_type=document_type,
            file_reference=file_reference,
            status="UPLOADED" if file_reference else "PENDING",
            metadata=metadata or {},
            uploaded_by=actor if file_reference else None,
            uploaded_at=now if file_reference else None,
            status_reason=cls._reason(reason),
            idempotency_key=idempotency_key,
        )
        cls._event(
            document,
            "CREATE_DOCUMENT",
            actor,
            new_status=document.status,
            reason=cls._reason(reason),
            metadata={"changed_fields": ["status", "file_reference"] if file_reference else ["status"]},
        )
        owner = task_owner or actor
        if document.status == "PENDING":
            cls._task(
                owner,
                actor,
                title=f"Upload {document.document_type} document",
                description="Upload the required Ordinary Life evidence document.",
                entity_type="OLDocumentRecord",
                entity_id=document.pk,
                route=cls._route("OLDocumentRecord", document.pk),
                priority="HIGH",
                due_at=timezone.now() + timedelta(days=2),
            )
        cls._notification(
            owner,
            f"ordinary-life-document-{document.pk}-created",
            kind="ORDINARY_LIFE_DOCUMENT",
            title="Ordinary Life document created",
            message=f"{document.document_type} is {document.status.lower()}.",
            status=document.status,
            entity_type="OLDocumentRecord",
            entity_id=document.pk,
            route=cls._route("OLDocumentRecord", document.pk),
        )
        return document

    @classmethod
    @transaction.atomic
    def upload_document(cls, document, *, file_reference, actor=None, metadata=None, reason=""):
        actor = cls._require_permission(actor, "UPDATE")
        document = OLDocumentRecord.objects.select_for_update().get(pk=document.pk)
        if document.status not in {"PENDING", "REJECTED"}:
            raise ValidationError({"status": "Only pending or rejected documents can be uploaded."})
        file_reference = str(file_reference or "").strip()
        if not file_reference:
            raise ValidationError({"file_reference": "A file reference is required."})
        previous = document.status
        document.file_reference = file_reference
        document.status = "UPLOADED"
        document.metadata = metadata if metadata is not None else document.metadata
        document.uploaded_by = actor
        document.uploaded_at = timezone.now()
        document.status_reason = cls._reason(reason)
        document.rejected_by = None
        document.rejected_at = None
        document.save(update_fields=["file_reference", "status", "metadata", "uploaded_by", "uploaded_at", "status_reason", "rejected_by", "rejected_at"])
        cls._event(document, "UPLOAD_DOCUMENT", actor, previous_status=previous, new_status=document.status, reason=document.status_reason, metadata={"changed_fields": ["file_reference", "status", "metadata"]})
        cls._notification(actor, f"ordinary-life-document-{document.pk}-uploaded", kind="ORDINARY_LIFE_DOCUMENT", title="Document uploaded", message=f"{document.document_type} is ready for verification.", status=document.status, entity_type="OLDocumentRecord", entity_id=document.pk, route=cls._route("OLDocumentRecord", document.pk))
        return document

    @classmethod
    @transaction.atomic
    def verify_document(cls, document, *, actor=None, reason=""):
        actor = cls._require_any_permission(actor, "REVIEW", "APPROVE")
        document = OLDocumentRecord.objects.select_for_update().get(pk=document.pk)
        if document.status != "UPLOADED":
            raise ValidationError({"status": "Only uploaded documents can be verified."})
        document.status = "VERIFIED"
        document.verified_by = actor
        document.verified_at = timezone.now()
        document.status_reason = cls._reason(reason, required=True)
        document.save(update_fields=["status", "verified_by", "verified_at", "status_reason"])
        cls._event(document, "VERIFY_DOCUMENT", actor, previous_status="UPLOADED", new_status=document.status, reason=document.status_reason, metadata={"changed_fields": ["status", "verified_by", "verified_at"]})
        cls._notification(actor, f"ordinary-life-document-{document.pk}-verified", kind="ORDINARY_LIFE_DOCUMENT", title="Document verified", message=f"{document.document_type} has been verified.", status=document.status, entity_type="OLDocumentRecord", entity_id=document.pk, route=cls._route("OLDocumentRecord", document.pk))
        return document

    @classmethod
    @transaction.atomic
    def reject_document(cls, document, *, actor=None, reason=""):
        actor = cls._require_any_permission(actor, "REVIEW", "REJECT")
        document = OLDocumentRecord.objects.select_for_update().get(pk=document.pk)
        if document.status not in {"PENDING", "UPLOADED"}:
            raise ValidationError({"status": "Only pending or uploaded documents can be rejected."})
        reason = cls._reason(reason, required=True)
        previous = document.status
        document.status = "REJECTED"
        document.rejected_by = actor
        document.rejected_at = timezone.now()
        document.status_reason = reason
        document.save(update_fields=["status", "rejected_by", "rejected_at", "status_reason"])
        cls._event(document, "REJECT_DOCUMENT", actor, previous_status=previous, new_status=document.status, reason=reason, metadata={"changed_fields": ["status", "rejected_by", "rejected_at", "status_reason"]})
        cls._alert(actor, title="Ordinary Life document rejected", message=f"{document.document_type} requires correction: {reason}", entity_type="OLDocumentRecord", entity_id=document.pk, route=cls._route("OLDocumentRecord", document.pk), severity="WARNING")
        return document

    @classmethod
    @transaction.atomic
    def submit_document_verification(cls, document, *, actor=None, comments=""):
        actor = cls._require_permission(actor, "REVIEW")
        document = OLDocumentRecord.objects.select_for_update().get(pk=document.pk)
        if document.status != "UPLOADED":
            raise ValidationError({"status": "Only uploaded documents can enter verification approval."})
        existing = ApprovalRequest.objects.filter(
            module=cls.MODULE,
            entity_type="OLDocumentRecord",
            entity_id=document.pk,
            action="VERIFY",
            status="PENDING",
        ).first()
        if existing:
            return existing
        approval = ApprovalService.submit(
            module=cls.MODULE,
            entity_type="OLDocumentRecord",
            entity_id=document.pk,
            action="VERIFY",
            requested_data={"status": "VERIFIED", "document_type": document.document_type},
            current_data={"status": document.status},
            entity_repr=str(document),
            submitted_by=actor,
            comments=cls._reason(comments),
        )
        cls._event(document, "SUBMIT_DOCUMENT_VERIFICATION", actor, new_status=document.status, reason=cls._reason(comments), metadata={"approval_id": str(approval.pk)})
        cls._task(actor, actor, title=f"Verify {document.document_type} document", description="Review and verify the uploaded Ordinary Life evidence.", entity_type="ApprovalRequest", entity_id=approval.pk, route=cls._route("OLDocumentRecord", document.pk), priority="HIGH")
        return approval

    @classmethod
    @transaction.atomic
    def complete_document_verification(cls, approval_id, *, reviewer=None, comments=""):
        reviewer = cls._require_permission(reviewer, "APPROVE")
        approval = ApprovalService.approve(approval_id, reviewer, comments=comments)
        if approval.module != cls.MODULE or approval.entity_type != "OLDocumentRecord" or approval.action != "VERIFY":
            return approval
        document = OLDocumentRecord.objects.get(pk=approval.entity_id)
        return cls.verify_document(document, actor=reviewer, reason=comments or "Verification approval completed")

    @classmethod
    @transaction.atomic
    def reject_document_verification(cls, approval_id, *, reviewer=None, comments=""):
        reviewer = cls._require_permission(reviewer, "REJECT")
        comments = cls._reason(comments, required=True)
        approval = ApprovalService.reject(approval_id, reviewer, comments=comments)
        if approval.module != cls.MODULE or approval.entity_type != "OLDocumentRecord" or approval.action != "VERIFY":
            return approval
        document = OLDocumentRecord.objects.get(pk=approval.entity_id)
        return cls.reject_document(document, actor=reviewer, reason=comments)

    @classmethod
    @transaction.atomic
    def add_note(
        cls,
        *,
        proposal=None,
        policy=None,
        content,
        actor=None,
        is_internal=True,
        idempotency_key=None,
    ):
        actor = cls._require_permission(actor, "CREATE")
        proposal, policy = cls._parent(proposal, policy)
        content = str(content or "").strip()
        if not content:
            raise ValidationError({"content": "Note content is required."})
        if idempotency_key:
            existing = OLNote.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return existing
        note = OLNote.objects.create(
            proposal=proposal,
            policy=policy,
            content=content,
            is_internal=bool(is_internal),
            created_by=actor,
            idempotency_key=idempotency_key,
        )
        cls._event(note, "ADD_NOTE", actor, reason="Internal note added", metadata={"changed_fields": ["content"], "is_internal": note.is_internal})
        cls._notification(actor, f"ordinary-life-note-{note.pk}", kind="ORDINARY_LIFE_NOTE", title="Ordinary Life note added", message="A new workflow note was recorded.", entity_type="OLNote", entity_id=note.pk, route=cls._route("OLPolicy" if policy else "OLProposal", policy.pk if policy else proposal.pk))
        return note

    @classmethod
    @transaction.atomic
    def submit_policy_approval(cls, entity, *, entity_type, action, actor=None, requested_data=None, comments=""):
        actor = cls._require_permission(actor, "REVIEW")
        entity_type = str(entity_type or entity.__class__.__name__)
        action = str(action or "APPROVE").upper()
        entity_id = entity.pk
        existing = ApprovalRequest.objects.filter(module=cls.MODULE, entity_type=entity_type, entity_id=entity_id, action=action, status="PENDING").first()
        if existing:
            return existing
        approval = ApprovalService.submit(
            module=cls.MODULE,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            requested_data=requested_data or {},
            current_data={"status": getattr(entity, "status", "")},
            entity_repr=str(entity),
            submitted_by=actor,
            comments=cls._reason(comments),
        )
        cls._event(entity, "SUBMIT_APPROVAL", actor, new_status=getattr(entity, "status", ""), reason=cls._reason(comments), metadata={"approval_id": str(approval.pk), "approval_action": action})
        cls._task(actor, actor, title=f"Review {entity_type} approval", description=f"Review {action.lower()} approval for {entity_type}.", entity_type="ApprovalRequest", entity_id=approval.pk, route=cls._route(entity_type, entity_id), priority="HIGH")
        return approval

    @classmethod
    @transaction.atomic
    def complete_policy_approval(cls, approval_id, *, reviewer=None, comments=""):
        reviewer = cls._require_permission(reviewer, "APPROVE")
        approval = ApprovalService.approve(approval_id, reviewer, comments=comments)
        if approval.module != cls.MODULE:
            return approval
        method_by_entity = {
            "OLEndorsement": "approve_endorsement",
            "OLPolicyRenewal": "approve_renewal",
            "OLReinstatementRequest": "approve_reinstatement",
        }
        method_name = method_by_entity.get(approval.entity_type)
        if not method_name:
            return approval
        from apps.ordinary_life.models import OLEndorsement
        from apps.ordinary_life.services.policy_service import OrdinaryLifePolicyService

        model_by_entity = {
            "OLEndorsement": OLEndorsement,
            "OLPolicyRenewal": OLPolicyRenewal,
            "OLReinstatementRequest": OLReinstatementRequest,
        }
        entity = model_by_entity[approval.entity_type].objects.get(pk=approval.entity_id)
        return getattr(OrdinaryLifePolicyService, method_name)(entity, actor=reviewer, reason=comments or "Shared approval completed")

    @classmethod
    def workflow_history(cls, *, entity_type, entity_id, actor=None):
        cls._require_permission(actor, "READ")
        return OLWorkflowEvent.objects.filter(entity_type=entity_type, entity_id=entity_id).select_related("actor").order_by("created_at")

    @classmethod
    def audit_history(cls, *, model_name, object_id, actor=None):
        cls._require_permission(actor, "COMPLIANCE")
        return AuditLog.objects.filter(app_label="ordinary_life", model_name=model_name.lower(), object_id=str(object_id)).select_related("user").order_by("created_at")

    @classmethod
    def open_document_work_items(cls, document, *, owner, actor=None):
        actor = cls._require_permission(actor, "ASSIGN")
        if document.status == "PENDING":
            return cls._task(owner, actor, title=f"Upload {document.document_type} document", description="Upload the required Ordinary Life evidence document.", entity_type="OLDocumentRecord", entity_id=document.pk, route=cls._route("OLDocumentRecord", document.pk), priority="HIGH")
        if document.status == "UPLOADED":
            return cls._task(owner, actor, title=f"Verify {document.document_type} document", description="Verify the uploaded Ordinary Life evidence document.", entity_type="OLDocumentRecord", entity_id=document.pk, route=cls._route("OLDocumentRecord", document.pk), priority="HIGH")
        return None


OrdinaryLifeWorkflowOperations = OrdinaryLifeOperationsService
