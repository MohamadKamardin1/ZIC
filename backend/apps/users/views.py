import logging

from rest_framework import viewsets, generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction

from apps.core.permissions import IsAdminUser, IsOwnerOrAdmin, HasModulePermission, OrPermission
from apps.core.pagination import StandardPagination
from .models import (
    User, UserGroup, UserPermission, PermissionGroup,
    UserSession, UserActivityLog,
)
from .serializers import (
    UserListSerializer, UserDetailSerializer, UserCreateSerializer,
    UserUpdateSerializer, UserProfileSerializer,
    UserGroupSerializer, UserGroupDetailSerializer,
    UserPermissionSerializer, PermissionGroupSerializer,
    UserSessionSerializer, UserActivityLogSerializer,
    ChangePasswordSerializer,
)

logger = logging.getLogger('apps.users.views')


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    pagination_class = StandardPagination
    filterset_fields = ['is_active', 'is_approved', 'user_type', 'is_2fa_enabled']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']
    ordering_fields = ['date_joined', 'last_login', 'last_activity', 'username', 'email']

    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        elif self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserDetailSerializer

    def get_permissions(self):
        if self.action in ['me', 'update_profile', 'change_password']:
            return [permissions.IsAuthenticated()]
        if self.action in ['list']:
            return [permissions.IsAuthenticated(), HasModulePermission('users', 'READ')]
        if self.action in ['create', 'destroy', 'activate', 'deactivate']:
            return [permissions.IsAuthenticated(), HasModulePermission('users', 'MANAGE')]
        if self.action in ['retrieve', 'update', 'partial_update']:
            return [permissions.IsAuthenticated(), OrPermission(IsOwnerOrAdmin(), HasModulePermission('users', 'MANAGE'))]
        return [permissions.IsAuthenticated(), HasModulePermission('users', 'MANAGE')]

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response({
            'success': True,
            'status_code': 200,
            'message': 'Profile retrieved',
            'data': serializer.data,
            'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
        })

    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        UserActivityLog.objects.create(
            user=request.user,
            action_type='PROFILE_UPDATE',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
        )
        return Response({
            'success': True,
            'status_code': 200,
            'message': 'Profile updated',
            'data': serializer.data,
            'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
        })

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.must_change_password = False
        request.user.password_changed_at = timezone.now()
        request.user.save()
        UserActivityLog.objects.create(
            user=request.user,
            action_type='PASSWORD_CHANGE',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
            details={'password_changed_at': timezone.now().isoformat()},
        )
        return Response({
            'success': True,
            'status_code': 200,
            'message': 'Password changed successfully',
            'data': None,
            'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
        })

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({
            'success': True,
            'status_code': 200,
            'message': f'User {user.username} deactivated',
            'data': None,
            'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
        })

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({
            'success': True,
            'status_code': 200,
            'message': f'User {user.username} activated',
            'data': None,
            'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
        })

    def perform_create(self, serializer):
        user = serializer.save()
        UserActivityLog.objects.create(
            user=user,
            action_type='LOGIN',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')[:255],
        )

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


class UserGroupViewSet(viewsets.ModelViewSet):
    queryset = UserGroup.objects.all()

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated(), HasModulePermission('users', 'READ')]
        return [permissions.IsAuthenticated(), HasModulePermission('users', 'MANAGE')]

    def get_serializer_class(self):
        if self.action in ['retrieve', 'list']:
            return UserGroupDetailSerializer if self.action == 'retrieve' else UserGroupSerializer
        return UserGroupSerializer

    @action(detail=True, methods=['post'])
    def assign_permissions(self, request, pk=None):
        group = self.get_object()
        permission_ids = request.data.get('permission_ids', [])
        permissions = UserPermission.objects.filter(id__in=permission_ids)
        group.permissions.add(*permissions)
        return Response({
            'success': True,
            'status_code': 200,
            'message': f'{permissions.count()} permissions assigned to {group.name}',
            'data': None,
            'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
        })

    @action(detail=True, methods=['post'])
    def remove_permissions(self, request, pk=None):
        group = self.get_object()
        permission_ids = request.data.get('permission_ids', [])
        permissions = UserPermission.objects.filter(id__in=permission_ids)
        group.permissions.remove(*permissions)
        return Response({
            'success': True,
            'status_code': 200,
            'message': f'{permissions.count()} permissions removed from {group.name}',
            'data': None,
            'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
        })


class UserPermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserPermission.objects.all()
    serializer_class = UserPermissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['module', 'action', 'resource_type']
    search_fields = ['name', 'codename', 'module']

    @action(detail=False, methods=['get'])
    def modules(self, request):
        modules = UserPermission.objects.values_list('module', flat=True).distinct()
        return Response({
            'success': True,
            'status_code': 200,
            'message': 'Modules retrieved',
            'data': list(modules),
            'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
        })


class PermissionGroupViewSet(viewsets.ModelViewSet):
    queryset = PermissionGroup.objects.all()
    serializer_class = PermissionGroupSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated(), HasModulePermission('users', 'READ')]
        return [permissions.IsAuthenticated(), HasModulePermission('users', 'MANAGE')]
    filterset_fields = ['module_code']
    search_fields = ['name', 'module_code']


class UserSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return UserSession.objects.all()
        return UserSession.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def revoke(self, request):
        session_id = request.data.get('session_id')
        if not session_id:
            return Response({'error': 'session_id required'}, status=400)
        try:
            session = UserSession.objects.get(id=session_id)
            if session.user != request.user and not request.user.is_superuser:
                return Response({'error': 'Forbidden'}, status=403)
            session.is_active = False
            session.save()
            return Response({
                'success': True,
                'status_code': 200,
                'message': 'Session revoked',
                'data': None,
                'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
            })
        except UserSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)


class UserActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    filterset_fields = ['action_type', 'user']
    search_fields = ['user__username', 'user__email', 'ip_address']
    ordering_fields = ['timestamp']

    def get_queryset(self):
        return UserActivityLog.objects.select_related('user').all()
