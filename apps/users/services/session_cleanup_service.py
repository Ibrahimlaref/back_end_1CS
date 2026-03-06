from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.users.models.user import SessionLog


class SessionCleanupService:
    EVENT_NAME = "session_log_cleanup"
    REVOKED_RETENTION_DAYS = 30
    STALE_RETENTION_DAYS = 90
    DEFAULT_BATCH_SIZE = 5000

    def purge_expired_sessions(self, now=None, batch_size=None):
        now = now or timezone.now()
        batch_size = batch_size or self.DEFAULT_BATCH_SIZE

        revoked_cutoff = now - timedelta(days=self.REVOKED_RETENTION_DAYS)
        stale_cutoff = now - timedelta(days=self.STALE_RETENTION_DAYS)

        active_filter = Q(is_revoked=False, logged_out_at__isnull=True)
        purge_filter = Q(is_revoked=True, logged_out_at__lt=revoked_cutoff) | Q(logged_in_at__lt=stale_cutoff)

        candidate_queryset = SessionLog.objects.filter(purge_filter).exclude(active_filter).order_by("id")

        total_deleted = 0
        while True:
            batch_ids = list(candidate_queryset.values_list("id", flat=True)[:batch_size])
            if not batch_ids:
                break
            deleted_count, _ = SessionLog.objects.filter(id__in=batch_ids).delete()
            total_deleted += deleted_count

        return {
            "deleted_count": total_deleted,
            "revoked_cutoff": revoked_cutoff,
            "stale_cutoff": stale_cutoff,
            "batch_size": batch_size,
        }
