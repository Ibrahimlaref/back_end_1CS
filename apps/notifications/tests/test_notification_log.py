from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import Gym
from apps.notifications.models import Notification, NotificationLog
from apps.notifications.services.analytics import open_rate_by_type
from apps.notifications.tasks import retry_failed_notifications
from apps.users.models import User


def _create_notification(notification_type: str = Notification.Type.GENERAL) -> Notification:
    suffix = timezone.now().strftime("%H%M%S%f")
    user = User.objects.create_user(
        email=f"{notification_type}-{suffix}@example.com",
        password="StrongPass123!",
    )
    gym = Gym.objects.create(name=f"Gym {suffix}", slug=f"gym-{suffix}")
    return Notification.objects.create(
        gym=gym,
        user=user,
        type=notification_type,
        title="Title",
        message="Body",
    )


@pytest.mark.django_db
def test_email_webhook_updates_notification_log_status():
    client = APIClient()
    notification = _create_notification()
    log = NotificationLog.objects.create(
        notification=notification,
        channel=NotificationLog.Channel.EMAIL,
        status=NotificationLog.Status.SENT,
    )

    payload = {
        "event": "delivered",
        "notification_id": str(notification.id),
        "provider": "sendgrid",
    }

    response = client.post("/api/v1/notifications/webhooks/email/", payload, format="json")

    log.refresh_from_db()

    assert response.status_code == 200
    assert response.json() == {"updated": 1}
    assert log.status == NotificationLog.Status.DELIVERED
    assert log.raw_payload["event"] == "delivered"
    assert log.raw_payload["notification_id"] == str(notification.id)


@pytest.mark.django_db
def test_open_rate_by_type_returns_correct_percentages():
    general_opened = _create_notification(Notification.Type.GENERAL)
    NotificationLog.objects.create(
        notification=general_opened,
        channel=NotificationLog.Channel.EMAIL,
        status=NotificationLog.Status.OPENED,
    )

    general_delivered = _create_notification(Notification.Type.GENERAL)
    NotificationLog.objects.create(
        notification=general_delivered,
        channel=NotificationLog.Channel.EMAIL,
        status=NotificationLog.Status.DELIVERED,
    )

    promotion_sent = _create_notification(Notification.Type.PROMOTION)
    NotificationLog.objects.create(
        notification=promotion_sent,
        channel=NotificationLog.Channel.EMAIL,
        status=NotificationLog.Status.SENT,
    )

    old_notification = _create_notification(Notification.Type.GENERAL)
    old_log = NotificationLog.objects.create(
        notification=old_notification,
        channel=NotificationLog.Channel.EMAIL,
        status=NotificationLog.Status.OPENED,
    )
    NotificationLog.objects.filter(pk=old_log.pk).update(timestamp=timezone.now() - timedelta(days=60))

    metrics = {item["type"]: item for item in open_rate_by_type(days=30)}

    assert metrics["general"] == {
        "type": "general",
        "sent": 2,
        "opened": 1,
        "open_rate_pct": 50.0,
    }
    assert metrics["promotion"] == {
        "type": "promotion",
        "sent": 1,
        "opened": 0,
        "open_rate_pct": 0.0,
    }


@pytest.mark.django_db
@patch("apps.notifications.tasks.send_email_notification.apply_async")
def test_retry_failed_notifications_enqueues_retry_with_countdown(mock_apply_async):
    notification = _create_notification()
    log = NotificationLog.objects.create(
        notification=notification,
        channel=NotificationLog.Channel.EMAIL,
        status=NotificationLog.Status.FAILED,
    )

    scheduled_count = retry_failed_notifications.run()

    mock_apply_async.assert_called_once_with(
        args=[str(notification.id), str(notification.user_id)],
        countdown=300,
    )
    assert scheduled_count == 1

    log.refresh_from_db()
    assert log.raw_payload["_retry_enqueued"] is True
