import logging

from django.contrib.auth.password_validation import validate_password
from django.core import exceptions as django_exceptions
from rest_framework import serializers

from .models import (
    NotificationPreference,
    PermissionGroup,
    User,
    UserActivityLog,
    UserGroup,
    UserPermission,
    UserSession,
)

logger = logging.getLogger('apps.users.serializers')


class UserListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    active_sessions_count = serializers.IntegerField(read_only=True)
    groups = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'user_type', 'status', 'partner_id', 'is_active', 'is_approved',
            'is_2fa_enabled', 'mfa_required', 'sso_provider', 'sso_subject',
            'last_password_changed_at', 'email_verified', 'phone_verified',
            'department', 'job_title', 'employee_id',
            'last_login', 'last_activity', 'date_joined',
            'active_sessions_count', 'groups',
        ]


class UserDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    is_account_locked = serializers.BooleanField(read_only=True)
    is_password_expired = serializers.BooleanField(read_only=True)
    groups = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'user_type', 'status', 'partner_id', 'is_active', 'is_approved',
            'is_2fa_enabled', 'mfa_required', 'sso_provider', 'sso_subject',
            'last_password_changed_at', 'otp_method', 'is_account_locked',
            'is_password_expired', 'email_verified', 'email_verified_at',
            'phone_verified', 'phone_verified_at',
            'failed_login_attempts', 'account_locked_until',
            'must_change_password', 'password_changed_at',
            'avatar', 'date_of_birth', 'department', 'job_title',
            'employee_id', 'terms_accepted_at',
            'last_login', 'last_activity', 'last_ip_address',
            'date_joined', 'groups',
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    password_confirm = serializers.CharField(write_only=True, required=True)
    group_ids = serializers.ListField(child=serializers.UUIDField(), required=False)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone_number',
            'user_type', 'department', 'job_title', 'employee_id',
            'date_of_birth', 'group_ids',
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        try:
            validate_password(attrs['password'])
        except django_exceptions.ValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)}) from e
        return attrs

    def create(self, validated_data):
        group_ids = validated_data.pop('group_ids', [])
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        if group_ids:
            user.groups.add(*UserGroup.objects.filter(id__in=group_ids))
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    group_ids = serializers.ListField(child=serializers.UUIDField(), required=False)

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number',
            'user_type', 'is_active', 'is_approved',
            'department', 'job_title', 'employee_id',
            'date_of_birth', 'avatar', 'group_ids',
        ]

    def update(self, instance, validated_data):
        group_ids = validated_data.pop('group_ids', None)
        instance = super().update(instance, validated_data)
        if group_ids is not None:
            instance.groups.set(UserGroup.objects.filter(id__in=group_ids))
        return instance


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'user_type', 'is_2fa_enabled', 'otp_method',
            'email_verified', 'phone_verified',
            'avatar', 'date_of_birth', 'department', 'job_title', 'employee_id',
            'last_login', 'last_activity', 'date_joined',
        ]
        read_only_fields = ['id', 'username', 'email', 'user_type',
                             'email_verified', 'phone_verified',
                             'date_joined', 'last_login', 'last_activity']

    def update(self, instance, validated_data):
        if 'first_name' in validated_data:
            instance.first_name = validated_data['first_name']
        if 'last_name' in validated_data:
            instance.last_name = validated_data['last_name']
        if 'phone_number' in validated_data:
            instance.phone_number = validated_data['phone_number']
        instance.save()
        return instance


class UserGroupSerializer(serializers.ModelSerializer):
    permission_count = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = UserGroup
        fields = [
            'id', 'name', 'code', 'description', 'group_type',
            'is_active', 'is_system', 'is_system_group',
            'permission_count', 'user_count', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'is_system', 'is_system_group', 'permission_count',
            'user_count', 'created_at', 'updated_at',
        ]

    def validate_code(self, value):
        return value.strip().upper().replace(' ', '_')

    def get_permission_count(self, obj):
        return obj.permissions.filter(is_active=True).count()

    def get_user_count(self, obj):
        return obj.users.filter(is_active=True).count()


class UserGroupDetailSerializer(UserGroupSerializer):
    permissions = serializers.SerializerMethodField()
    users = serializers.SerializerMethodField()

    class Meta(UserGroupSerializer.Meta):
        fields = UserGroupSerializer.Meta.fields + ['permissions', 'users']

    def get_permissions(self, obj):
        return UserPermissionSerializer(obj.permissions.all(), many=True).data

    def get_users(self, obj):
        return [
            {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'user_type': user.user_type,
                'status': user.status,
            }
            for user in obj.users.all()
        ]


class UserPermissionSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source='codename', read_only=True)

    class Meta:
        model = UserPermission
        fields = [
            'id', 'name', 'code', 'codename', 'module', 'action',
            'resource_type', 'description', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'code', 'codename', 'created_at']


class GroupAssignmentSerializer(serializers.Serializer):
    permission_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=True,
    )
    user_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=True,
    )


class PermissionGroupSerializer(serializers.ModelSerializer):
    permission_count = serializers.SerializerMethodField()
    permissions = UserPermissionSerializer(many=True, read_only=True)

    class Meta:
        model = PermissionGroup
        fields = [
            'id', 'name', 'module_code', 'description',
            'permissions', 'permission_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_permission_count(self, obj):
        return obj.permissions.count()


class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = [
            'id', 'device_type', 'ip_address', 'user_agent',
            'login_time', 'last_activity', 'is_active',
        ]
        read_only_fields = ['id', 'login_time']


class UserActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivityLog
        fields = [
            'id', 'user', 'action_type', 'ip_address',
            'user_agent', 'timestamp', 'details',
        ]
        read_only_fields = ['id', 'user', 'action_type', 'ip_address',
                             'user_agent', 'timestamp', 'details']


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    new_password_confirm = serializers.CharField(required=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Passwords do not match.'})
        if attrs['current_password'] == attrs['new_password']:
            raise serializers.ValidationError(
                {'new_password': 'New password cannot be the same as current password.'}
            )
        try:
            validate_password(attrs['new_password'], self.context['request'].user)
        except django_exceptions.ValidationError as e:
            raise serializers.ValidationError({'new_password': list(e.messages)}) from e
        return attrs


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'email_notifications', 'sms_notifications',
            'push_notifications', 'login_alerts', 'marketing_emails',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
