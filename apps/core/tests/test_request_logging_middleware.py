import json
import uuid
from unittest.mock import Mock, patch

from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from apps.core.middleware.request_logging import RequestLoggingMiddleware
from apps.core.models import RequestLog
from apps.core.services.observability import emit_request_event


@override_settings(
    REQUEST_LOGGING_ENABLED=True,
    REQUEST_LOG_SUCCESS_SAMPLE_RATE=0.10,
    REQUEST_LOG_SLOW_MS=1000,
    REQUEST_LOG_P95_ALERT_MS=500,
    REQUEST_LOG_BUFFER_SIZE=1000,
    REQUEST_LOG_BUFFER_TTL_SEC=900,
    REQUEST_LOG_ALERT_COOLDOWN_SEC=300,
    OBSERVABILITY_PROVIDER="stdout",
    REDIS_URL="redis://localhost:6379/0",
)
class RequestLoggingMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _build_middleware(self, status_code=200):
        def _response(_request):
            return JsonResponse({"ok": True}, status=status_code)

        middleware = RequestLoggingMiddleware(_response)
        middleware.metrics_service.record_latency = Mock(
            return_value={
                "p95_global_ms": 120.0,
                "p95_route_ms": 115.0,
                "alert_triggered": False,
            }
        )
        return middleware

    def test_2xx_sampling_skips_persistence_but_updates_metrics(self):
        request = self.factory.get("/api/users/v1/auth/login/")
        middleware = self._build_middleware(status_code=200)

        with patch("apps.core.middleware.request_logging.random.random", return_value=0.95), patch(
            "apps.core.middleware.request_logging.RequestLog.objects.create"
        ) as create_log, patch("apps.core.middleware.request_logging.emit_request_event") as emit_log:
            response = middleware(request)

        self.assertEqual(response.status_code, 200)
        middleware.metrics_service.record_latency.assert_called_once()
        create_log.assert_not_called()
        emit_log.assert_not_called()
        self.assertIn("X-Request-Id", response)

    def test_4xx_always_sampled_and_persisted(self):
        request = self.factory.get("/api/users/v1/auth/login/")
        request.user_id = uuid.uuid4()
        request.gym_id = uuid.uuid4()
        middleware = self._build_middleware(status_code=401)

        with patch("apps.core.middleware.request_logging.RequestLog.objects.create") as create_log, patch(
            "apps.core.middleware.request_logging.emit_request_event"
        ) as emit_log:
            response = middleware(request)

        self.assertEqual(response.status_code, 401)
        create_log.assert_called_once()
        kwargs = create_log.call_args.kwargs
        self.assertEqual(kwargs["status_code"], 401)
        self.assertEqual(kwargs["gym_id"], request.gym_id)
        self.assertEqual(kwargs["user_id"], request.user_id)
        emit_log.assert_called_once()

    def test_slow_requests_flagged_when_over_threshold(self):
        request = self.factory.get("/api/users/v1/auth/login/")
        middleware = self._build_middleware(status_code=200)

        with patch("apps.core.middleware.request_logging.random.random", return_value=0.0), patch(
            "apps.core.middleware.request_logging.RequestLog.objects.create"
        ) as create_log, patch(
            "apps.core.middleware.request_logging.time.monotonic",
            side_effect=[1.0, 2.3],
        ):
            middleware(request)

        self.assertTrue(create_log.called)
        self.assertTrue(create_log.call_args.kwargs["is_slow"])
        self.assertGreater(create_log.call_args.kwargs["duration_ms"], 1000)

    def test_p95_alert_emitted_once_when_metrics_triggers_alert(self):
        request = self.factory.get("/api/users/v1/auth/login/")
        middleware = self._build_middleware(status_code=200)
        middleware.metrics_service.record_latency = Mock(
            return_value={
                "p95_global_ms": 650.0,
                "p95_route_ms": 620.0,
                "alert_triggered": True,
            }
        )

        with patch("apps.core.middleware.request_logging.random.random", return_value=0.0), patch(
            "apps.core.middleware.request_logging.emit_latency_alert"
        ) as emit_alert:
            middleware(request)

        emit_alert.assert_called_once()
        payload = emit_alert.call_args.args[0]
        self.assertEqual(payload["alert_type"], "p95_latency")
        self.assertEqual(payload["p95_ms"], 650.0)

    def test_exception_path_logs_as_500(self):
        request = self.factory.get("/api/users/v1/auth/login/")

        def _raise(_request):
            raise RuntimeError("boom")

        middleware = RequestLoggingMiddleware(_raise)
        middleware.metrics_service.record_latency = Mock(
            return_value={
                "p95_global_ms": 200.0,
                "p95_route_ms": 180.0,
                "alert_triggered": False,
            }
        )

        with patch("apps.core.middleware.request_logging.RequestLog.objects.create") as create_log:
            with self.assertRaises(RuntimeError):
                middleware(request)

        self.assertEqual(create_log.call_args.kwargs["status_code"], 500)

    def test_null_user_and_gym_ids_when_not_available(self):
        request = self.factory.get("/api/users/v1/auth/login/")
        middleware = self._build_middleware(status_code=404)

        with patch("apps.core.middleware.request_logging.RequestLog.objects.create") as create_log:
            middleware(request)

        kwargs = create_log.call_args.kwargs
        self.assertIsNone(kwargs["user_id"])
        self.assertIsNone(kwargs["gym_id"])

    def test_redis_failure_does_not_break_request(self):
        request = self.factory.get("/api/users/v1/auth/login/")
        middleware = self._build_middleware(status_code=200)
        middleware.metrics_service.record_latency = Mock(side_effect=RuntimeError("redis down"))

        with patch("apps.core.middleware.request_logging.random.random", return_value=0.95), patch(
            "apps.core.middleware.request_logging.emit_internal_error"
        ) as emit_internal_error:
            response = middleware(request)

        self.assertEqual(response.status_code, 200)
        emit_internal_error.assert_called_once()

    def test_observability_event_is_valid_json(self):
        payload = {"trace_id": "trace-123", "method": "GET", "status_code": 200}
        with patch("apps.core.services.observability.logger.log") as logger_log:
            emit_request_event(payload)

        message = logger_log.call_args.args[1]
        data = json.loads(message)
        self.assertEqual(data["event"], "api_request")
        self.assertEqual(data["trace_id"], "trace-123")


@override_settings(
    REQUEST_LOGGING_ENABLED=True,
    REQUEST_LOG_SUCCESS_SAMPLE_RATE=0.10,
    REQUEST_LOG_SLOW_MS=1000,
    REQUEST_LOG_P95_ALERT_MS=500,
    REQUEST_LOG_BUFFER_SIZE=1000,
    REQUEST_LOG_BUFFER_TTL_SEC=900,
    REQUEST_LOG_ALERT_COOLDOWN_SEC=300,
    OBSERVABILITY_PROVIDER="stdout",
    REDIS_URL="redis://localhost:6379/0",
)
class RequestLoggingMiddlewareDatabaseTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_sampled_request_persists_row_in_request_logs_table(self):
        request = self.factory.get("/api/users/v1/auth/login/")
        request.user_id = uuid.uuid4()
        request.gym_id = uuid.uuid4()

        def _response(_request):
            return JsonResponse({"ok": False}, status=500)

        middleware = RequestLoggingMiddleware(_response)
        middleware.metrics_service.record_latency = Mock(
            return_value={
                "p95_global_ms": 200.0,
                "p95_route_ms": 190.0,
                "alert_triggered": False,
            }
        )

        with patch("apps.core.middleware.request_logging.emit_request_event"), patch(
            "apps.core.middleware.request_logging.emit_latency_alert"
        ), patch("apps.core.middleware.request_logging.emit_internal_error"):
            response = middleware(request)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(RequestLog.objects.count(), 1)

        row = RequestLog.objects.first()
        self.assertIsNotNone(row)
        self.assertEqual(row.method, "GET")
        self.assertEqual(row.path, "/api/users/v1/auth/login/")
        self.assertEqual(row.status_code, 500)
        self.assertEqual(row.gym_id, request.gym_id)
        self.assertEqual(row.user_id, request.user_id)
