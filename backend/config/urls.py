from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from apps.core.views import health_check, liveness_check, readiness_check
from apps.authentication.views import AccessMetadataView
from apps.ol_quotations.views import OLPlanSearchView
from apps.ol_quotations.option_views import OLOptionRegistryView

api_v1_patterns = [
    path('health/', health_check, name='health-check'),
    path('live/', liveness_check, name='liveness-check'),
    path('ready/', readiness_check, name='readiness-check'),
    path('auth/', include('apps.authentication.urls')),
    path('iam/me/access/', AccessMetadataView.as_view(), name='iam-me-access'),
    path('users/', include('apps.users.urls')),
    path('partners/', include('apps.partners.urls')),
    path('onboarding/', include('apps.partner_onboarding.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('system-parameters/', include('apps.system_parameters.urls')),
    path('governance/', include('apps.governance.urls')),
    path('ai/', include('apps.ai_assistant.urls')),
    path('group-life/', include('apps.group_life.urls')),
    path('ordinary-life/', include('apps.ordinary_life.urls')),
    path('ol-parameters/', include('apps.ol_parameters.urls')),
    path('ol/plans/search/', OLPlanSearchView.as_view(), name='ol-plan-search-root'),
    path('ol/options/<str:entity>/', OLOptionRegistryView.as_view(), name='ol-option-registry-root'),
    path('ol-quotations/', include('apps.ol_quotations.urls')),
    path('ol/quotations/', include('apps.ol_quotations.urls')),
    path('group-credit/', include('apps.group_credit.urls')),
    path('front-office/', include('apps.front_office.urls')),
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
