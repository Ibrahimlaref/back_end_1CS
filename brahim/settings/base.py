"""
Django settings for brahim project.
"""

from pathlib import Path
from celery.schedules import crontab
import environ


BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='dev-only-insecure-secret-key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', default=True)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# ─── APPS ─────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    "django_filters",
    'drf_spectacular',
    'django_celery_beat',

    # FitTech apps
    'apps.core',
    'apps.users',
    'apps.notifications',
    'apps.membersNsubscription',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middleware.request_logging.RequestLoggingMiddleware',
    # US-001 — added after core app is created
    'apps.core.middleware.jwt_auth.JWTAuthMiddleware',
    'apps.core.middleware.tenant.TenantMiddleware',
]

ROOT_URLCONF = 'brahim.urls'

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

WSGI_APPLICATION = 'brahim.wsgi.application'

# ─── DATABASE ─────────────────────────────────────────────────────────────────
DATABASES = {
    'default': env.db(
        'DATABASE_URL',
        default='postgres://fittech:fittech@localhost:5432/fittech_dev',
    ),
}
DATABASES['default']['CONN_MAX_AGE'] = env.int('DB_CONN_MAX_AGE', default=60)

PGBOUNCER_ENABLED = env.bool('PGBOUNCER_ENABLED', default=False)
if PGBOUNCER_ENABLED:
    # Required when using PgBouncer transaction pooling with Django.
    DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True
    DATABASES['default']['CONN_MAX_AGE'] = env.int('DB_CONN_MAX_AGE', default=0)

# ─── AUTH ─────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = 'users.User'

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# ─── JWT ──────────────────────────────────────────────────────────────────────
JWT_SECRET_KEY = env('JWT_SECRET_KEY', default=SECRET_KEY)
STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY', default='')
JWT_ACCESS_TOKEN_LIFETIME_MINUTES = 15
JWT_REFRESH_TOKEN_LIFETIME_DAYS = 7

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── I18N ─────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ─── STATIC ───────────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ORIGIN_ALLOW_ALL = env.bool('CORS_ORIGIN_ALLOW_ALL', default=True)
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

# ─── REDIS ────────────────────────────────────────────────────────────────────
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')
# Observability
REQUEST_LOGGING_ENABLED = env.bool('REQUEST_LOGGING_ENABLED', default=True)
REQUEST_LOG_SUCCESS_SAMPLE_RATE = env.float('REQUEST_LOG_SUCCESS_SAMPLE_RATE', default=0.10)
REQUEST_LOG_SLOW_MS = env.int('REQUEST_LOG_SLOW_MS', default=1000)
REQUEST_LOG_P95_ALERT_MS = env.int('REQUEST_LOG_P95_ALERT_MS', default=500)
REQUEST_LOG_BUFFER_SIZE = env.int('REQUEST_LOG_BUFFER_SIZE', default=1000)
REQUEST_LOG_BUFFER_TTL_SEC = env.int('REQUEST_LOG_BUFFER_TTL_SEC', default=900)
REQUEST_LOG_ALERT_COOLDOWN_SEC = env.int('REQUEST_LOG_ALERT_COOLDOWN_SEC', default=300)
OBSERVABILITY_PROVIDER = env('OBSERVABILITY_PROVIDER', default='stdout')
SENTRY_DSN = env('SENTRY_DSN', default='')
SENTRY_TRACES_SAMPLE_RATE = env.float('SENTRY_TRACES_SAMPLE_RATE', default=0.10)

# ─── CELERY ───────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Queue routing
CELERY_TASK_ROUTES = {
    'apps.notifications.tasks.*': {'queue': 'notifications'},
    'apps.users.tasks.send_email_task': {'queue': 'notifications'},
    'apps.users.tasks.cleanup_session_logs': {'queue': 'scheduled'},
    'apps.gyms.tasks.dispatch_welcome_email': {'queue': 'notifications'},
}

# Retry policy
CELERY_TASK_MAX_RETRIES = 3
CELERY_TASK_DEFAULT_RETRY_DELAY = 60

# ─── CELERY BEAT SCHEDULE ─────────────────────────────────────────────────────
CELERY_BEAT_SCHEDULE = {
    # Weekly session log cleanup (also seeded via django-celery-beat migration)
    'users.session-log-cleanup-weekly': {
        'task': 'apps.users.tasks.cleanup_session_logs',
        'schedule': crontab(minute=0, hour=3, day_of_week=0),
        'options': {'queue': 'scheduled'},
    },
}

# ─── EMAIL ────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=False)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@fittech.com')

# ─── ADMIN ────────────────────────────────────────────────────────────────────
ADMIN_EMAIL = env('ADMIN_EMAIL', default='admin@fittech.com')

# ─── FIREBASE ─────────────────────────────────────────────────────────────────
FIREBASE_CREDENTIALS_PATH = env('FIREBASE_CREDENTIALS_PATH', default='')

# ─── REST FRAMEWORK ───────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SPECTACULAR_SETTINGS = {
    'TITLE':       'FitTech API',
    'DESCRIPTION': 'FitTech Gym Management Platform API',
    'VERSION':     '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'plain': {
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'plain',
        },
    },
    'loggers': {
        'observability.request': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
            send_default_pii=False,
        )
    except ImportError:
        pass



