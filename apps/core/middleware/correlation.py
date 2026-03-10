import threading
import time
import uuid

from apps.core.metrics import REQUEST_COUNT, REQUEST_LATENCY

_state = threading.local()


def get_correlation_id() -> str | None:
    return getattr(_state, "correlation_id", None)


def set_correlation_id(correlation_id: str | None) -> None:
    _state.correlation_id = correlation_id


def get_gym_id() -> str | None:
    return getattr(_state, "gym_id", None)


def set_gym_id(gym_id) -> None:
    _state.gym_id = str(gym_id) if gym_id is not None else None


def clear_observability_context() -> None:
    set_correlation_id(None)
    set_gym_id(None)


class CorrelationIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.monotonic()
        correlation_id = request.META.get("HTTP_X_REQUEST_ID") or str(uuid.uuid4())
        trace_id = request.META.get("HTTP_X_TRACE_ID") or correlation_id

        request.correlation_id = correlation_id
        request.request_id = correlation_id
        request.trace_id = trace_id

        clear_observability_context()
        set_correlation_id(correlation_id)

        response = None
        status_code = 500

        try:
            response = self.get_response(request)
            status_code = getattr(response, "status_code", 500)
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            endpoint = self._resolve_endpoint(request)
            duration_ms = (time.monotonic() - started) * 1000
            REQUEST_COUNT.labels(request.method, endpoint, str(status_code)).inc()
            REQUEST_LATENCY.labels(endpoint).observe(duration_ms)

            if response is not None:
                response["X-Request-ID"] = correlation_id

            clear_observability_context()

    @staticmethod
    def _resolve_endpoint(request):
        match = getattr(request, "resolver_match", None)
        route = getattr(match, "route", None) if match else None
        if route:
            return route if route.startswith("/") else f"/{route}"
        return request.path
