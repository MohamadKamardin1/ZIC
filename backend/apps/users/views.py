import logging

from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.authentication import services as iam_services
from apps.core.pagination import StandardPagination
from apps.core.permissions import HasModulePermission, HasPermission, IsAdminUser, IsOwnerOrAdmin, OrPermission

from .models import (
    PermissionGroup,
    User,
    UserActivityLog,
    UserGroup,
    UserPermission,
    UserSession,
)
from .rbac import RBACService
from .serializers import (
    ChangePasswordSerializer,
    GroupAssignmentSerializer,
    PermissionGroupSerializer,
    UserActivityLogSerializer,
    UserCreateSerializer,
    UserDetailSerializer,
    UserGroupDetailSerializer,
    UserGroupSerializer,
    UserListSerializer,
    UserPermissionSerializer,
    UserProfileSerializer,
    UserSessionSerializer,
    UserUpdateSerializer,
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
        try:
            iam_services.set_password(request.user, serializer.validated_data['new_password'], request)
        except iam_services.IAMServiceError as exc:
            return Response({'error': exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'success': True,
            'status_code': 200,
            'message': 'Password changed successfully',
            'data': None,
            'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
        })

    @action(detail=True, methods=['post'])
    def reset_mfa(self, request, pk=None):
        user = self.get_object()
        try:
            iam_services.reset_user_mfa(actor=request.user, user=user, request=request)
        except iam_services.IAMServiceError as exc:
            code = status.HTTP_403_FORBIDDEN if exc.code == 'forbidden' else status.HTTP_400_BAD_REQUEST
            return Response({'error': exc.message}, status=code)
        return Response({
            'success': True,
            'status_code': 200,
            'message': f'MFA reset for {user.username}',
            'data': {'user_id': str(user.id), 'mfa_enabled': False, 'mfa_required': False},
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
    queryset = UserGroup.objects.prefetch_related('permissions', 'users').all()

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [
                permissions.IsAuthenticated(),
                OrPermission(
                    HasPermission('user_management.view'),
                    HasModulePermission('users', 'READ'),
                ),
            ]
        return [
            permissions.IsAuthenticated(),
            OrPermission(
                HasPermission('user_management.administer'),
                HasModulePermission('users', 'MANAGE'),
            ),
        ]

    def get_serializer_class(self):
        return UserGroupDetailSerializer if self.action == 'retrieve' else UserGroupSerializer

    def _wrapped(self, message, data=None, code=200):
        return Response({
            'success': True,
            'status_code': code,
            'message': message,
            'data': data,
            'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
        }, status=code)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = RBACService.create_group(actor=request.user, data=serializer.validated_data, request=request)
        return self._wrapped('Group created successfully.', UserGroupDetailSerializer(group).data, status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        group = self.get_object()
        serializer = self.get_serializer(group, data=request.data, partial=kwargs.pop('partial', False))
        serializer.is_valid(raise_exception=True)
        group = RBACService.update_group(actor=request.user, group=group, data=serializer.validated_data, request=request)
        return self._wrapped('Group updated successfully.', UserGroupDetailSerializer(group).data)

    def destroy(self, request, *args, **kwargs):
        group = self.get_object()
        group = RBACService.deactivate_group(actor=request.user, group=group, request=request)
        return self._wrapped('Group deactivated successfully.', UserGroupDetailSerializer(group).data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        group = RBACService.deactivate_group(actor=request.user, group=self.get_object(), request=request)
        return self._wrapped('Group deactivated successfully.', UserGroupDetailSerializer(group).data)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        group = self.get_object()
        if group.is_system:
            group.is_active = True
            group.updated_by = request.user
            group.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        else:
            group.is_active = True
            group.updated_by = request.user
            group.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        return self._wrapped('Group activated successfully.', UserGroupDetailSerializer(group).data)

    @action(detail=True, methods=['post'])
    def assign_permissions(self, request, pk=None):
        group = self.get_object()
        serializer = GroupAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assigned = RBACService.assign_permissions(
            actor=request.user,
            group=group,
            permission_ids=serializer.validated_data.get('permission_ids', []),
            request=request,
        )
        return self._wrapped(
            f'{len(assigned)} permissions assigned to {group.name}.',
            {'permission_ids': [str(permission.id) for permission in assigned]},
        )

    @action(detail=True, methods=['post'])
    def remove_permissions(self, request, pk=None):
        group = self.get_object()
        serializer = GroupAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        removed = RBACService.remove_permissions(
            actor=request.user,
            group=group,
            permission_ids=serializer.validated_data.get('permission_ids', []),
            request=request,
        )
        return self._wrapped(
            f'{len(removed)} permissions removed from {group.name}.',
            {'permission_ids': [str(permission.id) for permission in removed]},
        )

    @action(detail=True, methods=['post'])
    def assign_users(self, request, pk=None):
        group = self.get_object()
        serializer = GroupAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assigned = RBACService.assign_users(
            actor=request.user,
            group=group,
            user_ids=serializer.validated_data.get('user_ids', []),
            request=request,
        )
        return self._wrapped(
            f'{len(assigned)} users assigned to {group.name}.',
            {'user_ids': [str(user.id) for user in assigned]},
        )

    @action(detail=True, methods=['post'])
    def remove_users(self, request, pk=None):
        group = self.get_object()
        serializer = GroupAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        removed = RBACService.remove_users(
            actor=request.user,
            group=group,
            user_ids=serializer.validated_data.get('user_ids', []),
            request=request,
        )
        return self._wrapped(
            f'{len(removed)} users removed from {group.name}.',
            {'user_ids': [str(user.id) for user in removed]},
        )


class UserPermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserPermission.objects.filter(is_active=True)
    serializer_class = UserPermissionSerializer
    filterset_fields = ['module', 'action', 'resource_type']
    search_fields = ['name', 'codename', 'module', 'description']

    def get_permissions(self):
        return [
            permissions.IsAuthenticated(),
            OrPermission(
                HasPermission('user_management.view'),
                HasModulePermission('users', 'READ'),
            ),
        ]

    @action(detail=False, methods=['get'])
    def modules(self, request):
        modules = UserPermission.objects.filter(is_active=True).values_list('module', flat=True).distinct()
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
            return [
                permissions.IsAuthenticated(),
                OrPermission(
                    HasPermission('user_management.view'),
                    HasModulePermission('users', 'READ'),
                ),
            ]
        return [
            permissions.IsAuthenticated(),
            OrPermission(
                HasPermission('user_management.administer'),
                HasModulePermission('users', 'MANAGE'),
            ),
        ]
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
