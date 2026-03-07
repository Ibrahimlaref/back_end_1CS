import uuid
from django.db import models
from django.conf import settings


class Equipment(models.Model):
    """
    Physical equipment owned by a gym.

    Status transitions driven by report workflow:
      operational → under_maintenance   (US-073: file report)
      under_maintenance → operational   (US-074: resolve report)
      any → decommissioned              (US-072: admin soft-delete)

    UNIQUE(gym_id, serial_number) at DB level.
    last_maintenance updated to now() on report resolution (US-074).
    """

    STATUS_CHOICES = [
        ("operational", "Operational"),
        ("maintenance_needed", "Maintenance Needed"),
        ("under_maintenance", "Under Maintenance"),
        ("decommissioned", "Decommissioned"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(
        "gyms.Gym",
        on_delete=models.CASCADE,
        related_name="equipment",
    )
    name = models.CharField(max_length=120)
    serial_number = models.CharField(max_length=100)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default="operational")
    purchased_at = models.DateField(null=True, blank=True)
    last_maintenance = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("gym", "serial_number")]
        indexes = [
            models.Index(fields=["gym", "status"]),
        ]

    def __str__(self):
        return f"{self.name} [{self.serial_number}] ({self.status}) @ {self.gym}"


class MaintenanceReport(models.Model):
    """
    Report filed when equipment needs attention.

    Status flow (forward only, enforced in view):
      open → acknowledged → in_progress → resolved

    Rules:
      - One active report per equipment at a time (duplicate guard US-073).
      - Filing → equipment.status = 'under_maintenance' (atomic).
      - Resolving → equipment.status = 'operational' +
        equipment.last_maintenance = now() (atomic).
    """

    STATUS_CHOICES = [
        ("open", "Open"),
        ("acknowledged", "Acknowledged"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(
       "membersandsubscriptions.Gym",
        on_delete=models.CASCADE,
        related_name="maintenance_reports",
    )
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name="maintenance_reports",
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="maintenance_reports_filed",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_reports_assigned",
    )
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["equipment", "status"]),
            models.Index(fields=["gym", "status"]),
        ]

    def __str__(self):
        return f"Report #{self.id} on {self.equipment} [{self.status}]"