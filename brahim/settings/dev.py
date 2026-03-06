
from .base import *

DEBUG = True

# Use env-configurable backend in dev (console by default).
EMAIL_BACKEND = env(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend',
)

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

## Verify the structure looks like this
'''
brahim/
├── __init__.py      ✅  imports celery_app
├── celery.py        ✅  Celery app config
├── settings/
│   ├── base.py      ✅  all CELERY_* config here
│   ├── dev.py       ✅  DEBUG=True, console email
│   └── prod.py      (leave for later)
├── urls.py          (untouched for now)
├── asgi.py
└── wsgi.py
'''
