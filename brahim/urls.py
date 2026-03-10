import importlib.util

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.api.v1.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api/v1/notifications/', include('apps.notifications.api.v1.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/redoc/', SpectacularRedocView.as_view(), name='redoc'),
    path('api/swagger/', SpectacularSwaggerView.as_view(), name='swagger'),
    path('api/membersNsubscription/', include('apps.membersNsubscription.urls')),
]

if importlib.util.find_spec('django_prometheus') is not None:
    urlpatterns.insert(0, path('', include('django_prometheus.urls')))
