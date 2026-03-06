from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import Notification, NotificationPreference, NotificationLog

User = get_user_model()


class NotificationDispatcher:
    """Service responsible for dispatching notifications across channels.

    The dispatch method handles preference checking, logging, and enqueuing
    email/push tasks. In-app notifications are recorded synchronously.
    """

    @staticmethod
    def dispatch(gym, user: User, notif_type: str, channels: list[str], title: str, message: str):
        # create the master notification entry
        notif = Notification.objects.create(
            gym=gym,
            user=user,
            type=notif_type,
            title=title,
            message=message,
        )

        for channel in channels:
            # fetch preference for this user/gym/type/channel, default to enabled
            pref = NotificationPreference.objects.filter(
                gym=gym,
                user=user,
                notif_type=notif_type,
                channel=channel,
            ).first()
            enabled = True if pref is None else pref.is_enabled

            # create initial log record
            log = NotificationLog.objects.create(
                notification=notif,
                channel=channel,
                status=NotificationLog.Status.PENDING,
                attempted_at=timezone.now(),
            )

            if not enabled:
                log.status = NotificationLog.Status.FAILED
                log.save(update_fields=["status"])
                continue

            if channel == NotificationLog.Channel.IN_APP:
                # in-app is immediate
                log.status = NotificationLog.Status.SENT
                log.delivered_at = timezone.now()
                log.save(update_fields=["status", "delivered_at"])

            elif channel == NotificationLog.Channel.EMAIL:
                from . import tasks

                tasks.send_email.delay(
                    template_name='general',
                    context={
                        'title': title,
                        'message': message,
                    },
                    recipient=user.email,
                )

            elif channel == NotificationLog.Channel.PUSH:
                from . import tasks

                tasks.send_push_notification.delay(str(notif.id), str(user.id))

            else:
                log.status = NotificationLog.Status.FAILED
                log.save(update_fields=["status"])