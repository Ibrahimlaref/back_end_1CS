from rest_framework import serializers
from apps.membersNsubscription.models.equipment import Equipment, MaintenanceReport


class EquipmentSerializer(serializers.ModelSerializer):
    """status is read-only — set by report workflow, not direct PATCH."""

    class Meta:
        model = Equipment
        fields = ["id", "gym", "name", "serial_number", "status",
                  "purchased_at", "last_maintenance", "created_at"]
        read_only_fields = ["id", "gym", "status", "last_maintenance", "created_at"]


class EquipmentAdminSerializer(serializers.ModelSerializer):
    """Admin serializer — allows setting status directly (e.g. decommission)."""

    class Meta:
        model = Equipment
        fields = ["id", "gym", "name", "serial_number", "status",
                  "purchased_at", "last_maintenance", "created_at"]
        read_only_fields = ["id", "gym", "last_maintenance", "created_at"]

    def validate_status(self, value):
        if value not in ["decommissioned", "operational", "maintenance_needed"]:
            raise serializers.ValidationError(
                f"Cannot manually set status to '{value}'. Use the maintenance report workflow."
            )
        return value


class MaintenanceReportSerializer(serializers.ModelSerializer):
    reported_by_name = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    equipment_name = serializers.CharField(source="equipment.name", read_only=True)

    class Meta:
        model = MaintenanceReport
        fields = [
            "id", "gym", "equipment", "equipment_name",
            "reported_by", "reported_by_name",
            "assigned_to", "assigned_to_name",
            "description", "status", "resolved_at", "created_at",
        ]
        read_only_fields = ["id", "gym", "equipment", "reported_by",
                            "status", "resolved_at", "created_at"]

    def get_reported_by_name(self, obj):
        if obj.reported_by:
            return f"{obj.reported_by.first_name} {obj.reported_by.last_name}".strip()
        return None

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip()
        return None


class ReportMalfunctionSerializer(serializers.Serializer):
    """Input for US-073: file a malfunction report."""
    description = serializers.CharField(min_length=10, max_length=2000)


class UpdateReportSerializer(serializers.Serializer):
    """
    Input for US-074: advance report status.
    resolution_notes is required when new_status='resolved'.
    """
    new_status = serializers.ChoiceField(choices=["acknowledged", "in_progress", "resolved"])
    assigned_to_id = serializers.UUIDField(required=False, allow_null=True)
    resolution_notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs.get("new_status") == "resolved":
            if not attrs.get("resolution_notes", "").strip():
                raise serializers.ValidationError(
                    {"resolution_notes": "resolution_notes is required when resolving a report."}
                )
        return attrs