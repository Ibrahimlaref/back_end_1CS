import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

from apps.core.tasks import CorrelatedTask

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    base=CorrelatedTask,
    max_retries=3,
    default_retry_delay=60,   # retry after 60s
    name="core.tasks.dispatch_welcome_email",
)
def dispatch_welcome_email(
    self,
    *,
    gym_id: str,
    owner_email: str,
    owner_name: str,
    gym_name: str,
) -> None:
    """
    AC-4: Sends a welcome email to the gym owner after provisioning.
    Triggered via transaction.on_commit() — never fires on rollback.
    Retries up to 3 times on failure.
    """
    try:
        send_mail(
            subject=f"Welcome to FitTech — {gym_name} is ready!",
            message=(
                f"Hi {owner_name},\n\n"
                f"Your gym '{gym_name}' has been successfully provisioned on FitTech.\n\n"
                f"Gym ID: {gym_id}\n\n"
                "You can now log in and start configuring your workspace.\n\n"
                "— The FitTech Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner_email],
            fail_silently=False,
        )
        logger.info(
            "Welcome email sent to %s for gym_id=%s", owner_email, gym_id
        )

    except Exception as exc:
        logger.error(
            "Welcome email failed for gym_id=%s, retrying... error=%s",
            gym_id,
            exc,
        )
        raise self.retry(exc=exc)
