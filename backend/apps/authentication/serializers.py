import logging
import pyotp
import qrcode
import base64
import io

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from django.conf import settings

from apps.users.models import User, UserOTP, TwoFactorAuth, UserSession, UserActivityLog

logger = logging.getLogger('apps.authentication.serializers')


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, help_text='Username or email address')
    password = serializers.CharField(required=True, write_only=True)
    otp_code = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        username_or_email = attrs.get('username')
        password = attrs.get('password')
        otp_code = attrs.get('otp_code', '')
        request = self.context.get('request')

        # Try to find user by username first, then by email
        user = None
        try:
            user = User.objects.get(username=username_or_email)
        except User.DoesNotExist:
            # If username not found, try email
            try:
                user = User.objects.get(email=username_or_email)
            except User.DoesNotExist:
                raise serializers.ValidationError('Invalid credentials.')

        if not user.is_active:
            raise serializers.ValidationError('Account is disabled.')

        if user.is_account_locked:
            raise serializers.ValidationError(
                f'Account locked until {user.account_locked_until.strftime("%Y-%m-%d %H:%M")}.'
            )

        # Authenticate with the actual username
        auth_user = authenticate(request=request, username=user.username, password=password)
        if auth_user is None:
            user.record_failed_login()
            raise serializers.ValidationError('Invalid credentials.')

        if not auth_user.is_approved:
            raise serializers.ValidationError('Account pending approval.')

        if auth_user.is_2fa_enabled and not otp_code:
            attrs['requires_2fa'] = True
            attrs['user'] = auth_user
            return attrs

        if auth_user.is_2fa_enabled and otp_code:
            two_factor = TwoFactorAuth.objects.filter(user=auth_user, is_active=True).first()
            if two_factor:
                totp = pyotp.TOTP(two_factor.app_secret)
                if not totp.verify(otp_code):
                    if not two_factor.verify_backup_code(otp_code):
                        raise serializers.ValidationError('Invalid OTP code.')

        auth_user.reset_failed_login()
        auth_user.last_login = timezone.now()
        auth_user.save(update_fields=['last_login', 'failed_login_attempts', 'account_locked_until'])

        UserActivityLog.objects.create(
            user=auth_user,
            action_type='LOGIN',
            ip_address=self.context.get('ip_address', ''),
            user_agent=self.context.get('user_agent', '')[:255],
        )

        attrs['user'] = auth_user
        attrs['requires_2fa'] = False
        return attrs


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone_number',
        ]

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already taken.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already registered.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.is_active = True
        user.is_approved = False
        user.save()
        return user


class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True)


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class ConfirmResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Passwords do not match.'})
        return attrs


class Setup2FASerializer(serializers.Serializer):
    def get_otp_uri(self, user):
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        otp_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name='ZIC Insurance'
        )
        return secret, otp_uri

    def get_qr_code(self, otp_uri):
        qr = qrcode.make(otp_uri)
        buffer = io.BytesIO()
        qr.save(buffer, format='PNG')
        buffer.seek(0)
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        return f'data:image/png;base64,{qr_base64}'


class Verify2FASerializer(serializers.Serializer):
    otp_code = serializers.CharField(required=True)


class Disable2FASerializer(serializers.Serializer):
    password = serializers.CharField(required=True)

    def validate_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Incorrect password.')
        return value


class RequestOTPSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(required=True)
    method = serializers.ChoiceField(choices=['SMS', 'EMAIL', 'AUTH_APP'], required=True)


class VerifyOTPSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(required=True)
    otp_code = serializers.CharField(required=True)
