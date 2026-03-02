from django.core.mail import send_mail
from django.conf import settings
from celery import shared_task


@shared_task(
    bind=True,
    max_retries=3,
    name='apps.users.tasks.send_email_task',
    queue='notifications',
)
def send_email_task(self, to_email, subject, message):
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
    except Exception as exc:
        countdown = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=countdown)