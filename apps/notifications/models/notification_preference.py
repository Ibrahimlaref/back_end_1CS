import uuid

from django.db import models

from apps.core.models.gym import Gym
from apps.users.models.user import User


class NotificationPreference(models.Model):
    class Channel(models.TextChoices):
        IN_APP = "in_app", "In-App"
        EMAIL = "email", "Email"
        PUSH = "push", "Push"

    class Type(models.TextChoices):
        COURSE_REMINDER = "course_reminder", "Course Reminder"
        MARKETING = "marketing", "Marketing"
        SYSTEM = "system", "System"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="notification_preferences")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notification_preferences")
    notif_type = models.CharField(max_length=30, choices=Type.choices)
    channel = models.CharField(max_length=10, choices=Channel.choices)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        db_table = "notification_preferences"
        unique_together = [("gym", "user", "notif_type", "channel")]

    def __str__(self) -> str:
        return f"Preference: {self.user} -> {self.notif_type} ({self.channel})"
