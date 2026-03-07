from rest_framework import serializers
from apps.membersNsubscription.models.membership_plan import MembershipPlan


class MembershipPlanSerializer(serializers.ModelSerializer):
    """
    Cross-field rules:
    - session_pack → session_limit required and > 0
    - monthly/annual/trial → session_limit must be null
    - duration_days >= 1  |  price >= 0  |  currency = 3-char ISO
    """
    from rest_framework import serializers
from apps.membersNsubscription.models.membership_plan import MembershipPlan


# ── Read serializer ───────────────────────────────────────────────────────────

class MembershipPlanReadSerializer(serializers.ModelSerializer):
    """
    Output serializer — includes computed helpers is_session_based / is_unlimited
    so the frontend never has to re-derive them.
    """
    gym_name = serializers.CharField(source="gym.name", read_only=True)
    is_session_based = serializers.BooleanField(read_only=True)
    is_unlimited = serializers.BooleanField(read_only=True)

    class Meta:
        model = MembershipPlan
        fields = [
            "id",
            "gym",
            "gym_name",
            "name",
            "type",
            "price",
            "currency",
            "duration_days",
            "session_limit",
            "auto_renew",
            "is_active",
            "is_session_based",
            "is_unlimited",
        ]
        read_only_fields = fields


# ── Write serializer ──────────────────────────────────────────────────────────

class MembershipPlanWriteSerializer(serializers.ModelSerializer):
    """
    Input serializer for POST (create) and PATCH (partial update).

    Validation rules
    ────────────────
    price         : >= 0 (free trials allowed)
    duration_days : >= 1
    currency      : exactly 3 chars, uppercased automatically

    Cross-field (validate)
    ──────────────────────
    session_pack  → session_limit must be a positive integer
    monthly /
    annual /
    trial         → session_limit must be null / omitted

    PATCH safety
    ────────────
    On partial update, if only `session_limit` is sent without `type`,
    the existing instance type is used for cross-field validation.
    """

    class Meta:
        model = MembershipPlan
        fields = [
            "name",
            "type",
            "price",
            "currency",
            "duration_days",
            "session_limit",
            "auto_renew",
            "is_active",
        ]

    # ── field-level validators ────────────────────────────────────────────

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

    def validate_duration_days(self, value):
        if value < 1:
            raise serializers.ValidationError("duration_days must be at least 1.")
        return value

    def validate_currency(self, value):
        value = value.strip().upper()
        if len(value) != 3:
            raise serializers.ValidationError(
                "currency must be a 3-character ISO 4217 code (e.g. DZD, USD, EUR)."
            )
        return value

    # ── cross-field validator ─────────────────────────────────────────────

    def validate(self, attrs):
        # On PATCH, fall back to the existing instance value when a field
        # is not present in the incoming payload.
        plan_type = attrs.get("type") or getattr(self.instance, "type", None)
        session_limit = attrs.get(
            "session_limit",
            getattr(self.instance, "session_limit", None),
        )

        if plan_type is None:
            raise serializers.ValidationError({"type": "This field is required."})

        if plan_type == "session_pack":
            if session_limit is None or session_limit < 1:
                raise serializers.ValidationError({
                    "session_limit": (
                        "session_limit must be a positive integer for session_pack plans."
                    )
                })
        else:
            if session_limit is not None:
                raise serializers.ValidationError({
                    "session_limit": (
                        f"session_limit must be null for '{plan_type}' plans. "
                        f"Only session_pack plans use a session counter."
                    )
                })

        return attrs

    def to_representation(self, instance):
        """
        After create/update, return the full read representation
        so the caller gets gym_name + computed booleans in the response.
        """
        return MembershipPlanReadSerializer(instance, context=self.context).data

    class Meta:
        model = MembershipPlan
        fields = ["id", "gym", "name", "type", "price", "currency",
                  "duration_days", "session_limit", "auto_renew", "is_active"]
        read_only_fields = ["id", "gym"]

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

    def validate_duration_days(self, value):
        if value < 1:
            raise serializers.ValidationError("Duration must be at least 1 day.")
        return value

    def validate_currency(self, value):
        if len(value) != 3:
            raise serializers.ValidationError("Currency must be a 3-character ISO code (e.g. DZD, USD, EUR).")
        return value.upper()

    def validate(self, attrs):
        plan_type = attrs.get("type") or getattr(self.instance, "type", None)
        session_limit = attrs.get("session_limit", getattr(self.instance, "session_limit", None))

        if plan_type == "session_pack":
            if not session_limit or session_limit < 1:
                raise serializers.ValidationError(
                    {"session_limit": "session_limit must be a positive integer for session_pack plans."}
                )
        else:
            if session_limit is not None:
                raise serializers.ValidationError(
                    {"session_limit": f"session_limit must be null for '{plan_type}' plans."}
                )
        return attrs