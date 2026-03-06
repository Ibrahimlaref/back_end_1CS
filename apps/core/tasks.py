import redis
from celery import Task
from django.conf import settings

_redis = redis.from_url(settings.REDIS_URL)


class MonitoredTask(Task):
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
            send_admin_failure_alert.delay(self.name, str(exc))

    def on_success(self, retval, task_id, args, kwargs):
        # reset failure counter on success
        failure_key = f"task_failures:{self.name}"
        _redis.delete(failure_key)