import django_filters
from ..models.models import AuditLog

class AuditLogFilter(django_filters.FilterSet):
    date_from = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    date_to   = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = AuditLog
        fields = [
            "actor",
            "target_table",
            "action",
            "gym",
            "date_from",
            "date_to",
        ]