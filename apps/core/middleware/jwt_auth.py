import jwt
from django.conf import settings
from django.http import JsonResponse

EXEMPT_PATHS = (
    '/api/users/v1/auth/register/',
    '/api/users/v1/auth/verify-otp/',
    '/api/users/v1/auth/resend-otp/',
    '/api/users/v1/auth/login/',
    '/api/users/v1/auth/refresh/',
    '/health',
    '/admin/',
    '/api/schema/',
    '/api/redoc/',
    '/api/swagger/',
)


class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(p) for p in EXEMPT_PATHS):
            return self.get_response(request)

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header.startswith('Bearer '):
            return JsonResponse(
                {'error': 'Authorization header missing', 'code': 'auth_required'},
                status=401
            )

        token = auth_header.split(' ', 1)[1].strip()

        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired', 'code': 'token_expired'}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({'error': 'Invalid token', 'code': 'invalid_token'}, status=401)

        request.user_id = payload.get('user_id')
        request.gym_id  = payload.get('gym_id')
        request.role    = payload.get('role')
        request.jti     = payload.get('jwt_jti')

        return self.get_response(request)