import random
import time
import uuid

from django.conf import settings
from django.utils import timezone

from apps.core.models.request_log import RequestLog
from apps.core.services.observability import (
    emit_internal_error,
    emit_latency_alert,
    emit_request_event,
)
from apps.core.services.request_metrics import RequestMetricsService


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.metrics_service = RequestMetricsService()

    def __call__(self, request):
        if not self._should_observe_request(request):
            return self.get_response(request)

        started = time.monotonic()
        request_id = self._request_id_from_headers(request)
        trace_id = request.META.get("HTTP_X_TRACE_ID") or request_id
        request.request_id = request_id
        request.trace_id = trace_id

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
            duration_ms = int((time.monotonic() - started) * 1000)
            path = self._resolve_path(request)
            is_slow = duration_ms > int(settings.REQUEST_LOG_SLOW_MS)
            gym_id = self._normalize_uuid(getattr(request, "gym_id", None))
            user_id = self._normalize_uuid(self._resolve_user_id(request))

            try:
                metrics = self.metrics_service.record_latency(path=path, duration_ms=duration_ms)
            except Exception as exc:
                metrics = {
                    "p95_global_ms": None,
                    "p95_route_ms": None,
                    "alert_triggered": False,
                }
                emit_internal_error(
                    {
                        "message": "request_metrics_failed",
                        "error": str(exc),
                        "path": path,
                        "trace_id": trace_id,
                    }
                )

            p95_global_ms = metrics.get("p95_global_ms")
            sampled = self._should_sample(status_code)

            payload = {
                "trace_id": trace_id,
                "request_id": request_id,
                "method": request.method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "is_slow": is_slow,
                "gym_id": str(gym_id) if gym_id else None,
                "user_id": str(user_id) if user_id else None,
                "timestamp": timezone.now().isoformat(),
                "sampled": sampled,
                "p95_ms": p95_global_ms,
                "provider": settings.OBSERVABILITY_PROVIDER,
            }

            if sampled:
                self._persist_request_log(
                    method=request.method,
                    path=path,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    gym_id=gym_id,
                    user_id=user_id,
                    is_slow=is_slow,
                )
                emit_request_event(payload)

            if metrics.get("alert_triggered"):
                emit_latency_alert(
                    {
                        "trace_id": trace_id,
                        "path": path,
                        "p95_ms": p95_global_ms,
                        "threshold_ms": settings.REQUEST_LOG_P95_ALERT_MS,
                        "alert_type": "p95_latency",
                    }
                )

            if response is not None:
                response["X-Request-ID"] = request_id

    @staticmethod
    def _should_observe_request(request):
        if not getattr(settings, "REQUEST_LOGGING_ENABLED", True):
            return False
        return request.path.startswith("/api/")

    @staticmethod
    def _request_id_from_headers(request):
        return (
            getattr(request, "correlation_id", None)
            or getattr(request, "request_id", None)
            or request.META.get("HTTP_X_REQUEST_ID")
            or str(uuid.uuid4())
        )

    @staticmethod
    def _resolve_path(request):
        match = getattr(request, "resolver_match", None)
        route = getattr(match, "route", None) if match else None
        if route:
            return route if route.startswith("/") else f"/{route}"
        return request.path

    @staticmethod
    def _resolve_user_id(request):
        request_user_id = getattr(request, "user_id", None)
        if request_user_id:
            return request_user_id

        user = getattr(request, "user", None)
        if not user:
            return None
        if getattr(user, "is_authenticated", False):
            return getattr(user, "id", None)
        return None

    @staticmethod
    def _normalize_uuid(value):
        if not value:
            return None
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError, AttributeError):
            return None

    @staticmethod
    def _should_sample(status_code):
        if status_code >= 400:
            return True
        if 200 <= status_code < 300:
            return random.random() < float(settings.REQUEST_LOG_SUCCESS_SAMPLE_RATE)
        return True

    @staticmethod
    def _persist_request_log(**kwargs):
        try:
            RequestLog.objects.create(**kwargs)
        except Exception as exc:
            emit_internal_error(
                {
                    "message": "request_log_persist_failed",
                    "error": str(exc),
                    "path": kwargs.get("path"),
                }
            )
