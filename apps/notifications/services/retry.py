from __future__ import annotations

from typing import Any

from apps.core.tasks import apply_async_with_correlation


def merge_notification_payload(existing_payload: Any, payload_update: dict[str, Any] | None) -> dict[str, Any] | None:
    if payload_update is None:
        return existing_payload if isinstance(existing_payload, dict) else None

    merged: dict[str, Any] = {}
    if isinstance(existing_payload, dict):
        merged.update(existing_payload)
    merged.update(payload_update)
    return merged


def retry_already_enqueued(raw_payload: Any) -> bool:
    return isinstance(raw_payload, dict) and bool(raw_payload.get("_retry_enqueued"))


def schedule_failed_notification_retry(log: Any) -> None:
    if retry_already_enqueued(log.raw_payload):
        return

    from apps.notifications.tasks import retry_failed_notifications

    apply_async_with_correlation(retry_failed_notifications)
