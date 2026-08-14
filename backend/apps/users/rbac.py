from __future__ import annotations

from collections.abc import Iterable

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.common.models import DomainEvent
from apps.users.models import User, UserActivityLog, UserGroup, UserPermission


class RBACServiceError(ValidationError):
    """Raised when a group or permission mutation violates an IAM rule."""


def _request_context(request):
    if request is None:
        return None, ''
    return request.META.get('REMOTE_ADDR'), request.META.get('HTTP_USER_AGENT', '')[:500]


def _can_administer(actor: User) -> bool:
    return bool(
        actor
        and actor.is_authenticated
        and (
            actor.is_superuser
            or actor.has_permission('user_management.administer')
            or actor.has_module_permission('users', 'MANAGE')
        )
    )


def _require_admin(actor: User) -> None:
    if not _can_administer(actor):
        raise RBACServiceError('You are not authorized to administer groups and permissions.')


def _audit(actor, event_type, aggregate, payload, request=None, targets: Iterable[User] = ()):
    ip_address, user_agent = _request_context(request)
    target_list = list(targets)
    if not target_list and actor is not None:
        target_list = [actor]
    for target in target_list:
        UserActivityLog.objects.create(
            user=target,
            action_type=UserActivityLog.ActionType.PERMISSION_CHANGE,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                'actor_id': str(actor.id) if actor else None,
                'event_type': event_type,
                **payload,
            },
        )
    DomainEvent.objects.create(
        event_type=event_type,
        aggregate_type=aggregate.__class__.__name__,
        aggregate_id=str(aggregate.pk),
        payload={
            'actor_id': str(actor.id) if actor else None,
            **payload,
        },
    )


def _normalize_ids(values):
    return [str(value) for value in (values or [])]


class RBACService:
    @staticmethod
    @transaction.atomic
    def create_group(*, actor, data, request=None):
        _require_admin(actor)
        name = (data.get('name') or '').strip()
        code = (data.get('code') or name).strip().upper().replace(' ', '_')
        if not name or not code:
            raise RBACServiceError({'name': 'Group name and code are required.'})
        if UserGroup.objects.filter(name=name).exists():
            raise RBACServiceError({'name': 'A group with this name already exists.'})
        if UserGroup.objects.filter(code=code).exists():
            raise RBACServiceError({'code': 'A group with this code already exists.'})
        group = UserGroup.objects.create(
            name=name,
            code=code,
            description=data.get('description', ''),
            group_type=data.get('group_type', UserGroup.GroupType.INTERNAL),
            is_active=data.get('is_active', True),
            is_system=False,
            is_system_group=False,
            created_by=actor,
            updated_by=actor,
        )
        _audit(actor, 'iam.group.created', group, {'group_id': str(group.id), 'code': group.code}, request)
        return group

    @staticmethod
    @transaction.atomic
    def update_group(*, actor, group, data, request=None):
        _require_admin(actor)
        if group.is_system and any(key in data for key in ('code', 'group_type')):
            raise RBACServiceError('System group code and type cannot be changed.')
        for field in ('name', 'code', 'description', 'group_type', 'is_active'):
            if field in data:
                setattr(group, field, data[field])
        if group.code:
            group.code = group.code.strip().upper().replace(' ', '_')
        group.updated_by = actor
        group.save()
        _audit(actor, 'iam.group.updated', group, {'group_id': str(group.id), 'changes': list(data)}, request, group.users.all())
        return group

    @staticmethod
    @transaction.atomic
    def deactivate_group(*, actor, group, request=None):
        _require_admin(actor)
        if group.is_system:
            raise RBACServiceError('System groups cannot be deactivated.')
        group.is_active = False
        group.updated_by = actor
        group.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        _audit(actor, 'iam.group.deactivated', group, {'group_id': str(group.id)}, request, group.users.all())
        return group

    @staticmethod
    @transaction.atomic
    def assign_permissions(*, actor, group, permission_ids, request=None):
        _require_admin(actor)
        permissions = list(UserPermission.objects.filter(id__in=_normalize_ids(permission_ids), is_active=True))
        if len(permissions) != len(set(_normalize_ids(permission_ids))):
            raise RBACServiceError({'permission_ids': 'One or more permissions are invalid or inactive.'})
        group.permissions.add(*permissions)
        _audit(
            actor,
            'iam.group.permissions_assigned',
            group,
            {'group_id': str(group.id), 'permission_ids': [str(permission.id) for permission in permissions]},
            request,
            group.users.all(),
        )
        return permissions

    @staticmethod
    @transaction.atomic
    def remove_permissions(*, actor, group, permission_ids, request=None):
        _require_admin(actor)
        permissions = list(UserPermission.objects.filter(id__in=_normalize_ids(permission_ids)))
        group.permissions.remove(*permissions)
        _audit(
            actor,
            'iam.group.permissions_removed',
            group,
            {'group_id': str(group.id), 'permission_ids': [str(permission.id) for permission in permissions]},
            request,
            group.users.all(),
        )
        return permissions

    @staticmethod
    @transaction.atomic
    def assign_users(*, actor, group, user_ids, request=None):
        _require_admin(actor)
        users = list(User.objects.filter(id__in=_normalize_ids(user_ids), is_active=True))
        if len(users) != len(set(_normalize_ids(user_ids))):
            raise RBACServiceError({'user_ids': 'One or more users are invalid or inactive.'})
        partner_types = {'PARTNER', User.UserType.PORTAL_USER}
        for user in users:
            is_partner = user.user_type in partner_types
            if group.group_type == UserGroup.GroupType.PARTNER and not is_partner:
                raise RBACServiceError('Partner groups can only be assigned to partner users.')
            if group.group_type != UserGroup.GroupType.PARTNER and is_partner:
                raise RBACServiceError('Partner users can only be assigned to partner groups.')
        group.users.add(*users)
        _audit(
            actor,
            'iam.group.users_assigned',
            group,
            {'group_id': str(group.id), 'user_ids': [str(user.id) for user in users]},
            request,
            users,
        )
        return users

    @staticmethod
    @transaction.atomic
    def remove_users(*, actor, group, user_ids, request=None):
        _require_admin(actor)
        users = list(User.objects.filter(id__in=_normalize_ids(user_ids)))
        group.users.remove(*users)
        _audit(
            actor,
            'iam.group.users_removed',
            group,
            {'group_id': str(group.id), 'user_ids': [str(user.id) for user in users]},
            request,
            users,
        )
        return users

    @staticmethod
    def permission_check(user, permission_code):
        return bool(user and user.is_authenticated and user.has_permission(permission_code))
