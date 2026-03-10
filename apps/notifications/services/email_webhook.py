from __future__ import annotations

from typing import Any
from typing import cast

from apps.notifications.models import NotificationLog
from apps.notifications.services.retry import merge_notification_payload, schedule_failed_notification_retry

EVENT_STATUS_MAP = {
    "bounce": cast(str, NotificationLog.Status.FAILED),
    "bounced": cast(str, NotificationLog.Status.FAILED),
    "delivered": cast(str, NotificationLog.Status.DELIVERED),
    "failed": cast(str, NotificationLog.Status.FAILED),
    "open": cast(str, NotificationLog.Status.OPENED),
    "opened": cast(str, NotificationLog.Status.OPENED),
}


class InvalidEmailWebhookPayload(ValueError):
    pass


def process_email_delivery_webhook(payload: Any) -> list[NotificationLog]:
    events = _normalize_payload(payload)
    updated_logs: list[NotificationLog] = []

    for event in events:
        notification_id = _extract_notification_id(event)
        status = _extract_status(event)
        if not notification_id or not status:
            raise InvalidEmailWebhookPayload("Payload must include notification_id and a supported event type.")

        log = (
            NotificationLog.objects.filter(
                notification_id=notification_id,
                channel=NotificationLog.Channel.EMAIL,
            )
            .order_by("-timestamp")
            .first()
        )
        if log is None:
            raise InvalidEmailWebhookPayload("No matching email notification log was found.")

        previous_status = log.status
        log.status = status
        log.raw_payload = merge_notification_payload(log.raw_payload, event)
        log.save(update_fields=["status", "raw_payload"])

        if status == NotificationLog.Status.FAILED and previous_status != NotificationLog.Status.FAILED:
            schedule_failed_notification_retry(log)

        updated_logs.append(log)

    return updated_logs


def _normalize_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        events = payload
    elif isinstance(payload, dict) and isinstance(payload.get("events"), list):
        events = payload["events"]
    elif isinstance(payload, dict):
        events = [payload]
    else:
        raise InvalidEmailWebhookPayload("Webhook payload must be a JSON object or list.")

    if not events:
        raise InvalidEmailWebhookPayload("Webhook payload did not contain any events.")
    if not all(isinstance(event, dict) for event in events):
        raise InvalidEmailWebhookPayload("Each webhook event must be a JSON object.")

    return events


def _extract_status(event: dict[str, Any]) -> str | None:
    event_data = event.get("event-data")
    candidates = [
        event.get("event"),
        event.get("event_type"),
        event_data.get("event") if isinstance(event_data, dict) else None,
    ]
    for candidate in candidates:
        normalized = str(candidate).lower() if candidate is not None else None
        if normalized in EVENT_STATUS_MAP:
            return EVENT_STATUS_MAP[normalized]
    return None


def _extract_notification_id(event: dict[str, Any]) -> str | None:
    nested_candidates = [
        event,
        event.get("custom_args") if isinstance(event.get("custom_args"), dict) else None,
        event.get("user-variables") if isinstance(event.get("user-variables"), dict) else None,
        event.get("user_variables") if isinstance(event.get("user_variables"), dict) else None,
        event.get("event-data") if isinstance(event.get("event-data"), dict) else None,
    ]

    event_data = event.get("event-data")
    if isinstance(event_data, dict):
        nested_candidates.extend(
            [
                event_data.get("user-variables") if isinstance(event_data.get("user-variables"), dict) else None,
                event_data.get("custom-variables") if isinstance(event_data.get("custom-variables"), dict) else None,
                event_data.get("custom_variables") if isinstance(event_data.get("custom_variables"), dict) else None,
            ]
        )

    for candidate in nested_candidates:
        if not isinstance(candidate, dict):
            continue
        value = candidate.get("notification_id") or candidate.get("notificationId")
        if value:
            return str(value)

    return None
