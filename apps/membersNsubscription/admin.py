from django.contrib import admin

from apps.membersNsubscription.models.gym_role import UserGymRole
from apps.membersNsubscription.models.member_profile import MemberProfile
from apps.membersNsubscription.models.membership_plan import MembershipPlan
from apps.membersNsubscription.models.room import Room
from apps.membersNsubscription.models.equipment import Equipment, MaintenanceReport
from apps.membersNsubscription.models.product import Product


@admin.register(UserGymRole)
class UserGymRoleAdmin(admin.ModelAdmin):
    list_display = ["user", "gym", "role", "status", "joined_at"]
    list_filter = ["role", "status", "gym"]
    search_fields = ["user__email", "gym__name"]


@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "gym", "warning_count", "suspended_until", "created_at"]
    list_filter = ["gym"]
    search_fields = ["user__email", "gym__name"]
    readonly_fields = ["warning_count", "suspended_until"]


@admin.register(MembershipPlan)
class MembershipPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "gym", "type", "price", "currency", "duration_days", "is_active"]
    list_filter = ["type", "is_active", "auto_renew"]
    search_fields = ["name", "gym__name"]


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["name", "gym", "capacity", "is_active"]
    list_filter = ["is_active", "gym"]
    search_fields = ["name", "gym__name"]


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ["name", "serial_number", "gym", "status", "purchased_at", "last_maintenance"]
    list_filter = ["status", "gym"]
    search_fields = ["name", "serial_number", "gym__name"]


@admin.register(MaintenanceReport)
class MaintenanceReportAdmin(admin.ModelAdmin):
    list_display = ["id", "equipment", "gym", "status", "reported_by", "assigned_to", "created_at"]
    list_filter = ["status", "gym"]
    search_fields = ["equipment__name", "description"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "gym", "price", "stock_quantity", "is_active", "created_at"]
    list_filter = ["is_active", "gym"]
    search_fields = ["name", "gym__name"]