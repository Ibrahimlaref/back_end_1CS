import uuid

from django.db import models


class DBSchemaVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    git_sha = models.CharField(max_length=64, db_index=True)
    version_label = models.CharField(max_length=128, blank=True, db_index=True)
    environment = models.CharField(max_length=32, db_index=True)
    migration_heads = models.JSONField(default=dict)
    notes = models.JSONField(default=dict, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "db_schema_versions"
        indexes = [
            models.Index(fields=["environment", "applied_at"], name="db_schema_env_applied_idx"),
        ]
