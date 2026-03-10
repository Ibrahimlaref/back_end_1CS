from __future__ import annotations

from typing import Any

from importlib.util import find_spec

PROMETHEUS_CLIENT_AVAILABLE = find_spec("prometheus_client") is not None


class _FallbackCounterChild:
    def __init__(self) -> None:
        self.value = 0.0

    def inc(self, amount: float = 1.0) -> None:
        self.value += amount


class _FallbackHistogramChild:
    def __init__(self) -> None:
        self.count = 0
        self.sum = 0.0
        self.values: list[float] = []

    def observe(self, value: float) -> None:
        self.count += 1
        self.sum += value
        self.values.append(value)


class _FallbackCounter:
    def __init__(self, _name: str, _doc: str, labelnames: list[str]) -> None:
        self.labelnames = tuple(labelnames)
        self._children: dict[tuple[str, ...], _FallbackCounterChild] = {}

    def labels(self, *label_values: str) -> _FallbackCounterChild:
        key = tuple(label_values)
        if key not in self._children:
            self._children[key] = _FallbackCounterChild()
        return self._children[key]

    def clear(self) -> None:
        self._children = {}


class _FallbackHistogram:
    def __init__(self, _name: str, _doc: str, labelnames: list[str], buckets: list[int] | None = None) -> None:
        self.labelnames = tuple(labelnames)
        self.buckets = tuple(buckets or ())
        self._children: dict[tuple[str, ...], _FallbackHistogramChild] = {}

    def labels(self, *label_values: str) -> _FallbackHistogramChild:
        key = tuple(label_values)
        if key not in self._children:
            self._children[key] = _FallbackHistogramChild()
        return self._children[key]

    def clear(self) -> None:
        self._children = {}


def _build_counter(name: str, doc: str, labelnames: list[str]) -> Any:
    if PROMETHEUS_CLIENT_AVAILABLE:
        from prometheus_client import Counter

        return Counter(name, doc, labelnames)
    return _FallbackCounter(name, doc, labelnames)


def _build_histogram(
    name: str,
    doc: str,
    labelnames: list[str],
    buckets: list[int] | None = None,
) -> Any:
    if PROMETHEUS_CLIENT_AVAILABLE:
        from prometheus_client import Histogram

        if buckets is not None:
            return Histogram(name, doc, labelnames, buckets=buckets)
        return Histogram(name, doc, labelnames)
    return _FallbackHistogram(name, doc, labelnames, buckets=buckets)


REQUEST_COUNT = _build_counter(
    "request_count_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = _build_histogram(
    "request_latency_ms",
    "HTTP request latency in milliseconds",
    ["endpoint"],
    buckets=[10, 50, 100, 250, 500, 1000, 2500],
)
CELERY_TASK_DURATION = _build_histogram(
    "celery_task_duration_seconds",
    "Celery task execution time",
    ["task_name"],
)


def reset_metrics_for_tests() -> None:
    for metric in (REQUEST_COUNT, REQUEST_LATENCY, CELERY_TASK_DURATION):
        if hasattr(metric, "clear"):
            metric.clear()


def get_counter_value(metric: Any, *label_values: str) -> Any:
    child = metric.labels(*label_values)
    if hasattr(child, "_value"):
        return child._value.get()
    sample = _find_metric_sample(metric, "_total", label_values)
    if sample is not None:
        return sample
    return child.value


def get_histogram_count(metric: Any, *label_values: str) -> Any:
    child = metric.labels(*label_values)
    if hasattr(child, "_count"):
        return child._count.get()
    sample = _find_metric_sample(metric, "_count", label_values)
    if sample is not None:
        return sample
    return child.count


def _find_metric_sample(metric: Any, suffix: str, label_values: tuple[str, ...]) -> Any:
    label_names = tuple(getattr(metric, '_labelnames', ()))
    expected_labels = dict(zip(label_names, label_values))

    for collected_metric in metric.collect():
        for sample in collected_metric.samples:
            if sample.name != f"{collected_metric.name}{suffix}":
                continue
            sample_labels = {
                key: value
                for key, value in sample.labels.items()
                if key in expected_labels
            }
            if sample_labels == expected_labels:
                return sample.value
    return None
