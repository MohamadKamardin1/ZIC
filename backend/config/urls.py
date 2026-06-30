from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from apps.core.views import health_check

api_v1_patterns = [
    path('health/', health_check, name='health-check'),
    path('auth/', include('apps.authentication.urls')),
    path('users/', include('apps.users.urls')),
    path('partners/', include('apps.partners.urls')),
    path('onboarding/', include('apps.partner_onboarding.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('system-parameters/', include('apps.system_parameters.urls')),
    path('governance/', include('apps.governance.urls')),
    path('ai/', include('apps.ai_assistant.urls')),
    path('group-life/', include('apps.group_life.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/v1/', include((api_v1_patterns, 'api_v1'), namespace='v1')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
