from .base import *

DEBUG = True

# Extra apps only in dev
INSTALLED_APPS += [
    'django_extensions',
]

try:
    import django_migration_linter  # noqa: F401
except ImportError:
    django_migration_linter = None
else:
    INSTALLED_APPS += [
        'django_migration_linter',
    ]

# Show all SQL queries in dev
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'observability.request': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}