"""
Django settings for brahim project.
"""

from pathlib import Path
from celery.schedules import crontab
import environ


BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ─── SECURITY ─────────────────────────────────────────────────────────────────
SECRET_KEY = 'django-insecure-o500)e(7roy_yw)m1^%cr5vj5le5r3z596ub!&)2*n!agszwb1'
DEBUG = True
ALLOWED_HOSTS = []

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

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
    'default': env.db('DATABASE_URL')
}

# ─── AUTH ─────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = 'users.User'

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# ─── JWT ──────────────────────────────────────────────────────────────────────
JWT_SECRET_KEY = env('JWT_SECRET_KEY', default=SECRET_KEY)
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
CORS_ORIGIN_ALLOW_ALL = True

# ─── REDIS ────────────────────────────────────────────────────────────────────
REDIS_URL = env('REDIS_URL', default='redis://redis:6379/0')

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