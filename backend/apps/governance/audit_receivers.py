import logging

from django.db import connection
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.governance.services.audit_service import AuditService
from apps.partners.models import UserPartnerLink
from apps.users.models import (
    User,
    UserGroup,
    UserGroupReportCategory,
    UserPermission,
)

logger = logging.getLogger(__name__)


def _audit_table_ready():
    try:
        return AuditService.__module__ and "governance_audit_log" in connection.introspection.table_names()
    except Exception:  # pragma: no cover - defensive during app startup/migrations
        return False


def _capture_before(sender, instance, **kwargs):
    if not instance.pk or not _audit_table_ready():
        instance._audit_before_state = None
        return
    try:
        previous = sender.objects.filter(pk=instance.pk).first()
        instance._audit_before_state = AuditService.snapshot(previous) if previous else None
    except Exception:
        instance._audit_before_state = None


def _audit_saved(sender, instance, created, **kwargs):
    if not _audit_table_ready():
        return
    try:
        before = getattr(instance, "_audit_before_state", None)
        if created:
            AuditService.log_create(instance)
            return
        after = AuditService.snapshot(instance)
        changed = AuditService.changed_fields(before or {}, after)
        if not changed or set(changed).issubset({"last_activity", "last_ip_address", "user_agent"}):
            return
        AuditService.log_update(instance, before_state=before, changed_fields=changed)
    except Exception:
        logger.exception("Central audit receiver failed for %s", sender.__name__)


def _audit_deleted(sender, instance, **kwargs):
    if not _audit_table_ready():
        return
    try:
        AuditService.log_delete(instance)
    except Exception:
        logger.exception("Central delete audit receiver failed for %s", sender.__name__)


for _model in (User, UserGroup, UserPermission, UserGroupReportCategory, UserPartnerLink):
    pre_save.connect(_capture_before, sender=_model, weak=False, dispatch_uid=f"central-audit-pre-{_model._meta.label_lower}")
    post_save.connect(_audit_saved, sender=_model, weak=False, dispatch_uid=f"central-audit-post-{_model._meta.label_lower}")
    if _model in (UserGroupReportCategory, UserPartnerLink):
        post_delete.connect(_audit_deleted, sender=_model, weak=False, dispatch_uid=f"central-audit-delete-{_model._meta.label_lower}")


def _audit_m2m_changed(action, instance, model, pk_set, relation_name):
    if action not in {"post_add", "post_remove", "post_clear"} or not _audit_table_ready():
        return
    try:
        AuditService.log_action(
            action="ASSIGN" if action == "post_add" else "UNASSIGN",
            instance=instance,
            after_state={relation_name: sorted(str(pk) for pk in (pk_set or set()))},
            reason=f"{relation_name} membership changed",
            changed_fields=[relation_name],
        )
    except Exception:
        logger.exception("Central m2m audit receiver failed for %s", relation_name)


@receiver(m2m_changed, sender=User.groups.through, dispatch_uid="central-audit-user-groups")
def audit_user_groups(sender, instance, action, pk_set, **kwargs):
    _audit_m2m_changed(action, instance, UserGroup, pk_set, "groups")


@receiver(m2m_changed, sender=UserGroup.permissions.through, dispatch_uid="central-audit-group-permissions")
def audit_group_permissions(sender, instance, action, pk_set, **kwargs):
    _audit_m2m_changed(action, instance, UserPermission, pk_set, "permissions")


@receiver(m2m_changed, sender=UserGroup.report_categories.through, dispatch_uid="central-audit-group-report-categories")
def audit_group_report_categories(sender, instance, action, pk_set, **kwargs):
    _audit_m2m_changed(action, instance, UserGroupReportCategory, pk_set, "report_categories")
