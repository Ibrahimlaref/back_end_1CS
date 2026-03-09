from __future__ import annotations

from typing import Any

from apps.notifications.models import NotificationLog
from apps.notifications.services.retry import merge_notification_payload, schedule_failed_notification_retry

SUPPORTED_PUSH_PROVIDERS = {"apns", "fcm"}


def process_push_receipt(notification_id: str, provider: str, success: bool, raw: dict[str, Any]):
    if provider not in SUPPORTED_PUSH_PROVIDERS:
        raise ValueError(f"Unsupported push provider: {provider}")
    if not isinstance(raw, dict):
        raise ValueError("Push receipt payload must be a dictionary.")

    log = (
        NotificationLog.objects.filter(
            notification_id=notification_id,
            channel=NotificationLog.Channel.PUSH,
        )
        .order_by("-timestamp")
        .first()
    )
    if log is None:
        raise NotificationLog.DoesNotExist("No matching push notification log was found.")

    previous_status = log.status
    log.status = NotificationLog.Status.DELIVERED if success else NotificationLog.Status.FAILED
    log.raw_payload = merge_notification_payload(
        log.raw_payload,
        {
            "provider": provider,
            "success": success,
            "receipt": raw,
        },
    )
    log.save(update_fields=["status", "raw_payload"])

    if log.status == NotificationLog.Status.FAILED and previous_status != NotificationLog.Status.FAILED:
        schedule_failed_notification_retry(log)

    return log
