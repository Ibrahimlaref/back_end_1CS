import firebase_admin
from firebase_admin import credentials, messaging
from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from smtplib import SMTPRecipientsRefused

from .models import Notification, NotificationLog, UserDevice
from .locks import redis_task_lock

User = get_user_model()

if not firebase_admin._apps:
    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)


@shared_task(
    bind=True,
    max_retries=3,
    queue='notifications',
    name='apps.notifications.tasks.send_email',
)
def send_email(self, template_name: str, context: dict, recipient: str):
    """Render an email from Django templates and dispatch asynchronously.

    Retries 3 times with 5-minute backoff on failure.
    On bounce (SMTPRecipientsRefused), sets email_verified=False on the user.
    Uses Redis lock to prevent duplicate sends.
    """
    with redis_task_lock('send_email', recipient) as acquired:
        if not acquired:
            return  # duplicate task, exit safely

        try:
            subject = render_to_string(f'notifications/emails/{template_name}_subject.txt', context).strip()
            text_body = render_to_string(f'notifications/emails/{template_name}.txt', context)
            html_body = render_to_string(f'notifications/emails/{template_name}.html', context)

            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient],
            )
            msg.attach_alternative(html_body, "text/html")
            msg.send(fail_silently=False)

        except SMTPRecipientsRefused:
            # bounce: mark user email as needing recheck
            try:
                usr = User.objects.get(email=recipient)
                usr.email_verified = False
                usr.save(update_fields=['email_verified'])
            except User.DoesNotExist:
                pass
            raise

        except Exception as exc:
            raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True)
def send_email_notification(self, notification_id: str, user_id: str):
    """Legacy task: send raw notification email without templates."""
    with redis_task_lock('send_email_notification', notification_id) as acquired:
        if not acquired:
            return  # duplicate task, exit safely

        try:
            notif = Notification.objects.get(id=notification_id)
            user = User.objects.get(id=user_id)

            send_mail(
                subject=notif.title,
                message=notif.message,
                from_email=None,
                recipient_list=[user.email],
            )

            NotificationLog.objects.filter(notification=notif, channel=NotificationLog.Channel.EMAIL).update(
                status=NotificationLog.Status.SENT,
                delivered_at=timezone.now(),
            )
        except Exception:
            NotificationLog.objects.filter(notification_id=notification_id, channel=NotificationLog.Channel.EMAIL).update(
                status=NotificationLog.Status.FAILED,
            )
            raise


@shared_task(bind=True)
def send_push_notification(self, notification_id: str, user_id: str):
    """Lookup device tokens and dispatch push notifications via FCM."""
    with redis_task_lock('send_push_notification', notification_id) as acquired:
        if not acquired:
            return  # duplicate task, exit safely

        try:
            notif = Notification.objects.get(id=notification_id)
            devices = UserDevice.objects.filter(user_id=user_id)

            for device in devices:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=notif.title,
                        body=notif.message,
                    ),
                    token=device.token,
                )
                messaging.send(message)

            NotificationLog.objects.filter(
                notification=notif,
                channel=NotificationLog.Channel.PUSH
            ).update(
                status=NotificationLog.Status.SENT,
                delivered_at=timezone.now(),
            )
        except Exception:
            NotificationLog.objects.filter(
                notification_id=notification_id,
                channel=NotificationLog.Channel.PUSH
            ).update(status=NotificationLog.Status.FAILED)
            raise


@shared_task(queue='notifications')
def send_admin_failure_alert(task_name: str, error: str):
    """Send a failure alert email to the admin when a task fails consecutively."""
    send_email.delay(
        template_name='general',
        context={
            'title': f'⚠️ Task Failure Alert: {task_name}',
            'message': (
                f'The task "{task_name}" has failed more than 2 consecutive times.\n\n'
                f'Error: {error}'
            ),
        },
        recipient=settings.ADMIN_EMAIL,
    )