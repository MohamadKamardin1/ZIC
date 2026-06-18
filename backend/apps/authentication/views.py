import logging

from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import logout

from apps.users.models import User, UserOTP, TwoFactorAuth, UserSession, UserActivityLog
from .serializers import (
    LoginSerializer, RegisterSerializer, ResetPasswordSerializer,
    ConfirmResetPasswordSerializer, Setup2FASerializer,
    Verify2FASerializer, Disable2FASerializer,
    RequestOTPSerializer, VerifyOTPSerializer,
)

logger = logging.getLogger('apps.authentication.views')


def _get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh),
        'access_expires_in': settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds(),
        'refresh_expires_in': settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
    }


def _create_user_session(request, user):
    session = UserSession.objects.create(
        user=user,
        session_key=request.session.session_key or '',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
        device_type=_detect_device_type(request),
    )
    return session


def _detect_device_type(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    if 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
        return 'MOBILE'
    if 'tablet' in user_agent or 'ipad' in user_agent:
        return 'TABLET'
    return 'WEB'


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={
                'request': request,
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            }
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        if serializer.validated_data.get('requires_2fa'):
            return Response({
                'success': True,
                'status_code': 200,
                'message': 'OTP code required',
                'data': {'requires_2fa': True, 'user_id': str(user.id)},
                'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
            })

        tokens = _get_tokens_for_user(user)
        _create_user_session(request, user)

        from apps.users.serializers import UserListSerializer
        user_data = UserListSerializer(user).data

        return Response({
            'success': True,
            'status_code': 200,
            'message': 'Login successful',
            'data': {**tokens, 'user': user_data},
            'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
        })


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            UserSession.objects.filter(
                user=request.user, is_active=True
            ).update(is_active=False)

            UserActivityLog.objects.create(
                user=request.user,
                action_type='LOGOUT',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
            )

            logout(request)
        except Exception as e:
            logger.error(f'Logout error: {str(e)}')

        return Response({
            'success': True,
            'status_code': 200,
            'message': 'Logged out successfully',
            'data': None,
            'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
        })


class TokenRefreshView(BaseTokenRefreshView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            return Response({
                'success': True,
                'status_code': 200,
                'message': 'Token refreshed',
                'data': response.data,
                'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
            })
        return response


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            'success': True,
            'status_code': 201,
            'message': 'Registration successful. Awaiting approval.',
            'data': {'user_id': str(user.id), 'requires_approval': True},
            'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
        }, status=status.HTTP_201_CREATED)


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        otp_code = request.data.get('otp_code')
        try:
            user = User.objects.get(email=email)
            otp = UserOTP.objects.filter(
                user=user, otp_code=otp_code,
                otp_type='EMAIL_VERIFICATION', is_used=False
            ).last()
            if otp and otp.is_valid:
                otp.is_used = True
                otp.save()
                return Response({
                    'success': True,
                    'status_code': 200,
                    'message': 'Email verified successfully',
                    'data': None,
                    'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
                })
            return Response({'error': 'Invalid or expired OTP'}, status=400)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
            otp = UserOTP.generate_otp(user, 'PASSWORD_RESET')
            logger.info(f'Password reset OTP sent to {email}: {otp.otp_code}')
        except User.DoesNotExist:
            pass
        return Response({
            'success': True,
            'status_code': 200,
            'message': 'If the email exists, an OTP has been sent.',
            'data': None,
            'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
        })


class ConfirmResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ConfirmResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        try:
            otp = UserOTP.objects.get(
                otp_code=token, otp_type='PASSWORD_RESET',
                is_used=False, expires_at__gt=timezone.now()
            )
            otp.is_used = True
            otp.save()
            otp.user.set_password(new_password)
            otp.user.save()
            return Response({
                'success': True,
                'status_code': 200,
                'message': 'Password reset successfully',
                'data': None,
                'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
            })
        except UserOTP.DoesNotExist:
            return Response({'error': 'Invalid or expired token'}, status=400)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.users.serializers import ChangePasswordSerializer
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.password_changed_at = timezone.now()
        request.user.save()
        UserActivityLog.objects.create(
            user=request.user,
            action_type='PASSWORD_CHANGE',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
        )
        return Response({
            'success': True,
            'status_code': 200,
            'message': 'Password changed successfully',
            'data': None,
            'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
        })


class Setup2FAView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        two_factor, created = TwoFactorAuth.objects.get_or_create(user=request.user)
        setup_serializer = Setup2FASerializer()
        secret, otp_uri = setup_serializer.get_otp_uri(request.user)
        qr_code = setup_serializer.get_qr_code(otp_uri)
        two_factor.app_secret = secret
        two_factor.save()
        backup_codes = two_factor.generate_backup_codes()
        UserActivityLog.objects.create(
            user=request.user,
            action_type='TWO_FA_SETUP',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
        )
        return Response({
            'success': True,
            'status_code': 200,
            'message': '2FA setup initiated',
            'data': {
                'qr_code_url': qr_code,
                'secret': secret,
                'backup_codes': backup_codes,
            },
            'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
        })


class Verify2FAView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = Verify2FASerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp_code = serializer.validated_data['otp_code']
        try:
            two_factor = TwoFactorAuth.objects.get(user=request.user)
            import pyotp
            totp = pyotp.TOTP(two_factor.app_secret)
            if totp.verify(otp_code):
                two_factor.is_active = True
                two_factor.setup_completed_at = timezone.now()
                two_factor.save()
                request.user.is_2fa_enabled = True
                request.user.save(update_fields=['is_2fa_enabled'])
                return Response({
                    'success': True,
                    'status_code': 200,
                    'message': '2FA enabled successfully',
                    'data': {'backup_codes': two_factor.backup_codes},
                    'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
                })
            return Response({'error': 'Invalid OTP code'}, status=400)
        except TwoFactorAuth.DoesNotExist:
            return Response({'error': '2FA not set up. Call setup-2fa first.'}, status=400)


class Disable2FAView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = Disable2FASerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        TwoFactorAuth.objects.filter(user=request.user).update(
            is_active=False, app_secret=None, backup_codes=[]
        )
        request.user.is_2fa_enabled = False
        request.user.save(update_fields=['is_2fa_enabled'])
        UserActivityLog.objects.create(
            user=request.user,
            action_type='TWO_FA_DISABLE',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
        )
        return Response({
            'success': True,
            'status_code': 200,
            'message': '2FA disabled successfully',
            'data': None,
            'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
        })


class RequestOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email_or_phone = serializer.validated_data['email_or_phone']
        method = serializer.validated_data['method']
        try:
            if '@' in email_or_phone:
                user = User.objects.get(email=email_or_phone)
            else:
                user = User.objects.get(phone_number=email_or_phone)
            otp = UserOTP.generate_otp(user, 'LOGIN')
            logger.info(f'OTP for {email_or_phone} ({method}): {otp.otp_code}')
        except User.DoesNotExist:
            pass
        return Response({
            'success': True,
            'status_code': 200,
            'message': 'If the contact exists, an OTP has been sent.',
            'data': None,
            'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
        })


class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email_or_phone = serializer.validated_data['email_or_phone']
        otp_code = serializer.validated_data['otp_code']
        try:
            if '@' in email_or_phone:
                user = User.objects.get(email=email_or_phone)
            else:
                user = User.objects.get(phone_number=email_or_phone)
            otp = UserOTP.objects.filter(
                user=user, otp_code=otp_code,
                otp_type='LOGIN', is_used=False,
                expires_at__gt=timezone.now()
            ).last()
            if otp:
                otp.is_used = True
                otp.save()
                return Response({
                    'success': True,
                    'status_code': 200,
                    'message': 'OTP verified',
                    'data': None,
                    'meta': {'timestamp': timezone.now().isoformat(), 'version': 'v1'},
                })
        except User.DoesNotExist:
            pass
        return Response({'error': 'Invalid or expired OTP'}, status=400)


class CustomTokenObtainPairSerializer:
    pass
