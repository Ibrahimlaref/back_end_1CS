from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core import mail
from django.test import override_settings
from django.utils import timezone

from apps.core.models import AccessLog, AuditLog, Gym, SystemLog
from apps.core.services.retention_email import send_retention_preview_email
from apps.core.tasks import run_data_retention_policy
from apps.users.models import User
from apps.users.services.anonymise import anonymise_deleted_user


def _create_user(email: str, **extra_fields) -> User:
    defaults = {
        "password": "StrongPass123!",
        "first_name": "Alice",
        "last_name": "Member",
        "phone": "+1234567890",
        "photo_url": "https://example.com/photo.jpg",
        "date_of_birth": timezone.now().date(),
    }
    defaults.update(extra_fields)
    password = defaults.pop("password")
    return User.objects.create_user(email=email, password=password, **defaults)


def _create_gym(slug: str) -> Gym:
    return Gym.objects.create(name=f"Gym {slug}", slug=slug)


@pytest.mark.django_db
def test_anonymise_deleted_user_anonymises_user_after_grace_period():
    now = timezone.now()
    user = _create_user(
        "deleted@example.com",
        is_deleted=True,
        deleted_at=now - timedelta(days=31),
        is_anonymised=False,
    )

    with patch("apps.users.services.anonymise.timezone.now", return_value=now):
        anonymise_deleted_user(user.pk)

    user.refresh_from_db()

    assert user.email == f"deleted_{user.pk}@redacted.invalid"
    assert user.first_name == "Redacted"
    assert user.last_name == "Redacted"
    assert user.phone == ""
    assert user.photo_url == ""
    assert user.date_of_birth is None
    assert user.is_anonymised is True
    assert SystemLog.objects.filter(operation="anonymise_user", detail=f"user_id={user.pk}").exists()


@pytest.mark.django_db
def test_anonymise_deleted_user_is_noop_before_grace_period():
    now = timezone.now()
    user = _create_user(
        "recently-deleted@example.com",
        is_deleted=True,
        deleted_at=now - timedelta(days=29),
        is_anonymised=False,
    )
    original_email = user.email
    original_photo_url = user.photo_url

    with patch("apps.users.services.anonymise.timezone.now", return_value=now):
        anonymise_deleted_user(user.pk)

    user.refresh_from_db()

    assert user.email == original_email
    assert user.photo_url == original_photo_url
    assert user.is_anonymised is False
    assert SystemLog.objects.filter(operation="anonymise_user").count() == 0


@pytest.mark.django_db
@patch("apps.core.tasks.send_retention_preview_email")
def test_run_data_retention_policy_deletes_only_access_logs_beyond_cutoff(mock_preview_email):
    now = timezone.now()
    user = _create_user("member@example.com")
    gym = _create_gym("retention-access")

    old_log = AccessLog.objects.create(
        gym=gym,
        user=user,
        entry_type=AccessLog.EntryType.ENTRY,
        method=AccessLog.Method.MANUAL,
        path="/old",
        ip="10.0.0.1",
    )
    boundary_log = AccessLog.objects.create(
        gym=gym,
        user=user,
        entry_type=AccessLog.EntryType.ENTRY,
        method=AccessLog.Method.MANUAL,
        path="/boundary",
        ip="10.0.0.2",
    )
    recent_log = AccessLog.objects.create(
        gym=gym,
        user=user,
        entry_type=AccessLog.EntryType.ENTRY,
        method=AccessLog.Method.MANUAL,
        path="/recent",
        ip="10.0.0.3",
    )
    AccessLog.objects.filter(pk=old_log.pk).update(
        timestamp=now - timedelta(days=731),
        accessed_at=now - timedelta(days=731),
    )
    AccessLog.objects.filter(pk=boundary_log.pk).update(
        timestamp=now - timedelta(days=730),
        accessed_at=now - timedelta(days=730),
    )
    AccessLog.objects.filter(pk=recent_log.pk).update(
        timestamp=now - timedelta(days=100),
        accessed_at=now - timedelta(days=100),
    )

    with patch("apps.core.tasks.timezone.now", return_value=now):
        result = run_data_retention_policy.run()

    assert result["access_logs_deleted"] == 1
    assert not AccessLog.objects.filter(pk=old_log.pk).exists()
    assert AccessLog.objects.filter(pk=boundary_log.pk).exists()
    assert AccessLog.objects.filter(pk=recent_log.pk).exists()
    assert SystemLog.objects.filter(operation="purge_access_logs").exists()
    mock_preview_email.assert_called_once()


@pytest.mark.django_db
@patch("apps.core.tasks.send_retention_preview_email")
def test_audit_logs_are_never_deleted_by_retention_task(mock_preview_email):
    now = timezone.now()
    user = _create_user("audited@example.com")
    gym = _create_gym("retention-audit")
    audit_log = AuditLog.objects.create(
        gym=gym,
        actor=user,
        user=user,
        action=AuditLog.Action.CREATE,
        data={"resource": "membership"},
    )
    AuditLog.objects.filter(pk=audit_log.pk).update(
        timestamp=now - timedelta(days=5000),
        created_at=now - timedelta(days=5000),
    )

    with patch("apps.core.tasks.timezone.now", return_value=now):
        run_data_retention_policy.run()

    assert AuditLog.objects.filter(pk=audit_log.pk).exists()
    assert AuditLog.objects.count() == 1
    mock_preview_email.assert_called_once()


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_send_retention_preview_email_sends_to_all_staff_users():
    staff_one = _create_user("staff-one@example.com", is_staff=True)
    staff_two = _create_user("staff-two@example.com", is_staff=True)
    _create_user("member-only@example.com", is_staff=False)

    preview = {
        "access_logs_to_delete": 12,
        "error_logs_to_delete": 3,
        "users_to_anonymise": 2,
        "scheduled_at": "2026-04-01T02:00:00+00:00",
    }

    send_retention_preview_email(preview)

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.subject == "[Action Required] Scheduled data retention purge \u2014 2026-04-01T02:00:00+00:00"
    assert set(email.to) == {staff_one.email, staff_two.email}
    assert "Users to anonymise: 2" in email.alternatives[0][0]
