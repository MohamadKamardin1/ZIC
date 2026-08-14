from functools import wraps

from django.core.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class IsStaffUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.is_staff:
            return True
        return obj == request.user


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class HasModulePermission(BasePermission):
    def __init__(self, module_code=None, action=None):
        self.module_code = module_code
        self.action = action

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        if request.user.is_staff and self.action in ['READ']:
            return True
        return request.user.has_module_permission(self.module_code, self.action)


class HasPermission(BasePermission):
    """Authorize an endpoint using a normalized ``module.action`` code."""

    permission_code = None

    def __init__(self, permission_code=None):
        self.permission_code = permission_code or self.permission_code

    def has_permission(self, request, view):
        code = getattr(view, 'permission_code', None) or self.permission_code
        return bool(
            request.user
            and request.user.is_authenticated
            and code
            and request.user.has_permission(code)
        )


def permission_required(permission_code):
    """Protect a Django view with a normalized ``module.action`` permission."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated or not request.user.has_permission(permission_code):
                raise PermissionDenied(f'Missing permission: {permission_code}')
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


class OrPermission(BasePermission):
    def __init__(self, *permissions):
        self.permissions = permissions

    def has_permission(self, request, view):
        return any(perm.has_permission(request, view) for perm in self.permissions)

    def has_object_permission(self, request, view, obj):
        # Check has_object_permission if defined, otherwise fall back to has_permission
        results = []
        for perm in self.permissions:
            # BasePermission has_object_permission always returns True.
            # So if it's the default BasePermission.has_object_permission, we might want to check has_permission.
            # But wait! A cleaner way is: if the class has overridden has_object_permission, check it.
            # How do we know if it has overridden has_object_permission?
            # We can check: perm.__class__.has_object_permission != BasePermission.has_object_permission
            has_obj_perm_overridden = perm.__class__.has_object_permission != BasePermission.has_object_permission
            if has_obj_perm_overridden:
                val = perm.has_object_permission(request, view, obj)
            else:
                val = perm.has_permission(request, view)
            results.append(val)
        return any(results)

