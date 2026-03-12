import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone

from apps.gyms.models import Gym


# ─── PLATFORM LEVEL ───────────────────────────────────────────────────────────

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email           = models.EmailField(unique=True)
    first_name      = models.TextField(blank=True)
    last_name       = models.TextField(blank=True)
    phone           = models.TextField(blank=True)
    date_of_birth   = models.DateField(null=True, blank=True)
    photo_url       = models.TextField(blank=True)
    is_active       = models.BooleanField(default=True)
    is_staff        = models.BooleanField(default=False)
    email_verified  = models.BooleanField(default=False)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    # ─── 2FA FIELDS ───────────────────────────────────────────────────────────
    totp_secret     = models.TextField(blank=True)   # TOTP secret key (base32)
    totp_enabled    = models.BooleanField(default=False)  # is 2FA active?

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email


# ─── MEMBERSHIP & ROLES ───────────────────────────────────────────────────────

class UserGymRole(models.Model):
    class Role(models.TextChoices):
        MEMBER = "member", "Member"
        COACH  = "coach",  "Coach"
        ADMIN  = "admin",  "Admin"

    class Status(models.TextChoices):
        ACTIVE    = "active",    "Active"
        SUSPENDED = "suspended", "Suspended"
        INACTIVE  = "inactive",  "Inactive"

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym            = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="user_roles")
    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name="gym_roles")
    role           = models.CharField(max_length=20, choices=Role.choices)
    status         = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    joined_at      = models.DateTimeField(auto_now_add=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table      = "user_gym_roles"
        unique_together = [("gym", "user", "role")]

    def __str__(self):
        return f"{self.user} @ {self.gym} ({self.role})"


class MemberProfile(models.Model):
    id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym               = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="member_profiles")
    user              = models.ForeignKey(User, on_delete=models.CASCADE, related_name="member_profiles")
    height_cm         = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    weight_kg         = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    fitness_goal      = models.TextField(blank=True)
    medical_notes     = models.TextField(blank=True)
    emergency_contact = models.TextField(blank=True)
    warning_count     = models.SmallIntegerField(default=0)
    suspended_until   = models.DateTimeField(null=True, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table        = "member_profiles"
        unique_together = [("gym", "user")]

    def __str__(self):
        return f"MemberProfile: {self.user} @ {self.gym}"


class CoachProfile(models.Model):
    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym              = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="coach_profiles")
    user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name="coach_profiles")
    specialties      = ArrayField(models.TextField(), default=list, blank=True)
    biography        = models.TextField(blank=True)
    experience_years = models.SmallIntegerField(null=True, blank=True)
    is_active        = models.BooleanField(default=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table        = "coach_profiles"
        unique_together = [("gym", "user")]

    def __str__(self):
        return f"CoachProfile: {self.user} @ {self.gym}"


class CoachApplication(models.Model):
    class Status(models.TextChoices):
        PENDING   = "pending",   "Pending"
        ACCEPTED  = "accepted",  "Accepted"
        REJECTED  = "rejected",  "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym           = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="coach_applications")
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name="coach_applications")
    status        = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    cover_letter  = models.TextField(blank=True)
    reviewed_by   = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_applications"
    )
    reviewed_at    = models.DateTimeField(null=True, blank=True)
    rejection_note = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "coach_applications"

    def __str__(self):
        return f"CoachApplication: {self.user} @ {self.gym} ({self.status})"


class SessionLog(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="session_logs")
    gym          = models.ForeignKey(Gym, null=True, blank=True, on_delete=models.SET_NULL, related_name="session_logs")
    ip_address   = models.GenericIPAddressField(null=True, blank=True)
    user_agent   = models.TextField(blank=True)
    device_type  = models.TextField(blank=True)
    logged_in_at = models.DateTimeField(auto_now_add=True)
    logged_out_at= models.DateTimeField(null=True, blank=True)
    jwt_jti      = models.TextField(blank=True, db_index=True)
    is_revoked   = models.BooleanField(default=False)

    class Meta:
        db_table = "session_logs"
        indexes = [
            models.Index(fields=["user", "is_revoked"], name="sessionlog_user_revoked_idx"),
        ]


class Warning(models.Model):
    class Type(models.TextChoices):
        NO_SHOW    = "no_show",    "No Show"
        MISCONDUCT = "misconduct", "Misconduct"
        PAYMENT    = "payment",    "Payment"
        OTHER      = "other",      "Other"

    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym       = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="warnings")
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name="warnings")
    issued_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="issued_warnings")
    reason    = models.TextField()
    type      = models.CharField(max_length=20, choices=Type.choices)
    created_at= models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "warnings"

    def __str__(self):
        return f"Warning: {self.user} ({self.type})"
