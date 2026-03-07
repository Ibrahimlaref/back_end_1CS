import uuid
from django.db import models
from django.conf import settings


class Gym(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.TextField()
    slug       = models.SlugField(unique=True)
    address    = models.TextField(blank=True)
    city       = models.TextField(blank=True)
    country    = models.CharField(max_length=3, blank=True)
    phone      = models.TextField(blank=True)
    email      = models.EmailField(blank=True)
    logo_url   = models.TextField(blank=True)
    timezone   = models.TextField(default="UTC")
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ─── 2FA POLICY ───────────────────────────────────────────────────────────
    require_2fa = models.BooleanField(
        default=False,
        help_text="Force all staff (coaches and admins) to enable 2FA."
    )

    class Meta:
        db_table = "gyms"

    def __str__(self):
        return self.name


class PlatformOwnership(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="platform_ownerships")
    gym        = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="platform_ownerships")
    role       = models.TextField()
    granted_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "platform_ownerships"

    def __str__(self):
        return f"{self.user} → {self.gym} ({self.role})"


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"
        LOGIN  = "LOGIN",  "Login"
        LOGOUT = "LOGOUT", "Logout"

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym          = models.ForeignKey(Gym, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    actor        = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_actions")
    target_id    = models.UUIDField(null=True, blank=True)
    target_table = models.TextField(blank=True)
    action       = models.CharField(max_length=10, choices=Action.choices)
    old_values   = models.JSONField(null=True, blank=True)
    new_values   = models.JSONField(null=True, blank=True)
    ip_address   = models.GenericIPAddressField(null=True, blank=True)
    user_agent   = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"


class AccessLog(models.Model):
    class EntryType(models.TextChoices):
        ENTRY = "entry", "Entry"
        EXIT  = "exit",  "Exit"

    class Method(models.TextChoices):
        NFC    = "nfc",    "NFC"
        QR     = "qr",     "QR"
        MANUAL = "manual", "Manual"

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym         = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="access_logs")
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="access_logs")
    entry_type  = models.CharField(max_length=10, choices=EntryType.choices)
    method      = models.CharField(max_length=10, choices=Method.choices)
    device_id   = models.TextField(blank=True)
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "access_logs"


class ErrorLog(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym         = models.ForeignKey(Gym, null=True, blank=True, on_delete=models.SET_NULL, related_name="error_logs")
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="error_logs")
    error_code  = models.TextField(blank=True)
    message     = models.TextField()
    stack_trace = models.TextField(blank=True)
    endpoint    = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "error_logs"