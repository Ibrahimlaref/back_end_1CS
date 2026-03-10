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
    operation = models.CharField(max_length=64, blank=True, default="", db_index=True)
    detail = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    performed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "system_logs"

    def save(self, *args, **kwargs):
        if not self.operation and self.event:
            self.operation = self.event
        if not self.event and self.operation:
            self.event = self.operation
        if not self.detail and self.message:
            self.detail = self.message
        if not self.message and self.detail:
            self.message = self.detail
        super().save(*args, **kwargs)
