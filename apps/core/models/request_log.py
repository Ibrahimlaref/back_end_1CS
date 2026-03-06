import uuid

from django.db import models


class RequestLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    method = models.CharField(max_length=10)
    path = models.TextField()
    status_code = models.PositiveSmallIntegerField()
    duration_ms = models.PositiveIntegerField()
    gym_id = models.UUIDField(null=True, blank=True, db_index=True)
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    is_slow = models.BooleanField(default=False, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "request_logs"
        indexes = [
            models.Index(fields=["status_code", "timestamp"], name="reqlog_status_ts_idx"),
            models.Index(fields=["path", "timestamp"], name="reqlog_path_ts_idx"),
        ]
