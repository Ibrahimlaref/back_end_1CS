import uuid
from django.db import models
from django.conf import settings


class MemberProfile(models.Model):
  

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    gym = models.ForeignKey(
        "membersandsubscriptions.Gym",
        on_delete=models.CASCADE,
        related_name="member_profiles",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="member_profiles",
    )

    # Health fields — all optional on join, updateable via US-027
    height_cm = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    weight_kg = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    fitness_goal = models.TextField(blank=True, default="")
    medical_notes = models.TextField(blank=True, default="")
    emergency_contact = models.TextField(blank=True, default="")

    # Managed by DB triggers — READ ONLY via API
    warning_count = models.SmallIntegerField(default=0)
    suspended_until = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("gym", "user")]
        indexes = [
            models.Index(fields=["gym", "user"]),
        ]

    def __str__(self):
        return f"MemberProfile: {self.user} @ {self.gym}"