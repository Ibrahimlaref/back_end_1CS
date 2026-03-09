"""
Django settings for brahim project.
"""

from pathlib import Path
from celery.schedules import crontab
import importlib.util
import environ


BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

BASE_DIR = Path(__file__).resolve().parent.parent.parent

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
]
if importlib.util.find_spec('django_prometheus') is not None:
    INSTALLED_APPS.insert(0, 'django_prometheus')

MIDDLEWARE = [
    'apps.core.middleware.metrics.PrometheusBeforeMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'apps.core.middleware.correlation.CorrelationIdMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middleware.request_logging.RequestLoggingMiddleware',
    # US-001 — added after core app is created
    'apps.core.middleware.jwt_auth.JWTAuthMiddleware',
    'apps.core.middleware.tenant.TenantContextMiddleware',
    'apps.core.middleware.metrics.PrometheusAfterMiddleware',
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
    'default': env.db('DATABASE_URL')
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
REDIS_URL = env('REDIS_URL', default='redis://redis:6379/0')
_redis_cache_backend = 'django_redis.cache.RedisCache'
_redis_cache_options = {'CLIENT_CLASS': 'django_redis.client.DefaultClient'}
if importlib.util.find_spec('django_redis') is None:
    _redis_cache_backend = 'django.core.cache.backends.redis.RedisCache'
    _redis_cache_options = {}

CACHES = {
    'default': {
        'BACKEND': _redis_cache_backend,
        'LOCATION': env('REDIS_URL', default='redis://redis:6379/1'),
        'OPTIONS': _redis_cache_options,
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

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
    'apps.payments.tasks.*':      {'queue': 'payments'},
    'apps.analytics.tasks.*':     {'queue': 'analytics'},
    'apps.subscriptions.tasks.*': {'queue': 'scheduled'},
}

# Retry policy
CELERY_TASK_MAX_RETRIES = 3
CELERY_TASK_DEFAULT_RETRY_DELAY = 60

# Notifications
NOTIFICATIONS_RETRY_DELAY_SECONDS = env.int('NOTIFICATIONS_RETRY_DELAY_SECONDS', default=300)
NOTIFICATIONS_RETRY_LOOKBACK_MINUTES = env.int('NOTIFICATIONS_RETRY_LOOKBACK_MINUTES', default=10)

# Data Retention

# ─── CELERY BEAT SCHEDULE ─────────────────────────────────────────────────────
CELERY_BEAT_SCHEDULE = {
    # Expire subscriptions — every hour
    'expire_subscriptions': {
        'task': 'apps.subscriptions.tasks.expire_subscriptions',
        'schedule': crontab(minute=0),
    },
    # Resume paused memberships whose pause period has ended — daily 00:00
    'auto_resume_expired_pauses': {
        'task': 'apps.subscriptions.tasks.auto_resume_expired_pauses',
        'schedule': crontab(hour=0, minute=0),
    },
    # Lift expired suspensions — daily 01:00
    'lift_expired_suspensions': {
        'task': 'apps.subscriptions.tasks.lift_expired_suspensions',
        'schedule': crontab(hour=1, minute=0),
    },
    # Generate next week's course schedule — Sunday 23:00
    'generate_weekly_courses': {
        'task': 'apps.courses.tasks.generate_weekly_courses',
        'schedule': crontab(hour=23, minute=0, day_of_week=0),
    },
    # Recalculate member behavior scores — nightly 02:00
    'refresh_behavior_scores': {
        'task': 'apps.analytics.tasks.refresh_behavior_scores',
        'schedule': crontab(hour=2, minute=0),
    },
    # Recalculate retention risk signals — nightly 03:00
    'refresh_retention_signals': {
        'task': 'apps.analytics.tasks.refresh_retention_signals',
        'schedule': crontab(hour=3, minute=0),
    },
    'monthly-data-retention': {
        'task': 'apps.core.tasks.run_data_retention_policy',
        'schedule': crontab(day_of_month='1', hour='2', minute='0'),
    },
}

# ─── EMAIL ────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='ibrahimlaref23@gmail.com')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='ptuv mhqs iuot znhc')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@fittech.com')

# ─── ADMIN ────────────────────────────────────────────────────────────────────
ADMIN_EMAIL = env('ADMIN_EMAIL', default='ibrahimlaref23@gmail.com')

# ─── FIREBASE ─────────────────────────────────────────────────────────────────
FIREBASE_CREDENTIALS_PATH = env('FIREBASE_CREDENTIALS_PATH')

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


# ─── STATIC ───────────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@fittech.com')




EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=False)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
_json_formatter_class = (
    'pythonjsonlogger.jsonlogger.JsonFormatter'
    if importlib.util.find_spec('pythonjsonlogger') is not None
    else 'logging.Formatter'
)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'correlation': {
            '()': 'apps.core.middleware.log_filter.CorrelationIdFilter',
        },
    },
    'formatters': {
        'json': {
            '()': _json_formatter_class,
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s %(correlation_id)s %(gym_id)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'filters': ['correlation'],
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
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
        from apps.core.middleware.correlation import get_gym_id
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.django import DjangoIntegration
    except ImportError:
        pass
    else:
        def _before_send(event, hint):
            tags = event.setdefault('tags', {})
            tags['gym_id'] = get_gym_id() or 'unknown'
            return event

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration(), CeleryIntegration()],
            traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
            send_default_pii=False,
            before_send=_before_send,
        )



