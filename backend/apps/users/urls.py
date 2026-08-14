from rest_framework.routers import DefaultRouter

from .views import (
    PermissionGroupViewSet,
    ReportCategoryViewSet,
    UserActivityLogViewSet,
    UserGroupViewSet,
    UserPermissionViewSet,
    UserSessionViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'groups', UserGroupViewSet, basename='groups')
router.register(r'permissions', UserPermissionViewSet, basename='permissions')
router.register(r'report-categories', ReportCategoryViewSet, basename='report-categories')
router.register(r'permission-groups', PermissionGroupViewSet, basename='permission-groups')
router.register(r'sessions', UserSessionViewSet, basename='sessions')
router.register(r'audit-logs', UserActivityLogViewSet, basename='audit-logs')

urlpatterns = router.urls
