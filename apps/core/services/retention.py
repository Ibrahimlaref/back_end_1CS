from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.core.models import AccessLog, ErrorLog, SystemLog
from apps.users.models import User
from apps.users.services.anonymise import anonymise_deleted_user


def build_retention_preview(
    *,
    now=None,
    access_log_retention_days: int,
    error_log_retention_days: int,
    anonymisation_grace_days: int,
) -> dict[str, int | str]:
    current_time = now or timezone.now()
    access_cutoff = current_time - timedelta(days=access_log_retention_days)
    error_cutoff = current_time - timedelta(days=error_log_retention_days)
    anonymisation_cutoff = current_time - timedelta(days=anonymisation_grace_days)

    return {
        "access_logs_to_delete": AccessLog.objects.filter(timestamp__lt=access_cutoff).count(),
        "error_logs_to_delete": ErrorLog.objects.filter(timestamp__lt=error_cutoff).count(),
        "users_to_anonymise": User.objects.filter(
            is_anonymised=False,
            deleted_at__isnull=False,
            deleted_at__lte=anonymisation_cutoff,
        ).count(),
        "scheduled_at": current_time.isoformat(),
    }


def apply_data_retention_policy(
    *,
    now=None,
    access_log_retention_days: int,
    error_log_retention_days: int,
    anonymisation_grace_days: int,
) -> dict[str, int | str]:
    current_time = now or timezone.now()
    access_cutoff = current_time - timedelta(days=access_log_retention_days)
    error_cutoff = current_time - timedelta(days=error_log_retention_days)
    anonymisation_cutoff = current_time - timedelta(days=anonymisation_grace_days)

    user_ids = list(
        User.objects.filter(
            is_anonymised=False,
            deleted_at__isnull=False,
            deleted_at__lte=anonymisation_cutoff,
        ).values_list("pk", flat=True)
    )
    for user_id in user_ids:
        anonymise_deleted_user(user_id)

    access_logs = AccessLog.objects.filter(timestamp__lt=access_cutoff)
    access_deleted_count = access_logs.count()
    access_logs.delete()
    _write_system_log(
        operation="purge_access_logs",
        detail=f"deleted {access_deleted_count} rows older than {access_cutoff.isoformat()}",
    )

    error_logs = ErrorLog.objects.filter(timestamp__lt=error_cutoff)
    error_deleted_count = error_logs.count()
    error_logs.delete()
    _write_system_log(
        operation="purge_error_logs",
        detail=f"deleted {error_deleted_count} rows older than {error_cutoff.isoformat()}",
    )

    return {
        "access_logs_deleted": access_deleted_count,
        "error_logs_deleted": error_deleted_count,
        "users_anonymised": len(user_ids),
        "scheduled_at": current_time.isoformat(),
    }


def _write_system_log(*, operation: str, detail: str) -> None:
    SystemLog.objects.create(
        event=operation,
        operation=operation,
        level=SystemLog.Level.INFO,
        message=detail,
        detail=detail,
    )
