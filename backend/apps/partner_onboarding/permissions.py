from rest_framework import permissions


class OnboardingPermissionMixin:
    module_code = "partner_onboarding"

    def has_module_permission(self, request, action):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.has_module_permission(self.module_code, action)

    def has_object_permission(self, request, view, obj):
        if obj.submitted_by_id == request.user.id:
            return True
        return self.has_module_permission(request, "READ") or self.has_module_permission(
            request, "UPDATE"
        ) or self.has_module_permission(request, "APPROVE")


class IsOwnerOrReviewer(OnboardingPermissionMixin, permissions.BasePermission):
    """Read access for the owner; reviewer/approver access for authorized staff."""


class CanCreateApplication(OnboardingPermissionMixin, permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class CanSubmitApplication(OnboardingPermissionMixin, permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return obj.submitted_by_id == request.user.id and obj.status in ("DRAFT", "ACTIVE")


class CanReviewApplication(OnboardingPermissionMixin, permissions.BasePermission):
    def has_permission(self, request, view):
        return self.has_module_permission(request, "UPDATE") or self.has_module_permission(
            request, "APPROVE"
        )

    def has_object_permission(self, request, view, obj):
        return obj.status in ("SUBMITTED", "UNDER_REVIEW", "PENDING_DOCUMENTS") and self.has_permission(request, view)


class CanPerformComplianceAction(OnboardingPermissionMixin, permissions.BasePermission):
    def has_permission(self, request, view):
        return self.has_module_permission(request, "APPROVE")

    def has_object_permission(self, request, view, obj):
        return obj.status in ("COMPLIANCE_CHECK", "SUSPENDED") and self.has_permission(request, view)


class CanRejectApplication(CanPerformComplianceAction):
    def has_object_permission(self, request, view, obj):
        return obj.status in ("UNDER_REVIEW", "COMPLIANCE_CHECK", "PENDING_DOCUMENTS") and self.has_permission(request, view)


class CanConvertApplication(CanPerformComplianceAction):
    def has_object_permission(self, request, view, obj):
        return obj.status == "APPROVED" and self.has_permission(request, view)


class HasPartnerManagementPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.has_module_permission("partner_management", "UPDATE")
