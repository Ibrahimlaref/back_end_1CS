from django.core.exceptions import ImproperlyConfigured

from .base import *


DEBUG = False

# All production secrets must come from environment injection (Vault -> env).
SECRET_KEY = env('SECRET_KEY', default='')
JWT_SECRET_KEY = env('JWT_SECRET_KEY', default='')
STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY', default='')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])
CORS_ORIGIN_ALLOW_ALL = False
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

PGBOUNCER_ENABLED = env.bool('PGBOUNCER_ENABLED', default=True)
DATABASES['default']['CONN_MAX_AGE'] = env.int('DB_CONN_MAX_AGE', default=0 if PGBOUNCER_ENABLED else 60)
if PGBOUNCER_ENABLED:
    DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True


def _require(value, name):
    if not value:
        raise ImproperlyConfigured(f'Set the {name} environment variable')


_require(SECRET_KEY, 'SECRET_KEY')
_require(JWT_SECRET_KEY, 'JWT_SECRET_KEY')
_require(STRIPE_SECRET_KEY, 'STRIPE_SECRET_KEY')
_require(ALLOWED_HOSTS, 'ALLOWED_HOSTS')
_require(CORS_ALLOWED_ORIGINS, 'CORS_ALLOWED_ORIGINS')

if SECRET_KEY == 'dev-only-insecure-secret-key':
    raise ImproperlyConfigured('SECRET_KEY must be unique per environment')
