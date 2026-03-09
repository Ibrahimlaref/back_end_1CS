import logging
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from celery.signals import task_postrun, task_prerun
from rest_framework.test import APIClient

import apps.core.signals  # noqa: F401
from apps.core.metrics import CELERY_TASK_DURATION, get_histogram_count, reset_metrics_for_tests
from apps.core.middleware.correlation import clear_observability_context, set_correlation_id, set_gym_id
from apps.core.middleware.log_filter import CorrelationIdFilter
from apps.core.tasks import apply_async_with_correlation


@pytest.mark.django_db
@patch("apps.core.api.v1.views.health.cache.get", return_value=None)
def test_correlation_middleware_sets_request_id_on_response(_mock_cache_get):
    client = APIClient()

    response = client.get("/health/")

    assert response.status_code == 200
    assert response["X-Request-ID"]


@pytest.mark.django_db
@patch("apps.core.api.v1.views.health.cache.get", return_value=None)
def test_correlation_middleware_echoes_provided_request_id(_mock_cache_get):
    client = APIClient()

    response = client.get("/health/", HTTP_X_REQUEST_ID="req-123")

    assert response.status_code == 200
    assert response["X-Request-ID"] == "req-123"


def test_correlation_filter_injects_correlation_id_into_log_records():
    record = logging.LogRecord(
        name="observability.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )

    set_correlation_id("req-456")
    set_gym_id("gym-789")
    try:
        assert CorrelationIdFilter().filter(record) is True
        assert record.correlation_id == "req-456"
        assert record.gym_id == "gym-789"
    finally:
        clear_observability_context()


def test_apply_async_with_correlation_passes_request_id_header():
    task = Mock()

    set_correlation_id("req-999")
    try:
        apply_async_with_correlation(
            task,
            args=["alpha"],
            kwargs={"beta": "value"},
            countdown=30,
        )
    finally:
        clear_observability_context()

    task.apply_async.assert_called_once()
    task_kwargs = task.apply_async.call_args.kwargs
    assert task_kwargs["args"] == ["alpha"]
    assert task_kwargs["kwargs"] == {"beta": "value"}
    assert task_kwargs["countdown"] == 30
    assert task_kwargs["headers"]["correlation_id"] == "req-999"


def test_celery_task_duration_metric_is_observed_on_task_completion():
    reset_metrics_for_tests()

    class DummyTask:
        name = "tests.dummy_task"

    task = DummyTask()
    task.request = SimpleNamespace(headers={})

    with patch("apps.core.signals.time.monotonic", side_effect=[10.0, 12.5]):
        task_prerun.send(sender=DummyTask, task_id="task-1", task=task, args=(), kwargs={})
        task_postrun.send(
            sender=DummyTask,
            task_id="task-1",
            task=task,
            args=(),
            kwargs={},
            retval=None,
            state="SUCCESS",
        )

    assert get_histogram_count(CELERY_TASK_DURATION, "tests.dummy_task") == 1
