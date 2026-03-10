from typing import TYPE_CHECKING, cast

from apps.core.tasks import apply_async_with_correlation
from apps.notifications.models import Notification, NotificationLog, NotificationPreference

if TYPE_CHECKING:
    from apps.users.models.user import User


class NotificationDispatcher:
    """Create notifications, honor channel preferences, and enqueue delivery tasks."""

    @staticmethod
    def dispatch(gym, user: "User", notif_type: str, channels: list[str], title: str, message: str) -> None:
        notif = Notification.objects.create(
            gym=gym,
            user=user,
            type=notif_type,
            title=title,
            message=message,
        )

        for channel in channels:
            pref = NotificationPreference.objects.filter(
                gym=gym,
                user=user,
                notif_type=notif_type,
                channel=channel,
            ).first()
            enabled = True if pref is None else pref.is_enabled

            log = NotificationLog.objects.create(
                notification=notif,
                channel=channel,
                status=NotificationLog.Status.PENDING,
            )

            if not enabled:
                log.status = cast(str, NotificationLog.Status.FAILED)
                log.raw_payload = {"reason": "channel_disabled"}
                log.save(update_fields=["status", "raw_payload"])
                continue

            if channel == cast(str, NotificationLog.Channel.IN_APP):
                log.status = cast(str, NotificationLog.Status.SENT)
                log.save(update_fields=["status"])
                continue

            if channel == cast(str, NotificationLog.Channel.EMAIL):
                from apps.notifications import tasks

                apply_async_with_correlation(
                    tasks.send_email_notification,
                    args=[str(notif.id), str(user.id)],
                )
                continue

            if channel == cast(str, NotificationLog.Channel.PUSH):
                from apps.notifications import tasks

                apply_async_with_correlation(
                    tasks.send_push_notification,
                    args=[str(notif.id), str(user.id)],
                )
                continue

            log.status = cast(str, NotificationLog.Status.FAILED)
            log.raw_payload = {"reason": f"channel_not_implemented:{channel}"}
            log.save(update_fields=["status", "raw_payload"])
