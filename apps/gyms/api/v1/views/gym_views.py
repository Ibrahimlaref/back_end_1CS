import logging
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.v1.serializers.gym_serializers import (
    GymProvisionSerializer,
    GymProvisionResponseSerializer,
)
from core.services.gym_service import provision_gym, GymProvisioningError, RLSVerificationError

logger = logging.getLogger(__name__)


class GymProvisionView(APIView):
    """
    POST /platform/gyms

    US-002: Gym Tenant Provisioning
    ─────────────────────────────────────────────────────────
    AC-1  Gym + PlatformOwnership created atomically
    AC-2  Slug validated unique + ^[a-z0-9-]+$  (serializer)
    AC-3  RLS verified active post-creation     (service)
    AC-4  Welcome email via Celery on commit     (service)
    AC-5  AuditLog entry created                (service)
    AC-6  Returns 201 with gym_id               (this view)
    """

    def post(self, request: Request) -> Response:

        # ── Validate input (AC-2) ─────────────────────────────────────
        serializer = GymProvisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # ── Extract request meta for AuditLog ─────────────────────────
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        try:
            # ── Provision (AC-1, AC-3, AC-4, AC-5) ───────────────────
            gym = provision_gym(
                **serializer.validated_data,
                owner_user=request.user,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        except RLSVerificationError as exc:
            logger.critical("RLS verification failed during provisioning: %s", exc)
            return Response(
                {"detail": "Tenant isolation could not be verified. Provisioning aborted."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        except GymProvisioningError as exc:
            logger.error("Gym provisioning error: %s", exc)
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Return 201 with gym_id (AC-6) ─────────────────────────────
        response_serializer = GymProvisionResponseSerializer(gym)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def _get_client_ip(request: Request) -> str | None:
        """Extracts real client IP, accounting for proxies."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
