from django.urls import path

from apps.membersNsubscription.api.v1.views.membership import JoinGymView
from apps.membersNsubscription.api.v1.views.plans import (
    MembershipPlanListCreateView,
    MembershipPlanDetailView,
)
from apps.membersNsubscription.api.v1.views.rooms import (
    RoomListCreateView,
    RoomDetailView,
)
from apps.membersNsubscription.api.v1.views.equipment import (
    EquipmentListCreateView,
    EquipmentDetailView,
    ReportMalfunctionView,
    ManageMaintenanceReportView,
)
from apps.membersNsubscription.api.v1.views.products import (
    ProductListCreateView,
    ProductDetailView,
)
from apps.membersNsubscription.api.v1.views.AccessLog import GymScanView


urlpatterns = [
    # Join gym
    path("gyms/<uuid:gym_id>/join/", JoinGymView.as_view(), name="gym-join"),

    # Membership plans
    path("gyms/<uuid:gym_id>/plans/", MembershipPlanListCreateView.as_view(), name="plans-list"),
    path(
        "gyms/<uuid:gym_id>/plans/<uuid:plan_id>/",
        MembershipPlanDetailView.as_view(),
        name="plan-detail",
    ),

    # Rooms
    path("gyms/<uuid:gym_id>/rooms/", RoomListCreateView.as_view(), name="rooms-list"),
    path(
        "gyms/<uuid:gym_id>/rooms/<uuid:room_id>/",
        RoomDetailView.as_view(),
        name="room-detail",
    ),

    # Equipment
    path("gyms/<uuid:gym_id>/equipment/", EquipmentListCreateView.as_view(), name="equipment-list"),
    path(
        "gyms/<uuid:gym_id>/equipment/<uuid:equipment_id>/",
        EquipmentDetailView.as_view(),
        name="equipment-detail",
    ),
    path(
        "gyms/<uuid:gym_id>/equipment/<uuid:equipment_id>/report/",
        ReportMalfunctionView.as_view(),
        name="equipment-report",
    ),
    path(
        "gyms/<uuid:gym_id>/equipment/<uuid:equipment_id>/reports/",
        ManageMaintenanceReportView.as_view(),
        name="maintenance-reports",
    ),
    path(
        "gyms/<uuid:gym_id>/equipment/<uuid:equipment_id>/reports/<uuid:report_id>/",
        ManageMaintenanceReportView.as_view(),
        name="maintenance-report-detail",
    ),

    # Products
    path("gyms/<uuid:gym_id>/products/", ProductListCreateView.as_view(), name="products-list"),
    path(
        "gyms/<uuid:gym_id>/products/<uuid:product_id>/",
        ProductDetailView.as_view(),
        name="product-detail",
    ),

    # Access log
    path("scan/", GymScanView.as_view(), name="gym-scan"),
]
