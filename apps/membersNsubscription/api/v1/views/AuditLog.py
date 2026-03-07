from rest_framework import generics
from rest_framework.permissions import IsAdminUser
from ....models.models import AuditLog
from ..serializers.AuditLog import AuditLogSerializer
from ....filters.AuditLog import AuditLogFilter

class AuditLogListView(generics.ListAPIView):
    permission_classes=[IsAdminUser]
    serializer_class=AuditLogSerializer
    filterset_class=AuditLogFilter
    ordering=["-created_at"]

    def get_queryset(self):
        return AuditLog.objects.select_related("actor","gym").all()