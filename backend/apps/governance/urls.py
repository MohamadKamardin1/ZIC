from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AuditLogViewSet,
    ApprovalRequestViewSet,
    ConfigurationVersionViewSet,
    DocumentVersionViewSet,
    KYCReviewHistoryViewSet,
    PartnerTypeAssignmentHistoryViewSet,
    ComplianceDashboardViewSet,
)

router = DefaultRouter()
router.register(r"audit-logs", AuditLogViewSet, basename="audit-logs")
router.register(r"approvals", ApprovalRequestViewSet, basename="approvals")
router.register(r"config-versions", ConfigurationVersionViewSet, basename="config-versions")
router.register(r"document-versions", DocumentVersionViewSet, basename="document-versions")
router.register(r"kyc-review-history", KYCReviewHistoryViewSet, basename="kyc-review-history")
router.register(
    r"assignment-history",
    PartnerTypeAssignmentHistoryViewSet,
    basename="assignment-history",
)
router.register(r"compliance", ComplianceDashboardViewSet, basename="compliance")

urlpatterns = [
    path("", include(router.urls)),
]
