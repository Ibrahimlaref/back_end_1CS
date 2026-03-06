import json
import logging
from datetime import date, datetime
from decimal import Decimal


logger = logging.getLogger("observability.request")


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def emit_structured_event(event, payload, level=logging.INFO):
    body = {"event": event, **payload}
    logger.log(level, json.dumps(body, default=_json_default, separators=(",", ":")))


def emit_request_event(payload):
    emit_structured_event("api_request", payload, level=logging.INFO)


def emit_latency_alert(payload):
    emit_structured_event("latency_alert", payload, level=logging.WARNING)


def emit_internal_error(payload):
    emit_structured_event("observability_error", payload, level=logging.ERROR)

