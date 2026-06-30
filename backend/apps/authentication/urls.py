from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='auth-login'),
    path('logout/', views.LogoutView.as_view(), name='auth-logout'),
    path('refresh/', views.TokenRefreshView.as_view(), name='auth-refresh'),
    path('register/', views.RegisterView.as_view(), name='auth-register'),
    path('verify-email/', views.VerifyEmailView.as_view(), name='auth-verify-email'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='auth-reset-password'),
    path('confirm-reset-password/', views.ConfirmResetPasswordView.as_view(), name='auth-confirm-reset-password'),
    path('change-password/', views.ChangePasswordView.as_view(), name='auth-change-password'),
    path('setup-2fa/', views.Setup2FAView.as_view(), name='auth-setup-2fa'),
    path('verify-2fa/', views.Verify2FAView.as_view(), name='auth-verify-2fa'),
    path('disable-2fa/', views.Disable2FAView.as_view(), name='auth-disable-2fa'),
    path('me/', views.MeView.as_view(), name='auth-me'),
    path('request-otp/', views.RequestOTPView.as_view(), name='auth-request-otp'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='auth-verify-otp'),
]
