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
LOGGING['loggers']['django.db.backends'] = {
    'handlers': ['console'],
    'level': 'DEBUG',
    'propagate': False,
}
