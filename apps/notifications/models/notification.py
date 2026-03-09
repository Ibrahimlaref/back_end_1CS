import uuid

from django.db import models

from apps.core.models.gym import Gym
from apps.users.models.user import User


class Notification(models.Model):
    class Type(models.TextChoices):
        COURSE_REMINDER = "course_reminder", "Course Reminder"
        SUBSCRIPTION_RENEWAL = "subscription_renewal", "Subscription Renewal"
        WARNING_ISSUED = "warning_issued", "Warning Issued"
        PROMOTION = "promotion", "Promotion"
        GENERAL = "general", "General"
        RECOMMENDATION = "recommendation", "Recommendation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="notifications")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=30, choices=Type.choices)
    title = models.TextField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"

    @property
    def notification_type(self) -> str:
        return self.type

    def __str__(self) -> str:
        return f"{self.title} -> {self.user}"
