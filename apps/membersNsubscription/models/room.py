import uuid
from django.db import models


class Room(models.Model):
    """
    A physical room inside a gym (e.g. Yoga Studio, Cardio Floor).

    capacity  → SMALLINT; ConflictService (US-045) ensures course
                max_participants never exceeds this value
    is_active → soft-delete; prevents new course assignments
                but preserves existing Course FK rows

    UNIQUE(gym_id, name) at DB level.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(
        "membersandsubscriptions.Gym",
        on_delete=models.CASCADE,
        related_name="rooms",
    )
    name = models.CharField(max_length=120)
    capacity = models.SmallIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("gym", "name")]
        indexes = [
            models.Index(fields=["gym", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} (cap:{self.capacity}) @ {self.gym}"