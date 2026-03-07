import uuid
from django.db import models


class MembershipPlan(models.Model):
    """
    Template defining the terms of a subscription offered by a gym.

    type          → ENUM(monthly, annual, session_pack, trial)
    session_limit → NULL for monthly/annual/trial (unlimited)
                    required integer > 0 for session_pack
    auto_renew    → plan auto-renews on expiry
    is_active     → soft-delete; hides from new subscribers,
                    preserves existing Subscription FK rows
    """

    PLAN_TYPE_CHOICES = [
        ("monthly", "Monthly"),
        ("annual", "Annual"),
        ("session_pack", "Session Pack"),
        ("trial", "Trial"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(
        "membersandsubscriptions.Gym",
        on_delete=models.CASCADE,
        related_name="membership_plans",
    )
    name = models.CharField(max_length=120)
    type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="DZD")
    duration_days = models.IntegerField()
    session_limit = models.IntegerField(null=True, blank=True)
    auto_renew = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["gym", "is_active"]),
            models.Index(fields=["gym", "type"]),
        ]

    def __str__(self):
        return f"{self.name} [{self.type}] @ {self.gym}"