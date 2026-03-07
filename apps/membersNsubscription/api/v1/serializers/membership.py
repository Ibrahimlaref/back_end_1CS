from rest_framework import serializers
from apps.membersNsubscription.models.gym_role import UserGymRole
from apps.membersNsubscription.models.member_profile import MemberProfile


class JoinGymSerializer(serializers.Serializer):
  

    height_cm = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    weight_kg = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    fitness_goal = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    medical_notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    emergency_contact = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class UserGymRoleSerializer(serializers.ModelSerializer):
    gym_name = serializers.CharField(source="gym.name", read_only=True)
    gym_slug = serializers.CharField(source="gym.slug", read_only=True)

    class Meta:
        model = UserGymRole
        fields = [
            "id",
            "gym",
            "gym_name",
            "gym_slug",
            "role",
            "status",
            "joined_at",
            "deactivated_at",
        ]
        read_only_fields = fields


class MemberProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberProfile
        fields = [
            "id",
            "gym",
            "user",
            "height_cm",
            "weight_kg",
            "fitness_goal",
            "medical_notes",
            "emergency_contact",
            "warning_count",
            "suspended_until",
            "created_at",
        ]
        # warning_count and suspended_until are DB-managed — never writable via API
        read_only_fields = [
            "id", "gym", "user",
            "warning_count", "suspended_until",
            "created_at",
        ]