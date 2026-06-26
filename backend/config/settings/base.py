import os
from datetime import timedelta

import environ
from pathlib import Path

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
    CORS_ALLOWED_ORIGINS=(list, ['http://localhost:3000', 'http://localhost:8000']),
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('DJANGO_SECRET_KEY', default='insecure-dev-key-change-in-production')
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env('ALLOWED_HOSTS')

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_extensions',
    'django_filters',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'oauth2_provider',
    'drf_spectacular',
    'axes',
    'import_export',
    'csp',
    'django_celery_beat',
    'django_celery_results',

    'config.apps.CoreConfig',
    'apps.core',
    'apps.users',
    'apps.user_management',
    'apps.security_management',
    'apps.audit_management',
    'apps.authentication',
    'apps.partners',
    'apps.partner_onboarding',
    'apps.dashboard',
    'apps.common',
    'apps.system_parameters',
    'apps.ai_assistant',
    'apps.governance',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
    'csp.middleware.CSPMiddleware',
    'apps.core.middleware.RequestLoggingMiddleware',
    'apps.core.middleware.UniqueRequestIDMiddleware',
    'apps.core.middleware.UserActivityMiddleware',
    'apps.governance.middleware.AuditContextMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL', default='sqlite:///db.sqlite3')
}

AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
    {'NAME': 'apps.users.validators.ComplexPasswordValidator'},
    {'NAME': 'apps.users.validators.PasswordHistoryValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Harare'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

LOGIN_URL = 'admin:login'
LOGOUT_URL = 'admin:logout'

CORS_ALLOWED_ORIGINS = env('CORS_ALLOWED_ORIGINS')
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-request-id',
    'x-requested-with',
]

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True

CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        'default-src': ("'self'",),
        'style-src': ("'self'", "'unsafe-inline'"),
        'script-src': ("'self'", "'unsafe-inline'", "'unsafe-eval'"),
        'img-src': ("'self'", "data:", "https://cdn.jsdelivr.net"),
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'apps.core.pagination.StandardPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/hour',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
    'DEFAULT_RENDERER_CLASSES': [
        'djangorestframework_camel_case.render.CamelCaseJSONRenderer',
        'djangorestframework_camel_case.render.CamelCaseBrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'djangorestframework_camel_case.parser.CamelCaseJSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'COERCE_DECIMAL_TO_STRING': True,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': env('JWT_SECRET_KEY', default=SECRET_KEY),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_OBTAIN_SERIALIZER': 'apps.authentication.serializers.CustomTokenObtainPairSerializer',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'ZIC Insurance API',
    'DESCRIPTION': 'Zanzibar Insurance Corporation - Enterprise API Gateway',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/v[0-9]',
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
    'SWAGGER_UI_DIST': 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5',
    'COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATIONS': True,
    'ENABLE_DJANGO_DEPLOY_CHECK': False,
    'TAGS': [
        {'name': 'Authentication', 'description': 'Authentication & Authorization'},
        {'name': 'Users', 'description': 'User management'},
        {'name': 'Partners', 'description': 'Partner onboarding & management'},
        {'name': 'Dashboard', 'description': 'Dashboard aggregation'},
        {'name': 'Health', 'description': 'System health checks'},
    ],
}

OAUTH2_PROVIDER = {
    'ACCESS_TOKEN_EXPIRE_SECONDS': 3600,
    'REFRESH_TOKEN_EXPIRE_SECONDS': 86400 * 7,
    'AUTHORIZATION_CODE_EXPIRE_SECONDS': 300,
    'CLIENT_ID_GENERATOR_CLASS': 'oauth2_provider.generators.ClientIdGenerator',
    'CLIENT_SECRET_GENERATOR_CLASS': 'oauth2_provider.generators.ClientSecretGenerator',
    'SCOPES': {
        'read': 'Read access',
        'write': 'Write access',
        'read:profile': 'Read user profile',
        'write:profile': 'Update user profile',
        'read:partners': 'Read partner data',
        'write:partners': 'Write partner data',
    },
}

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_ENABLE_ADMIN = True
AXES_RESET_ON_SUCCESS = True

DEEPSEEK_API_KEY = env('DEEPSEEK_API_KEY', default='')

CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/1')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/2')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Harare'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

JAZZMIN_SETTINGS = {
    'site_title': 'ZIC Insurance',
    'site_header': 'Zanzibar Insurance Corporation',
    'site_brand': 'ZIC',
    'welcome_sign': 'Welcome to ZIC Insurance Portal',
    'copyright': 'Zanzibar Insurance Corporation',
    'search_model': 'users.User',
    'user_avatar': None,
    'topmenu_links': [
        {'name': 'Home', 'url': 'admin:index', 'permissions': ['auth.view_user']},
    ],
    'show_sidebar': True,
    'navigation_expanded': True,
    'hide_apps': ['users', 'auth', 'token_blacklist', 'oauth2_provider',
                   'django_celery_beat', 'django_celery_results',
                   'config', 'core', 'common', 'dashboard', 'authentication'],
    'hide_models': [],
    'order_with_respect_to': ['user_management', 'security_management',
                               'audit_management', 'partners', 'axes'],
    'custom_links': {},
    'icons': {
        'user_management.user': 'fas fa-users',
        'user_management.usergroup': 'fas fa-user-tag',
        'user_management.userpermission': 'fas fa-shield-alt',
        'user_management.permissiongroup': 'fas fa-layer-group',
        'security_management.usersession': 'fas fa-clock',
        'security_management.userotp': 'fas fa-qrcode',
        'security_management.twofactorauth': 'fas fa-lock',
        'audit_management.useractivitylog': 'fas fa-history',
        'partners.partner': 'fas fa-handshake',
        'axes.accessattempt': 'fas fa-shield',
        'axes.accesslog': 'fas fa-list',
    },
    'default_icon_parents': 'fas fa-chevron-circle-right',
    'default_icon_children': 'fas fa-circle',
    'related_modal_active': False,
    'custom_css': 'admin/css/material3.css',
    'custom_js': None,
    'use_google_fonts_cdn': True,
    'show_ui_builder': False,
    'changeform_format': 'horizontal_tabs',
    'changeform_format_overrides': {},
}

JAZZMIN_UI_TWEAKS = {
    'navbar_small_text': False,
    'footer_small_text': False,
    'body_small_text': False,
    'brand_small_text': False,
    'brand_colour': 'navbar-primary',
    'accent': 'accent-primary',
    'navbar': 'navbar-white navbar-light',
    'no_navbar_border': True,
    'navbar_fixed': True,
    'layout_boxed': False,
    'footer_fixed': False,
    'sidebar_fixed': True,
    'sidebar': 'sidebar-light-primary',
    'sidebar_nav_small_text': False,
    'sidebar_disable_expand': False,
    'sidebar_nav_child_indent': False,
    'sidebar_nav_compact_style': False,
    'sidebar_nav_legacy_style': False,
    'sidebar_nav_flat_style': True,
    'theme': 'default',
    'dark_mode_theme': None,
    'button_classes': {
        'primary': 'btn-primary',
        'secondary': 'btn-secondary',
        'info': 'btn-info',
        'warning': 'btn-warning',
        'danger': 'btn-danger',
        'success': 'btn-success',
    },
}

IMPORT_EXPORT_USE_TRANSACTIONS = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'structlog': {
            '()': 'apps.core.logging.ZICLogFormatter',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'fmt': '%(timestamp)s %(level)s %(name)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'structlog',
        },
        'info_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'info.log',
            'formatter': 'json',
            'maxBytes': 10485760,
            'backupCount': 5,
            'level': 'INFO',
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'error.log',
            'formatter': 'json',
            'maxBytes': 10485760,
            'backupCount': 5,
            'level': 'ERROR',
        },
        'debug_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'debug.log',
            'formatter': 'json',
            'maxBytes': 10485760,
            'backupCount': 5,
            'level': 'DEBUG',
        },
    },
    'root': {
        'handlers': ['console', 'info_file', 'error_file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'info_file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'info_file', 'error_file', 'debug_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'info_file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
