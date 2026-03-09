from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from apps.users.models import User


def send_retention_preview_email(preview: dict) -> None:
    recipients = list(
        User.objects.filter(is_staff=True).exclude(email="").values_list("email", flat=True)
    )
    if not recipients:
        return

    html_message = render_to_string("core/emails/retention_preview.html", {"preview": preview})
    send_mail(
        subject=f"[Action Required] Scheduled data retention purge \u2014 {preview['scheduled_at']}",
        message=strip_tags(html_message),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        html_message=html_message,
    )
