from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.membersNsubscription.models.gym import Gym
from apps.membersNsubscription.models.equipment  import Equipment, MaintenanceReport
from apps.membersNsubscription.api.v1.serializers.equipment import (
    EquipmentSerializer,
    EquipmentAdminSerializer,
    MaintenanceReportSerializer,
    ReportMalfunctionSerializer,
    UpdateReportSerializer,
)
from apps.membersNsubscription.api.v1.permissions import IsGymAdmin, IsActiveMember

ALLOWED_TRANSITIONS = {
    "open":         ["acknowledged", "in_progress"],
    "acknowledged": ["in_progress", "resolved"],
    "in_progress":  ["resolved"],
    "resolved":     [],
}


class EquipmentListCreateView(APIView):
    """
    GET  /gyms/{gym_id}/equipment/   → list all equipment (any active member)
    POST /gyms/{gym_id}/equipment/   → register equipment (admin only)
    US-072 — Register and Manage Equipment.
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsGymAdmin()]
        return [IsAuthenticated(), IsActiveMember()]

    def get(self, request, gym_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)
        items = Equipment.objects.filter(gym=gym).order_by("name")
        return Response(EquipmentSerializer(items, many=True).data)

    def post(self, request, gym_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)
        serializer = EquipmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save(gym=gym)
        return Response(EquipmentSerializer(item).data, status=status.HTTP_201_CREATED)


class EquipmentDetailView(APIView):
    """
    GET    /gyms/{gym_id}/equipment/{equipment_id}/
    PATCH  /gyms/{gym_id}/equipment/{equipment_id}/   (admin only)
    DELETE /gyms/{gym_id}/equipment/{equipment_id}/   (admin — decommission)
    """

    def get_permissions(self):
        if self.request.method in ("PATCH", "DELETE"):
            return [IsAuthenticated(), IsGymAdmin()]
        return [IsAuthenticated(), IsActiveMember()]

    def _get(self, gym_id, equipment_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)
        return get_object_or_404(Equipment, id=equipment_id, gym=gym)

    def get(self, request, gym_id, equipment_id):
        return Response(EquipmentSerializer(self._get(gym_id, equipment_id)).data)

    def patch(self, request, gym_id, equipment_id):
        item = self._get(gym_id, equipment_id)
        serializer = EquipmentAdminSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(EquipmentSerializer(serializer.save()).data)

    def delete(self, request, gym_id, equipment_id):
        item = self._get(gym_id, equipment_id)
        item.status = "decommissioned"
        item.save(update_fields=["status"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReportMalfunctionView(APIView):
    """
    POST /gyms/{gym_id}/equipment/{equipment_id}/report/
    US-073 — Report Equipment Malfunction.

    Duplicate guard: one active report per equipment at a time → 409.
    Atomic: report creation + equipment.status='under_maintenance'.
    """

    permission_classes = [IsAuthenticated, IsActiveMember]

    @transaction.atomic
    def post(self, request, gym_id, equipment_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)
        item = get_object_or_404(Equipment, id=equipment_id, gym=gym)

        if item.status == "decommissioned":
            return Response(
                {"detail": "Cannot file a report on decommissioned equipment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        active_report = MaintenanceReport.objects.filter(
            equipment=item,
            status__in=["open", "acknowledged", "in_progress"],
        ).first()
        if active_report:
            return Response(
                {
                    "detail": "An active maintenance report already exists for this equipment.",
                    "existing_report": MaintenanceReportSerializer(active_report).data,
                },
                status=status.HTTP_409_CONFLICT,
            )

        serializer = ReportMalfunctionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report = MaintenanceReport.objects.create(
            gym=gym,
            equipment=item,
            reported_by=request.user,
            description=serializer.validated_data["description"],
            status="open",
        )
        item.status = "under_maintenance"
        item.save(update_fields=["status"])

        return Response(MaintenanceReportSerializer(report).data, status=status.HTTP_201_CREATED)


class ManageMaintenanceReportView(APIView):
    """
    GET   /gyms/{gym_id}/equipment/{equipment_id}/reports/
    PATCH /gyms/{gym_id}/equipment/{equipment_id}/reports/{report_id}/
    US-074 — Manage Maintenance Workflow.

    On resolve (atomic):
      report.resolved_at = now()
      equipment.status = 'operational'
      equipment.last_maintenance = now()
      Celery notification → reporter
    """

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), IsGymAdmin()]
        return [IsAuthenticated(), IsActiveMember()]

    def get(self, request, gym_id, equipment_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)
        item = get_object_or_404(Equipment, id=equipment_id, gym=gym)
        reports = MaintenanceReport.objects.filter(equipment=item).order_by("-created_at")
        return Response(MaintenanceReportSerializer(reports, many=True).data)

    @transaction.atomic
    def patch(self, request, gym_id, equipment_id, report_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)
        item = get_object_or_404(Equipment, id=equipment_id, gym=gym)
        report = get_object_or_404(MaintenanceReport, id=report_id, equipment=item, gym=gym)

        if report.status == "resolved":
            return Response(
                {"detail": "This report is already resolved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = UpdateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        new_status = data["new_status"]

        allowed = ALLOWED_TRANSITIONS.get(report.status, [])
        if new_status not in allowed:
            return Response(
                {
                    "detail": f"Cannot transition '{report.status}' → '{new_status}'.",
                    "allowed_next": allowed,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if data.get("assigned_to_id"):
            from django.contrib.auth import get_user_model
            report.assigned_to = get_object_or_404(
                get_user_model(), id=data["assigned_to_id"]
            )

        report.status = new_status

        if new_status == "resolved":
            report.resolved_at = timezone.now()
            item.status = "operational"
            item.last_maintenance = timezone.now()
            item.save(update_fields=["status", "last_maintenance"])

            try:
                from apps.membersNsubscription.tasks import send_maintenance_resolved
                send_maintenance_resolved.delay(
                    report_id=str(report.id),
                    reporter_id=str(report.reported_by_id),
                    equipment_name=item.name,
                )
            except Exception:
                pass

        report.save()
        return Response(MaintenanceReportSerializer(report).data)