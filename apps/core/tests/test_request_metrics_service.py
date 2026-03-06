from django.test import SimpleTestCase, override_settings

from apps.core.services.request_metrics import RequestMetricsService


class FakePipeline:
    def __init__(self, client):
        self.client = client
        self.ops = []

    def lpush(self, key, value):
        self.ops.append(("lpush", key, value))
        return self

    def ltrim(self, key, start, end):
        self.ops.append(("ltrim", key, start, end))
        return self

    def expire(self, key, ttl):
        self.ops.append(("expire", key, ttl))
        return self

    def execute(self):
        for op in self.ops:
            name = op[0]
            if name == "lpush":
                _, key, value = op
                self.client.lpush(key, value)
            elif name == "ltrim":
                _, key, start, end = op
                self.client.ltrim(key, start, end)
            elif name == "expire":
                _, key, ttl = op
                self.client.expire(key, ttl)
        self.ops = []
        return True


class FakeRedis:
    def __init__(self):
        self.data = {}
        self.ttl = {}

    def pipeline(self):
        return FakePipeline(self)

    def lpush(self, key, value):
        self.data.setdefault(key, [])
        self.data[key].insert(0, str(value))
        return len(self.data[key])

    def ltrim(self, key, start, end):
        items = self.data.get(key, [])
        self.data[key] = items[start : end + 1]
        return True

    def expire(self, key, ttl):
        self.ttl[key] = ttl
        return True

    def lrange(self, key, start, end):
        values = self.data.get(key, [])
        if end == -1:
            return values[start:]
        return values[start : end + 1]

    def set(self, key, value, nx=False, ex=None):
        exists = key in self.data
        if nx and exists:
            return False
        self.data[key] = [str(value)]
        if ex is not None:
            self.ttl[key] = ex
        return True


@override_settings(
    REQUEST_LOG_BUFFER_SIZE=5,
    REQUEST_LOG_BUFFER_TTL_SEC=60,
    REQUEST_LOG_P95_ALERT_MS=500,
    REQUEST_LOG_ALERT_COOLDOWN_SEC=120,
)
class RequestMetricsServiceTests(SimpleTestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.service = RequestMetricsService(redis_client=self.redis)

    def test_record_latency_updates_buffers_and_computes_p95(self):
        self.service.record_latency("/api/a", 100)
        self.service.record_latency("/api/a", 200)
        self.service.record_latency("/api/a", 300)
        result = self.service.record_latency("/api/a", 400)

        self.assertEqual(result["p95_global_ms"], 400.0)
        self.assertEqual(result["p95_route_ms"], 400.0)
        self.assertFalse(result["alert_triggered"])

    def test_p95_alert_uses_cooldown_lock(self):
        first = self.service.record_latency("/api/a", 900)
        second = self.service.record_latency("/api/a", 950)

        self.assertTrue(first["alert_triggered"])
        self.assertFalse(second["alert_triggered"])

    def test_handles_missing_redis_client(self):
        service = RequestMetricsService(redis_client=None)
        service.redis_client = None
        result = service.record_latency("/api/a", 123)

        self.assertIsNone(result["p95_global_ms"])
        self.assertIsNone(result["p95_route_ms"])
        self.assertFalse(result["alert_triggered"])

