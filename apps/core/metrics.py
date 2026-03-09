from __future__ import annotations

from importlib.util import find_spec

PROMETHEUS_CLIENT_AVAILABLE = find_spec("prometheus_client") is not None

if PROMETHEUS_CLIENT_AVAILABLE:
    from prometheus_client import Counter, Histogram
else:
    class _FallbackCounterChild:
        def __init__(self):
            self.value = 0.0

        def inc(self, amount=1.0):
            self.value += amount

    class _FallbackHistogramChild:
        def __init__(self):
            self.count = 0
            self.sum = 0.0
            self.values: list[float] = []

        def observe(self, value):
            self.count += 1
            self.sum += value
            self.values.append(value)

    class Counter:
        def __init__(self, _name, _doc, labelnames):
            self.labelnames = tuple(labelnames)
            self._children = {}

        def labels(self, *label_values):
            key = tuple(label_values)
            if key not in self._children:
                self._children[key] = _FallbackCounterChild()
            return self._children[key]

        def clear(self):
            self._children = {}

    class Histogram:
        def __init__(self, _name, _doc, labelnames, buckets=None):
            self.labelnames = tuple(labelnames)
            self.buckets = tuple(buckets or ())
            self._children = {}

        def labels(self, *label_values):
            key = tuple(label_values)
            if key not in self._children:
                self._children[key] = _FallbackHistogramChild()
            return self._children[key]

        def clear(self):
            self._children = {}


REQUEST_COUNT = Counter(
    "request_count_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "request_latency_ms",
    "HTTP request latency in milliseconds",
    ["endpoint"],
    buckets=[10, 50, 100, 250, 500, 1000, 2500],
)
CELERY_TASK_DURATION = Histogram(
    "celery_task_duration_seconds",
    "Celery task execution time",
    ["task_name"],
)


def reset_metrics_for_tests() -> None:
    for metric in (REQUEST_COUNT, REQUEST_LATENCY, CELERY_TASK_DURATION):
        if hasattr(metric, "clear"):
            metric.clear()


def get_counter_value(metric, *label_values):
    child = metric.labels(*label_values)
    if hasattr(child, "_value"):
        return child._value.get()
    sample = _find_metric_sample(metric, "_total", label_values)
    if sample is not None:
        return sample
    return child.value


def get_histogram_count(metric, *label_values):
    child = metric.labels(*label_values)
    if hasattr(child, "_count"):
        return child._count.get()
    sample = _find_metric_sample(metric, "_count", label_values)
    if sample is not None:
        return sample
    return child.count


def _find_metric_sample(metric, suffix: str, label_values):
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
