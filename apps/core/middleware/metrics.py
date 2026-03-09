try:
    from django_prometheus.middleware import (
        PrometheusAfterMiddleware as _PrometheusAfterMiddleware,
        PrometheusBeforeMiddleware as _PrometheusBeforeMiddleware,
    )
except ImportError:  # pragma: no cover - exercised only when package is missing
    class _PrometheusBeforeMiddleware:
        def __init__(self, get_response):
            self.get_response = get_response

        def __call__(self, request):
            return self.get_response(request)

    class _PrometheusAfterMiddleware:
        def __init__(self, get_response):
            self.get_response = get_response

        def __call__(self, request):
            return self.get_response(request)


class PrometheusBeforeMiddleware(_PrometheusBeforeMiddleware):
    pass


class PrometheusAfterMiddleware(_PrometheusAfterMiddleware):
    pass
