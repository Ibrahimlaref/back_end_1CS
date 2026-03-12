from rest_framework import serializers
from apps.membersNsubscription.models import MemberProfile


class MemberProfileUpdateSerializer(serializers.Serializer):
    """PATCH serializer — all fields optional, only provided fields are updated."""

    height_cm         = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    weight_kg         = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    fitness_goal      = serializers.CharField(required=False, allow_blank=True)
    medical_notes     = serializers.CharField(required=False, allow_blank=True)
    emergency_contact = serializers.CharField(required=False, allow_blank=True)

    def validate_height_cm(self, value):
        # AC-3: must be positive numeric
        if value is not None and value <= 0:
            raise serializers.ValidationError("Height must be a positive number.")
        return value

    def validate_weight_kg(self, value):
        # AC-3: must be positive numeric
        if value is not None and value <= 0:
            raise serializers.ValidationError("Weight must be a positive number.")
        return value


class MemberProfileResponseSerializer(serializers.ModelSerializer):
    """
    Read serializer returned after update.
    AC-4: medical_notes is included here — the view restricts
    who can see it (only coaches and the member themselves).
    """

    class Meta:
        model  = MemberProfile
        fields = [
            'id',
            'gym',
            'user',
            'height_cm',
            'weight_kg',
            'fitness_goal',
            'medical_notes',    # AC-4: restricted at view level
            'emergency_contact', # AC-5: free-text
            'warning_count',
            'suspended_until',
            'created_at',
        ]
        read_only_fields = fields


class MemberProfilePublicSerializer(serializers.ModelSerializer):
    """
    AC-4: Serializer for non-coach roles — excludes medical_notes.
    Used when role is not 'coach' or 'admin'.
    """

    class Meta:
        model  = MemberProfile
        fields = [
            'id',
            'gym',
            'user',
            'height_cm',
            'weight_kg',
            'fitness_goal',
            'emergency_contact',
            'warning_count',
            'suspended_until',
            'created_at',
        ]
        read_only_fields = fields