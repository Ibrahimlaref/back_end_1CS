import uuid
from django.db import models
from django.utils import timezone

from apps.users.models.user import User
from apps.core.models.gym import Gym
from django.contrib.postgres.fields import ArrayField

# ─── NOTIFICATION TYPES & CHANNELS ───────────────────────────────────────────

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

    def __str__(self):
        return f"{self.title} → {self.user}"


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

    def __str__(self):
        return f"Preference: {self.user} → {self.notif_type} ({self.channel})"


class NotificationLog(models.Model):
    class Channel(models.TextChoices):
        IN_APP = "in_app", "In-App"
        EMAIL = "email", "Email"
        PUSH = "push", "Push"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        OPENED = "opened", "Opened"
        FAILED = "failed", "Failed"
        BOUNCED = "bounced", "Bounced"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name="logs")
    channel = models.CharField(max_length=10, choices=Channel.choices)
    status = models.CharField(max_length=10, choices=Status.choices)
    provider_id = models.TextField(blank=True)  # Optional external ID from email/push provider
    attempted_at = models.DateTimeField(default=timezone.now)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notification_logs"

    def __str__(self):
        return f"{self.notification} → {self.channel} ({self.status})"
    

class UserDevice(models.Model):
    class Platform(models.TextChoices):
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"
        WEB = "web", "Web"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="devices")
    token = models.TextField(unique=True)
    platform = models.CharField(max_length=10, choices=Platform.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_devices"