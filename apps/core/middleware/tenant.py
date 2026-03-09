import time
from django.db import connection, transaction
from django.http import JsonResponse

from apps.core.middleware.correlation import set_gym_id


def _resolve_gym_id(request):
    return getattr(request, 'gym_id', None)
EXEMPT_PATHS = (
    '/api/users/v1/auth/register/',
    '/api/users/v1/auth/verify-otp/',
    '/api/users/v1/auth/resend-otp/',
    '/api/users/v1/auth/login/',
    '/api/users/v1/auth/refresh/',
    '/api/v1/notifications/webhooks/email/',
    '/health',
    '/metrics',
    '/admin/',
    '/api/schema/',
    '/api/redoc/',
    '/api/swagger/',
)

class TenantContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(p) for p in EXEMPT_PATHS):
            return self.get_response(request)

        gym_id = _resolve_gym_id(request)

        if gym_id is None:
            return JsonResponse(
                {'error': 'gym_id required', 'code': 'tenant_required'},
                status=403
            )

        t_start = time.monotonic()
        set_gym_id(gym_id)
        with transaction.atomic():
            with connection.cursor() as cursor:
                # SET LOCAL is intentional - SET would persist on pooled connections.
                cursor.execute("SET LOCAL app.current_gym_id = %s", [str(gym_id)])
            response = self.get_response(request)
        response['X-Tenant-Ms'] = f"{(time.monotonic() - t_start) * 1000:.3f}"
        return response


TenantMiddleware = TenantContextMiddleware
