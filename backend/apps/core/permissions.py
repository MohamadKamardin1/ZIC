from rest_framework.permissions import BasePermission, SAFE_METHODS


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

