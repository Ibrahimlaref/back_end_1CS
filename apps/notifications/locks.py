import redis
from django.conf import settings
from contextlib import contextmanager

_redis = redis.from_url(settings.REDIS_URL)

@contextmanager
def redis_task_lock(task_name: str, entity_id: str, timeout: int = 300):
    """
    Context manager that acquires a Redis lock before running a task.
    Uses SET NX EX pattern (set if not exists, with expiry).
    
    timeout = task execution timeout + 30s buffer
    """
    lock_key = f"task:{task_name}:{entity_id}"
    lock_ttl = timeout + 30  # execution time + 30s buffer

    # Try to acquire the lock (SET NX EX)
    acquired = _redis.set(lock_key, "1", nx=True, ex=lock_ttl)

    if not acquired:
        # Another worker is already running this task
        yield False
        return

    try:
        yield True  # lock acquired, proceed with task
    finally:
        # Always release lock when done (success or failure)
        _redis.delete(lock_key)