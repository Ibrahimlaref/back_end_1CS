import time
from django.http import JsonResponse
from django.db import connection
EXEMPT_PATHS = (
    '/api/users/v1/auth/register/',
    '/api/users/v1/auth/verify-otp/',
    '/api/users/v1/auth/resend-otp/',
    '/api/users/v1/auth/login/',
    '/api/users/v1/auth/refresh/',
    '/api/users/v1/auth/reset-password/',
    '/health',
    '/admin/',
    '/api/schema/',
    '/api/redoc/',
    '/api/swagger/',
)

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(p) for p in EXEMPT_PATHS):
            return self.get_response(request)

        gym_id = getattr(request, 'gym_id', None)

        if gym_id is None:
            return JsonResponse(
                {'error': 'gym_id required', 'code': 'tenant_required'},
                status=403
            )

        t_start = time.monotonic()

        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL app.current_gym_id = %s", [str(gym_id)])

        response = self.get_response(request)
        response['X-Tenant-Ms'] = f"{(time.monotonic() - t_start) * 1000:.3f}"
        return response
