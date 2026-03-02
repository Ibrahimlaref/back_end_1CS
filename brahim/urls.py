from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


def health(request):
    from django.db import connection
    import redis
    from django.conf import settings

    checks = {'db': False, 'redis': False}

    try:
        connection.ensure_connection()
        checks['db'] = True
    except Exception:
        pass

    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        checks['redis'] = True
    except Exception:
        pass

    status_code = 200 if all(checks.values()) else 503
    return JsonResponse(checks, status=status_code)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health', health),
    path('api/users/', include('apps.users.urls')), 
    path('api/schema/',   SpectacularAPIView.as_view(),        name='schema'),
    path('api/redoc/',    SpectacularRedocView.as_view(),       name='redoc'),
    path('api/swagger/',  SpectacularSwaggerView.as_view(),     name='swagger'),
]