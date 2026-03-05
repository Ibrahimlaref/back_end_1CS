import re
from rest_framework import serializers
from gyms.models.gym import Gym, PlatformOwnership, AuditLog, AccessLog, ErrorLog


# ────────────────────────────────────────────────
# Shared slug validator  (AC-2)
# ────────────────────────────────────────────────
SLUG_RE = re.compile(r'^[a-z0-9-]+$')


def validate_slug_format(value: str) -> str:
    """Enforce lowercase ^[a-z0-9-]+$ — reusable across serializers."""
    if not SLUG_RE.match(value):
        raise serializers.ValidationError(
            "Slug must be lowercase and contain only letters, numbers, and hyphens."
        )
    return value


# ────────────────────────────────────────────────
# US-002  POST /platform/gyms
# ────────────────────────────────────────────────

class GymProvisionSerializer(serializers.ModelSerializer):
    """
    Input serializer for gym provisioning.
    Validates slug format + uniqueness (AC-2).
    Service layer handles atomic creation + RLS (AC-1, AC-3).
    """

    class Meta:
        model  = Gym
        fields = [
            "name",
            "slug",
            "address",
            "city",
            "country",
            "phone",
            "email",
            "logo_url",
            "timezone",
        ]
        extra_kwargs = {
            "name":     {"required": True},
            "slug":     {"required": True},
            # all others optional — already blank=True on the model
        }

    def validate_slug(self, value: str) -> str:
        # format check
        value = validate_slug_format(value)
        # uniqueness check (AC-2)
        if Gym.objects.filter(slug=value).exists():
            raise serializers.ValidationError("A gym with this slug already exists.")
        return value


class GymProvisionResponseSerializer(serializers.ModelSerializer):
    """
    Output serializer for 201 response (AC-6).
    Returns gym_id + slug so the caller can construct tenant URLs.
    """

    gym_id = serializers.UUIDField(source="id")

    class Meta:
        model  = Gym
        fields = ["gym_id", "slug", "name", "created_at"]
        read_only_fields = fields


# ────────────────────────────────────────────────
# PlatformOwnership
# ────────────────────────────────────────────────

class PlatformOwnershipSerializer(serializers.ModelSerializer):
    """
    Read serializer — returned nested inside gym detail responses.
    Write operations go through the service layer, not this serializer.
    """

    user_id = serializers.UUIDField(source="user.id", read_only=True)
    gym_id  = serializers.UUIDField(source="gym.id",  read_only=True)

    class Meta:
        model  = PlatformOwnership
        fields = [
            "id",
            "user_id",
            "gym_id",
            "role",
            "granted_at",
            "revoked_at",
        ]
        read_only_fields = fields


# ────────────────────────────────────────────────
# AuditLog
# ────────────────────────────────────────────────

class AuditLogSerializer(serializers.ModelSerializer):
    """
    Read-only. Written by the service layer, never via API input.
    """

    actor_id = serializers.UUIDField(source="actor.id", read_only=True, allow_null=True)
    gym_id   = serializers.UUIDField(source="gym.id",   read_only=True, allow_null=True)

    class Meta:
        model  = AuditLog
        fields = [
            "id",
            "gym_id",
            "actor_id",
            "target_id",
            "target_table",
            "action",
            "old_values",
            "new_values",
            "ip_address",
            "user_agent",
            "created_at",
        ]
        read_only_fields = fields


# ────────────────────────────────────────────────
# AccessLog  (future-ready)
# ────────────────────────────────────────────────

class AccessLogSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    gym_id  = serializers.UUIDField(source="gym.id",  read_only=True)

    class Meta:
        model  = AccessLog
        fields = [
            "id",
            "gym_id",
            "user_id",
            "entry_type",
            "method",
            "device_id",
            "accessed_at",
        ]
        read_only_fields = fields


# ────────────────────────────────────────────────
# ErrorLog  (future-ready)
# ────────────────────────────────────────────────

class ErrorLogSerializer(serializers.ModelSerializer):
    gym_id  = serializers.UUIDField(source="gym.id",  read_only=True, allow_null=True)
    user_id = serializers.UUIDField(source="user.id", read_only=True, allow_null=True)

    class Meta:
        model  = ErrorLog
        fields = [
            "id",
            "gym_id",
            "user_id",
            "error_code",
            "message",
            "stack_trace",
            "endpoint",
            "created_at",
        ]
        read_only_fields = fields