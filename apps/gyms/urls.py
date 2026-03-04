from django.urls import path
from core.api.v1.views.gym_views import GymProvisionView

urlpatterns = [
    # US-002: Gym Tenant Provisioning
    # POST /platform/gyms
    path("gyms/", GymProvisionView.as_view(), name="gym-provision"),
]
