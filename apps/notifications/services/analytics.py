from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, F, Q
from django.utils import timezone

from apps.notifications.models import NotificationLog


def open_rate_by_type(days: int = 30) -> list[dict]:
    cutoff = timezone.now() - timedelta(days=days)
    rows = (
        NotificationLog.objects.filter(
            channel=NotificationLog.Channel.EMAIL,
            timestamp__gte=cutoff,
        )
        .values(type=F("notification__type"))
        .annotate(
            sent=Count(
                "id",
                filter=Q(
                    status__in=[
                        NotificationLog.Status.SENT,
                        NotificationLog.Status.DELIVERED,
                        NotificationLog.Status.OPENED,
                    ]
                ),
            ),
            opened=Count("id", filter=Q(status=NotificationLog.Status.OPENED)),
        )
        .order_by("type")
    )

    metrics: list[dict] = []
    for row in rows:
        sent = row["sent"]
        opened = row["opened"]
        open_rate_pct = round((opened / sent) * 100, 2) if sent else 0.0
        metrics.append(
            {
                "type": row["type"],
                "sent": sent,
                "opened": opened,
                "open_rate_pct": open_rate_pct,
            }
        )
    return metrics
