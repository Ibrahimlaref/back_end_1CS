import uuid

from django.db import models


class SystemLog(models.Model):
    class Level(models.TextChoices):
        INFO = "INFO", "Info"
        ERROR = "ERROR", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.CharField(max_length=64, db_index=True)
    level = models.CharField(max_length=10, choices=Level.choices, db_index=True)
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "system_logs"
