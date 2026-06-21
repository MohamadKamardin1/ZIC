from rest_framework import permissions


class IsOwnerOrReviewer(permissions.BasePermission):
    """
    Allows access only to the owner (submitted_by) or users with review permissions.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        if obj.submitted_by == request.user:
            return True
        if request.user.has_module_permission("partner_onboarding", "review"):
            return True
        return False


class CanSubmitApplication(permissions.BasePermission):
    """
    Allows submission only if the application is in DRAFT or ACTIVE status.
    """
    def has_object_permission(self, request, view, obj):
        return obj.status in ("DRAFT", "ACTIVE")


class CanReviewApplication(permissions.BasePermission):
    """
    Allows review actions when the application is in a reviewable status.
    """
    def has_object_permission(self, request, view, obj):
        return obj.status in ("SUBMITTED", "UNDER_REVIEW", "PENDING_DOCUMENTS")


class CanPerformComplianceAction(permissions.BasePermission):
    """
    Allows compliance actions (approve, suspend, resume) from appropriate statuses.
    """
    def has_object_permission(self, request, view, obj):
        return obj.status in ("COMPLIANCE_CHECK", "SUSPENDED")


class CanRejectApplication(permissions.BasePermission):
    """
    Allows rejection from UNDER_REVIEW or COMPLIANCE_CHECK status.
    """
    def has_object_permission(self, request, view, obj):
        return obj.status in ("UNDER_REVIEW", "COMPLIANCE_CHECK", "PENDING_DOCUMENTS")


class CanConvertApplication(permissions.BasePermission):
    """
    Allows conversion only if the application is in APPROVED status.
    """
    def has_object_permission(self, request, view, obj):
        return obj.status == "APPROVED"


class HasPartnerManagementPermission(permissions.BasePermission):
    """
    Allows access to users with partner_management module permission.
    """
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return request.user.has_module_permission("partner_management", "manage")
