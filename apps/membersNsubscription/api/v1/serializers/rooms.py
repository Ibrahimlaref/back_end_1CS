from rest_framework import serializers
from apps.membersNsubscription.models import Room


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["id", "gym", "name", "capacity", "is_active"]
        read_only_fields = ["id", "gym"]

    def validate_capacity(self, value):
        if value < 1:
            raise serializers.ValidationError("Room capacity must be at least 1.")
        return value

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Room name cannot be blank.")
        return value.strip()
