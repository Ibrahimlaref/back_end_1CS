from rest_framework import serializers
from apps.users.models.user import CoachApplication


class CoachApplicationSubmitSerializer(serializers.Serializer):
    """Validates the cover letter on application submission."""
    cover_letter = serializers.CharField(required=False, allow_blank=True, default='')


class CoachApplicationResponseSerializer(serializers.ModelSerializer):
    """Read-only representation returned after create or withdraw."""

    class Meta:
        model  = CoachApplication
        fields = ['id', 'gym', 'user', 'status', 'cover_letter', 'created_at']
        read_only_fields = fields