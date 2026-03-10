from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from celery import shared_task

from apps.core.tasks import CorrelatedTask
from apps.core.models import SystemLog
from apps.users.services.session_cleanup_service import SessionCleanupService


@shared_task(
    bind=True,
    base=CorrelatedTask,
    max_retries=3,
    name='apps.users.tasks.send_email_task',
    queue='notifications',
)
def send_email_task(self, to_email, subject, message):
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
    except Exception as exc:
        countdown = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(
    bind=True,
    base=CorrelatedTask,
    max_retries=3,
    name='apps.users.tasks.cleanup_session_logs',
    queue='scheduled',
)
def cleanup_session_logs(self):
    started_at = timezone.now()
    service = SessionCleanupService()
    task_id = getattr(self.request, "id", None)

    try:
        result = service.purge_expired_sessions()
        completed_at = timezone.now()
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        SystemLog.objects.create(
            event=SessionCleanupService.EVENT_NAME,
            level=SystemLog.Level.INFO,
            message="Session cleanup completed.",
            metadata={
                "task_id": task_id,
                "deleted_count": result["deleted_count"],
                "revoked_cutoff": result["revoked_cutoff"].isoformat(),
                "stale_cutoff": result["stale_cutoff"].isoformat(),
                "batch_size": result["batch_size"],
                "duration_ms": duration_ms,
            },
        )
        return result
    except Exception as exc:
        failed_at = timezone.now()
        duration_ms = int((failed_at - started_at).total_seconds() * 1000)

        SystemLog.objects.create(
            event=SessionCleanupService.EVENT_NAME,
            level=SystemLog.Level.ERROR,
            message="Session cleanup failed.",
            metadata={
                "task_id": task_id,
                "error": str(exc),
                "duration_ms": duration_ms,
            },
        )

        retries = getattr(self.request, "retries", 0)
        countdown = 60 * (2 ** retries)
        raise self.retry(exc=exc, countdown=countdown)
