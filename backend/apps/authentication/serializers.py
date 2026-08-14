import base64
import io

import pyotp
import qrcode
from rest_framework import serializers

from apps.users.models import User

from .services import IAMServiceError, authenticate_login


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, help_text='Username or email address')
    password = serializers.CharField(required=True, write_only=True)
    otp_code = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        try:
            result = authenticate_login(
                identifier=attrs['username'],
                password=attrs['password'],
                request=self.context.get('request'),
                otp_code=attrs.get('otp_code', ''),
            )
        except IAMServiceError as exc:
            raise serializers.ValidationError(exc.message) from exc
        attrs['user'] = result.user
        attrs['requires_2fa'] = result.requires_mfa
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
        user.status = User.AccountStatus.PENDING_ACTIVATION
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
        return secret, totp.provisioning_uri(name=user.email, issuer_name='ZIC Insurance')

    def get_qr_code(self, otp_uri):
        qr = qrcode.make(otp_uri)
        buffer = io.BytesIO()
        qr.save(buffer, format='PNG')
        return f'data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}'


class Verify2FASerializer(serializers.Serializer):
    otp_code = serializers.CharField(required=True)


class Disable2FASerializer(serializers.Serializer):
    password = serializers.CharField(required=True, write_only=True)

    def validate_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError('Incorrect password.')
        return value


class RequestOTPSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(required=True)
    method = serializers.ChoiceField(choices=['SMS', 'EMAIL', 'AUTH_APP'], required=True)


class VerifyOTPSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(required=True)
    otp_code = serializers.CharField(required=True)
