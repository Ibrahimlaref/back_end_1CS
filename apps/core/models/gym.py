import uuid

from django.conf import settings
from django.db import models


class Gym(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField()
    slug = models.SlugField(unique=True)
    address = models.TextField(blank=True)
    city = models.TextField(blank=True)
    country = models.CharField(max_length=3, blank=True)
    phone = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    logo_url = models.TextField(blank=True)
    timezone = models.TextField(default="UTC")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gyms"

    def __str__(self):
        return self.name


class PlatformOwnership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="platform_ownerships",
    )
    gym = models.ForeignKey(
        Gym,
        on_delete=models.CASCADE,
        related_name="platform_ownerships",
    )
    role = models.TextField()
    granted_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "platform_ownerships"

    def __str__(self):
        return f"{self.user} -> {self.gym} ({self.role})"


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"
        LOGIN = "LOGIN", "Login"
        LOGOUT = "LOGOUT", "Logout"

    retention_exempt = True

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(
        Gym,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_actions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="compliance_audit_logs",
    )
    target_id = models.UUIDField(null=True, blank=True)
    target_table = models.TextField(blank=True)
    action = models.CharField(max_length=10, choices=Action.choices)
    data = models.JSONField(null=True, blank=True)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"

    def save(self, *args, **kwargs):
        if self.user_id is None and self.actor_id is not None:
            self.user_id = self.actor_id
        if self.data is None:
            self.data = {
                "target_id": str(self.target_id) if self.target_id else None,
                "target_table": self.target_table,
                "old_values": self.old_values,
                "new_values": self.new_values,
                "ip_address": self.ip_address,
                "user_agent": self.user_agent,
            }
        super().save(*args, **kwargs)


class AccessLog(models.Model):
    class EntryType(models.TextChoices):
        ENTRY = "entry", "Entry"
        EXIT = "exit", "Exit"

    class Method(models.TextChoices):
        NFC = "nfc", "NFC"
        QR = "qr", "QR"
        MANUAL = "manual", "Manual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="access_logs")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="access_logs",
    )
    ip = models.GenericIPAddressField(null=True, blank=True)
    path = models.CharField(max_length=255, blank=True)
    entry_type = models.CharField(max_length=10, choices=EntryType.choices)
    method = models.CharField(max_length=10, choices=Method.choices)
    device_id = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "access_logs"


class ErrorLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(
        Gym,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="error_logs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="error_logs",
    )
    level = models.CharField(max_length=16, default="ERROR", db_index=True)
    error_code = models.TextField(blank=True)
    message = models.TextField()
    traceback = models.TextField(blank=True)
    stack_trace = models.TextField(blank=True)
    endpoint = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "error_logs"

    def save(self, *args, **kwargs):
        if not self.traceback and self.stack_trace:
            self.traceback = self.stack_trace
        if not self.stack_trace and self.traceback:
            self.stack_trace = self.traceback
        super().save(*args, **kwargs)
