from rest_framework import serializers


class MembershipStatusSerializer(serializers.Serializer):
    """Request body for deactivate/reactivate."""
    action = serializers.ChoiceField(choices=['deactivate', 'reactivate'])
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class UserGymRoleStatusResponseSerializer(serializers.Serializer):
    """Response after status change."""
    id             = serializers.UUIDField()
    user_id        = serializers.UUIDField()
    gym_id         = serializers.UUIDField()
    role           = serializers.CharField()
    status         = serializers.CharField()
    deactivated_at = serializers.DateTimeField(allow_null=True)
    joined_at      = serializers.DateTimeField()