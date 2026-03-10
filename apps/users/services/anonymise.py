from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.core.models import SystemLog
from apps.users.models import User

ANONYMISATION_GRACE_DAYS = 30


def anonymise_deleted_user(user_id) -> None:
    user = User.objects.get(pk=user_id)
    cutoff = timezone.now() - timedelta(days=ANONYMISATION_GRACE_DAYS)
    if user.deleted_at is None or user.deleted_at > cutoff or user.is_anonymised:
        return

    update_fields = {
        "email",
        "first_name",
        "last_name",
        "phone",
        "is_anonymised",
    }

    user.email = f"deleted_{user.pk}@redacted.invalid"
    user.first_name = "Redacted"
    user.last_name = "Redacted"
    if hasattr(user, "phone"):
        user.phone = ""

    explicitly_handled = {"email", "first_name", "last_name", "phone"}
    for field in user._meta.fields:
        if field.name in explicitly_handled or not getattr(field, "PII", False):
            continue

        setattr(user, field.name, _redacted_field_value(user, field))
        update_fields.add(field.name)

    user.is_anonymised = True
    user.save(update_fields=sorted(update_fields))

    detail = f"user_id={user_id}"
    SystemLog.objects.create(
        event="anonymise_user",
        operation="anonymise_user",
        level=SystemLog.Level.INFO,
        message=detail,
        detail=detail,
    )


def _redacted_field_value(user: User, field: models.Field):
    if isinstance(field, models.EmailField):
        return f"deleted_{user.pk}@redacted.invalid"
    if isinstance(field, (models.CharField, models.TextField)):
        return ""
    if isinstance(field, models.DateTimeField):
        return None if field.null else timezone.now()
    if isinstance(field, models.DateField):
        return None if field.null else timezone.now().date()
    return None if field.null else getattr(user, field.name)
