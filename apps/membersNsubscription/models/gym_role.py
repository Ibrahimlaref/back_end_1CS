import uuid
from django.db import models
from django.conf import settings


class UserGymRole(models.Model):


    ROLE_CHOICES = [
        ("member", "Member"),
        ("coach", "Coach"),
        ("admin", "Admin"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("suspended", "Suspended"),
        ("inactive", "Inactive"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    gym = models.ForeignKey(
        "membersNsubscription.Gym",
        on_delete=models.CASCADE,
        related_name="member_user_roles",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="members_gym_roles",
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="member")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")

    joined_at = models.DateTimeField(auto_now_add=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("gym", "user")]
        indexes = [
            models.Index(fields=["gym", "status"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.user} @ {self.gym} [{self.role} / {self.status}]"

    @property
    def is_active(self):
        return self.status == "active"
