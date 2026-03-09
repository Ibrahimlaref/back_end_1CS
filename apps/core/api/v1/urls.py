
from django.urls import path

from apps.core.api.v1.views import HealthCheckView

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health-check'),
]
