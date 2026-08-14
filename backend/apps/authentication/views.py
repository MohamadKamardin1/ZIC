import logging

from django.contrib.auth import logout
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView

from apps.partners.serializers import PartnerContextSerializer
from apps.users.models import User, UserOTP
from apps.users.serializers import ChangePasswordSerializer, ReportCategorySerializer, UserListSerializer

from . import services
from .serializers import (
    ConfirmResetPasswordSerializer,
    Disable2FASerializer,
    LoginSerializer,
    RegisterSerializer,
    RequestOTPSerializer,
    ResetPasswordSerializer,
    Setup2FASerializer,
    Verify2FASerializer,
    VerifyOTPSerializer,
)

logger = logging.getLogger('apps.authentication.views')


def _meta():
    return services.response_meta()


def _success(message, data=None, code=status.HTTP_200_OK, **kwargs):
    return Response({
        'success': True,
        'status_code': code,
        'message': message,
        'data': data,
        'meta': _meta(),
        **kwargs,
    }, status=code)


def _user_payload(user):
    user_data = UserListSerializer(user).data
    permissions_list = []
    for group in user.groups.prefetch_related('permissions').all():
        permissions_list.extend(
            {'module': permission.module, 'action': permission.action}
            for permission in group.permissions.all()
        )
    seen = set()
    user_data['permissions'] = []
    for permission in permissions_list:
        key = (permission['module'], permission['action'])
        if key not in seen:
            seen.add(key)
            user_data['permissions'].append(permission)
    user_data['groups'] = list(user.groups.values_list('name', flat=True))
    user_data['visible_report_categories'] = ReportCategorySerializer(
        user.visible_report_categories(), many=True,
    ).data
    visible_partners = user.visible_partners()
    current_partner = user.current_partner()
    user_data['partner_context'] = {
        'current_partner': PartnerContextSerializer(current_partner).data if current_partner else None,
        'partner_ids': [str(partner_id) for partner_id in visible_partners.values_list('id', flat=True)],
        'partner_count': visible_partners.count(),
    }
    return user_data


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        if serializer.validated_data.get('requires_2fa'):
            return _success('OTP code required', {'requires_2fa': True, 'user_id': str(user.id)})
        services.create_session(request, user)
        return _success('Login successful', {
            **services.tokens_for_user(user),
            'user': _user_payload(user),
        })


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        services.logout_user(request, request.data.get('refresh_token'))
        logout(request)
        return _success('Logged out successfully')


class TokenRefreshView(BaseTokenRefreshView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            return _success('Token refreshed', response.data)
        return response


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return _success(
            'Registration successful. Awaiting approval.',
            {'user_id': str(user.id), 'requires_approval': True},
            status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        otp_code = request.data.get('otp_code')
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        otp = UserOTP.objects.filter(
            user=user, otp_code=otp_code,
            otp_type=UserOTP.OTPType.EMAIL_VERIFICATION,
            is_used=False, expires_at__gt=timezone.now(),
        ).last()
        if otp is None:
            return Response({'error': 'Invalid or expired OTP'}, status=status.HTTP_400_BAD_REQUEST)
        otp.is_used = True
        otp.save(update_fields=['is_used'])
        user.email_verified = True
        user.email_verified_at = timezone.now()
        user.save(update_fields=['email_verified', 'email_verified_at'])
        return _success('Email verified successfully')


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_password_reset(serializer.validated_data['email'])
        return _success('If the email exists, an OTP has been sent.')


class ConfirmResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ConfirmResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.confirm_password_reset(
                serializer.validated_data['token'],
                serializer.validated_data['new_password'],
                request,
            )
        except services.IAMServiceError as exc:
            return Response({'error': exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return _success('Password reset successfully')


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        try:
            services.set_password(request.user, serializer.validated_data['new_password'], request)
        except services.IAMServiceError as exc:
            return Response({'error': exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return _success('Password changed successfully')


class Setup2FAView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        secret, otp_uri, backup_codes = services.setup_totp(request.user)
        return _success('2FA setup initiated', {
            'qr_code_url': Setup2FASerializer().get_qr_code(otp_uri),
            'secret': secret,
            'backup_codes': backup_codes,
        })


class Verify2FAView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = Verify2FASerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.verify_totp(request.user, serializer.validated_data['otp_code'], request)
        except services.IAMServiceError as exc:
            return Response({'error': exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return _success('2FA enabled successfully', {'enabled': True})


class Disable2FAView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = Disable2FASerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        services.disable_totp(request.user, request)
        return _success('2FA disabled successfully')


class RequestOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = serializer.validated_data['email_or_phone']
        user = User.objects.filter(email__iexact=contact).first() if '@' in contact else User.objects.filter(phone_number=contact).first()
        if user:
            otp = UserOTP.generate_otp(user, UserOTP.OTPType.LOGIN)
            logger.info('OTP generated', extra={'otp_id': str(otp.id), 'method': serializer.validated_data['method']})
        return _success('If the contact exists, an OTP has been sent.')


class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = serializer.validated_data['email_or_phone']
        user = User.objects.filter(email__iexact=contact).first() if '@' in contact else User.objects.filter(phone_number=contact).first()
        otp = None
        if user:
            otp = UserOTP.objects.filter(
                user=user, otp_code=serializer.validated_data['otp_code'],
                otp_type=UserOTP.OTPType.LOGIN, is_used=False,
                expires_at__gt=timezone.now(),
            ).last()
        if otp is None:
            return Response({'error': 'Invalid or expired OTP'}, status=status.HTTP_400_BAD_REQUEST)
        otp.is_used = True
        otp.save(update_fields=['is_used'])
        return _success('OTP verified')


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return _success('User info retrieved', {'user': _user_payload(request.user)})
