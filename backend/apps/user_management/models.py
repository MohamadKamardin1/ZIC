from apps.users.models import User as BaseUser
from apps.users.models import UserGroup as BaseUserGroup
from apps.users.models import UserPermission as BaseUserPermission
from apps.users.models import PermissionGroup as BasePermissionGroup


class User(BaseUser):
    class Meta:
        proxy = True
        app_label = 'user_management'
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class UserGroup(BaseUserGroup):
    class Meta:
        proxy = True
        app_label = 'user_management'
        verbose_name = 'User Group'
        verbose_name_plural = 'User Groups'


class UserPermission(BaseUserPermission):
    class Meta:
        proxy = True
        app_label = 'user_management'
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'


class PermissionGroup(BasePermissionGroup):
    class Meta:
        proxy = True
        app_label = 'user_management'
        verbose_name = 'Permission Group'
        verbose_name_plural = 'Permission Groups'
