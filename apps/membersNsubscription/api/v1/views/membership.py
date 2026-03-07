from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.membersNsubscription.models.gym import Gym
from apps.membersNsubscription.models import UserGymRole
from apps.membersNsubscription.models.member_profile import MemberProfile
from apps.membersNsubscription.api.v1.serializers.membership import (
    JoinGymSerializer,
    UserGymRoleSerializer,
    MemberProfileSerializer,
)


class JoinGymView(APIView):
   

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, gym_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)

        # ── Idempotency check ────────────────────────────────────────────────
        existing_role = UserGymRole.objects.filter(
            gym=gym, user=request.user
        ).select_related("gym").first()

        if existing_role:
            profile = MemberProfile.objects.filter(
                gym=gym, user=request.user
            ).first()
            return Response(
                {
                    "detail": "You are already a member of this gym.",
                    "role": UserGymRoleSerializer(existing_role).data,
                    "profile": MemberProfileSerializer(profile).data if profile else None,
                },
                status=status.HTTP_200_OK,
            )

        # ── Validate optional health fields from body ────────────────────────
        serializer = JoinGymSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # ── Create UserGymRole ───────────────────────────────────────────────
        # role='member' is the only role assignable via self-join.
        # status='active' — no approval flow needed for basic membership.
        role = UserGymRole.objects.create(
            gym=gym,
            user=request.user,
            role="member",
            status="active",
        )

        # ── Create MemberProfile ─────────────────────────────────────────────
        # warning_count defaults to 0, suspended_until=None — DB defaults.
        profile = MemberProfile.objects.create(
            gym=gym,
            user=request.user,
            height_cm=data.get("height_cm"),
            weight_kg=data.get("weight_kg"),
            fitness_goal=data.get("fitness_goal", ""),
            medical_notes=data.get("medical_notes", ""),
            emergency_contact=data.get("emergency_contact", ""),
        )

        # ── Welcome notification (async, non-blocking) ───────────────────────
        try:
            from apps.notifications.tasks.dispatch import send_welcome_notification
            send_welcome_notification.delay(
                user_id=str(request.user.id),
                gym_id=str(gym.id),
            )
        except Exception:
            # Never let a notification error roll back the join transaction.
            pass

        return Response(
            {
                "detail": "Successfully joined the gym.",
                "role": UserGymRoleSerializer(role).data,
                "profile": MemberProfileSerializer(profile).data,
            },
            status=status.HTTP_201_CREATED,
        )