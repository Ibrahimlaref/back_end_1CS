import logging
import math

import redis
from django.conf import settings


logger = logging.getLogger(__name__)


class RequestMetricsService:
    GLOBAL_LATENCY_KEY = "request_metrics:latency:global"
    ROUTE_LATENCY_PREFIX = "request_metrics:latency:route:"
    GLOBAL_P95_ALERT_KEY = "request_metrics:alert:p95:global"

    def __init__(self, redis_client=None):
        self.redis_client = redis_client or self._build_client()

    def _build_client(self):
        try:
            return redis.from_url(settings.REDIS_URL)
        except Exception:
            logger.exception("Could not initialize Redis client for request metrics.")
            return None

    def record_latency(self, path, duration_ms):
        """
        Store request latency in rolling Redis buffers and compute updated p95 values.
        Returns:
        {
            "p95_global_ms": float | None,
            "p95_route_ms": float | None,
            "alert_triggered": bool,
        }
        """
        result = {
            "p95_global_ms": None,
            "p95_route_ms": None,
            "alert_triggered": False,
        }

        client = self.redis_client
        if client is None:
            return result

        try:
            route_key = self._route_key(path)
            self._append_latency(client, self.GLOBAL_LATENCY_KEY, duration_ms)
            self._append_latency(client, route_key, duration_ms)

            global_values = self._read_latencies(client, self.GLOBAL_LATENCY_KEY)
            route_values = self._read_latencies(client, route_key)

            result["p95_global_ms"] = self._compute_p95(global_values)
            result["p95_route_ms"] = self._compute_p95(route_values)

            threshold = float(settings.REQUEST_LOG_P95_ALERT_MS)
            p95_global = result["p95_global_ms"]
            if p95_global is not None and p95_global > threshold:
                cooldown = int(settings.REQUEST_LOG_ALERT_COOLDOWN_SEC)
                result["alert_triggered"] = bool(
                    client.set(self.GLOBAL_P95_ALERT_KEY, "1", nx=True, ex=cooldown)
                )

        except Exception:
            logger.exception("Failed recording request latency metrics.")

        return result

    def _append_latency(self, client, key, duration_ms):
        ttl = int(settings.REQUEST_LOG_BUFFER_TTL_SEC)
        max_items = int(settings.REQUEST_LOG_BUFFER_SIZE)

        pipeline = client.pipeline()
        pipeline.lpush(key, int(duration_ms))
        pipeline.ltrim(key, 0, max_items - 1)
        pipeline.expire(key, ttl)
        pipeline.execute()

    def _read_latencies(self, client, key):
        max_items = int(settings.REQUEST_LOG_BUFFER_SIZE)
        values = client.lrange(key, 0, max_items - 1)
        parsed = []
        for value in values:
            try:
                parsed.append(float(value))
            except (TypeError, ValueError):
                continue
        return parsed

    def _route_key(self, path):
        return f"{self.ROUTE_LATENCY_PREFIX}{path}"

    @staticmethod
    def _compute_p95(values):
        if not values:
            return None
        ordered = sorted(values)
        index = max(0, math.ceil(0.95 * len(ordered)) - 1)
        return round(float(ordered[index]), 2)

