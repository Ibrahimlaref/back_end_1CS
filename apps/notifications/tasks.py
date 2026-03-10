from datetime import timedelta
from smtplib import SMTPRecipientsRefused

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from apps.core.tasks import CorrelatedTask, apply_async_with_correlation

from .locks import redis_task_lock
from .models import Notification, NotificationLog, UserDevice
from .services.push_receipt import process_push_receipt
from .services.retry import (
    merge_notification_payload,
    retry_already_enqueued,
    schedule_failed_notification_retry,
)

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except ImportError:  # pragma: no cover - optional dependency in local/test environments
    firebase_admin = None
    credentials = None
    messaging = None

User = get_user_model()

def _ensure_firebase_initialized():
    if firebase_admin is None or credentials is None:
        raise RuntimeError("firebase_admin is not installed.")

    if firebase_admin._apps:
        return

    credentials_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", "")
    if not credentials_path:
        raise RuntimeError("FIREBASE_CREDENTIALS_PATH is not configured")

    cred = credentials.Certificate(credentials_path)
    firebase_admin.initialize_app(cred)


def _update_log(notification_id: str, channel: str, status: str, raw_payload: dict | None = None):
    log = (
        NotificationLog.objects.filter(notification_id=notification_id, channel=channel)
        .order_by("-timestamp")
        .first()
    )
    if log is None:
        return None

    log.status = status
    if raw_payload is not None:
        log.raw_payload = merge_notification_payload(log.raw_payload, raw_payload)
        log.save(update_fields=["status", "raw_payload"])
    else:
        log.save(update_fields=["status"])

    return log


@shared_task(
    bind=True,
    base=CorrelatedTask,
    max_retries=3,
    queue="notifications",
    name="apps.notifications.tasks.send_email",
)
def send_email(self, template_name: str, context: dict, recipient: str):
    """Render an email from Django templates and dispatch asynchronously."""
    with redis_task_lock("send_email", recipient) as acquired:
        if not acquired:
            return

        try:
            subject = render_to_string(f"notifications/emails/{template_name}_subject.txt", context).strip()
            text_body = render_to_string(f"notifications/emails/{template_name}.txt", context)
            html_body = render_to_string(f"notifications/emails/{template_name}.html", context)

            message = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient],
            )
            message.attach_alternative(html_body, "text/html")
            message.send(fail_silently=False)
        except SMTPRecipientsRefused:
            try:
                user = User.objects.get(email=recipient)
                user.email_verified = False
                user.save(update_fields=["email_verified"])
            except User.DoesNotExist:
                pass
            raise
        except Exception as exc:
            raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, base=CorrelatedTask)
def send_email_notification(self, notification_id: str, user_id: str):
    """Send a notification email and mark the channel log as sent or failed."""
    with redis_task_lock("send_email_notification", notification_id) as acquired:
        if not acquired:
            return

        try:
            notification = Notification.objects.get(id=notification_id)
            user = User.objects.get(id=user_id)

            send_mail(
                subject=notification.title,
                message=notification.message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )

            _update_log(
                notification_id=notification_id,
                channel=NotificationLog.Channel.EMAIL,
                status=NotificationLog.Status.SENT,
            )
        except Exception as exc:
            log = _update_log(
                notification_id=notification_id,
                channel=NotificationLog.Channel.EMAIL,
                status=NotificationLog.Status.FAILED,
                raw_payload={"error": str(exc)},
            )
            if log is not None:
                schedule_failed_notification_retry(log)
            raise


@shared_task(bind=True, base=CorrelatedTask)
def send_push_notification(self, notification_id: str, user_id: str):
    """Lookup device tokens and dispatch push notifications via FCM."""
    with redis_task_lock("send_push_notification", notification_id) as acquired:
        if not acquired:
            return

        try:
            _ensure_firebase_initialized()
            notification = Notification.objects.get(id=notification_id)
            devices = UserDevice.objects.filter(user_id=user_id)
            responses = []

            for device in devices:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=notification.title,
                        body=notification.message,
                    ),
                    token=device.token,
                )
                message_id = messaging.send(message)
                responses.append(
                    {
                        "device_id": str(device.id),
                        "platform": device.platform,
                        "message_id": message_id,
                    }
                )

            process_push_receipt(
                notification_id=notification_id,
                provider="fcm",
                success=True,
                raw={"responses": responses},
            )
        except Exception as exc:
            if NotificationLog.objects.filter(
                notification_id=notification_id,
                channel=NotificationLog.Channel.PUSH,
            ).exists():
                process_push_receipt(
                    notification_id=notification_id,
                    provider="fcm",
                    success=False,
                    raw={"error": str(exc)},
                )
            raise


@shared_task(base=CorrelatedTask, queue="notifications")
def send_admin_failure_alert(task_name: str, error: str):
    apply_async_with_correlation(
        send_email,
        kwargs={
            "template_name": "general",
            "context": {
                "title": f"Task Failure Alert: {task_name}",
                "message": (
                    f'The task "{task_name}" has failed more than 2 consecutive times.\n\n'
                    f"Error: {error}"
                ),
            },
            "recipient": settings.ADMIN_EMAIL,
        },
    )
