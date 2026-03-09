import time

from celery.signals import task_postrun, task_prerun

from apps.core.metrics import CELERY_TASK_DURATION


def _get_request_headers(task):
    headers = getattr(task.request, 'headers', None)
    if headers is None:
        headers = {}
        task.request.headers = headers
    return headers


@task_prerun.connect(dispatch_uid='apps.core.signals.observe_task_start')
def observe_task_start(task=None, **kwargs):
    if task is None:
        return

    headers = _get_request_headers(task)
    headers['_started_at'] = time.monotonic()


@task_postrun.connect(dispatch_uid='apps.core.signals.observe_task_completion')
def observe_task_completion(task=None, **kwargs):
    if task is None:
        return

    headers = _get_request_headers(task)
    started_at = headers.pop('_started_at', None)
    if started_at is None:
        return

    task_name = getattr(task, 'name', task.__class__.__name__)
    CELERY_TASK_DURATION.labels(task_name).observe(time.monotonic() - started_at)
