import traceback

import redis
from celery import Task, shared_task
from django.conf import settings
from django.utils import timezone

from apps.core.middleware.correlation import (
    clear_observability_context,
    get_correlation_id,
    set_correlation_id,
)
from apps.core.models import AuditLog, ErrorLog
from apps.core.services import (
    apply_data_retention_policy,
    build_retention_preview,
    send_retention_preview_email,
)

_redis = redis.from_url(settings.REDIS_URL)
ACCESS_LOG_RETENTION_DAYS = 730
ERROR_LOG_RETENTION_DAYS = 90
USER_ANONYMISATION_GRACE_DAYS = 30


def apply_async_with_correlation(task, *, args=None, kwargs=None, **options):
    headers = dict(options.pop('headers', {}) or {})
    correlation_id = get_correlation_id()
    if correlation_id:
        headers.setdefault('correlation_id', correlation_id)

    task_kwargs = {**options}
    if args is not None:
        task_kwargs['args'] = list(args)
    if kwargs:
        task_kwargs['kwargs'] = kwargs
    if headers:
        task_kwargs['headers'] = headers
    return task.apply_async(**task_kwargs)


class CorrelatedTask(Task):
    abstract = True

    def __call__(self, *args, **kwargs):
        headers = getattr(self.request, 'headers', {}) or {}
        clear_observability_context()
        set_correlation_id(headers.get('correlation_id'))
        try:
            return super().__call__(*args, **kwargs)
        finally:
            clear_observability_context()


class MonitoredTask(CorrelatedTask):
    """Base Celery task that tracks consecutive failures and alerts admin.

    Any periodic task that extends this class will automatically:
    - Count consecutive failures in Redis
    - Send an admin alert email after more than 2 consecutive failures
    - Reset the failure counter on success
    """
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        failure_key = f"task_failures:{self.name}"
        failures = _redis.incr(failure_key)
        _redis.expire(failure_key, 86400)  # reset counter after 24h

        if failures > 2:
            from apps.notifications.tasks import send_admin_failure_alert
            apply_async_with_correlation(
                send_admin_failure_alert,
                args=[self.name, str(exc)],
            )

    def on_success(self, retval, task_id, args, kwargs):
        # reset failure counter on success
        failure_key = f"task_failures:{self.name}"
        _redis.delete(failure_key)


@shared_task(
    bind=True,
    base=MonitoredTask,
    queue="scheduled",
    name="apps.core.tasks.run_data_retention_policy",
)
def run_data_retention_policy(self):
    current_time = timezone.now()
    try:
        preview = build_retention_preview(
            now=current_time,
            access_log_retention_days=ACCESS_LOG_RETENTION_DAYS,
            error_log_retention_days=ERROR_LOG_RETENTION_DAYS,
            anonymisation_grace_days=USER_ANONYMISATION_GRACE_DAYS,
        )
        send_retention_preview_email(preview)

        audit_log_count_before = AuditLog.objects.count()
        assert getattr(AuditLog, "retention_exempt", False) is True, "AuditLog must remain retention exempt."

        result = apply_data_retention_policy(
            now=current_time,
            access_log_retention_days=ACCESS_LOG_RETENTION_DAYS,
            error_log_retention_days=ERROR_LOG_RETENTION_DAYS,
            anonymisation_grace_days=USER_ANONYMISATION_GRACE_DAYS,
        )

        audit_log_count_after = AuditLog.objects.count()
        assert audit_log_count_before == audit_log_count_after, "AuditLog rows must never be purged."
        return result
    except Exception as exc:
        formatted_traceback = traceback.format_exc()
        ErrorLog.objects.create(
            level="ERROR",
            message=f"run_data_retention_policy failed: {exc}",
            traceback=formatted_traceback,
            stack_trace=formatted_traceback,
        )
        raise
