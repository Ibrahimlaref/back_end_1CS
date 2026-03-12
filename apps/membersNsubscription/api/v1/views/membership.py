from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.users.models.user import User
from apps.gyms.models import Gym
from apps.membersNsubscription.models import UserGymRole, MemberProfile
from apps.membersNsubscription.api.v1.serializers.membership import (
    JoinGymSerializer,
    UserGymRoleSerializer,
    MemberProfileSerializer,
)


class JoinGymView(APIView):

    @extend_schema(
        request=JoinGymSerializer,
        responses={
            201: OpenApiResponse(description='Successfully joined the gym.'),
            200: OpenApiResponse(description='Already a member of this gym.'),
            404: OpenApiResponse(description='Gym not found.'),
        },
        description='Join a gym as a member. Optionally provide health profile data.'
    )
    @transaction.atomic
    def post(self, request, gym_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)

        try:
            user = User.objects.get(id=request.user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # ── Idempotency check ────────────────────────────────────────────────
        existing_role = UserGymRole.objects.filter(
            gym=gym, user=user
        ).first()

        if existing_role:
            profile = MemberProfile.objects.filter(gym=gym, user=user).first()
            return Response(
                {
                    'detail': 'You are already a member of this gym.',
                    'role':    UserGymRoleSerializer(existing_role).data,
                    'profile': MemberProfileSerializer(profile).data if profile else None,
                },
                status=status.HTTP_200_OK,
            )

        # ── Validate optional health fields ──────────────────────────────────
        serializer = JoinGymSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # ── Create UserGymRole ───────────────────────────────────────────────
        role = UserGymRole.objects.create(
            gym=gym,
            user=user,
            role='member',
            status='active',
        )

        # ── Create MemberProfile ─────────────────────────────────────────────
        profile = MemberProfile.objects.create(
            gym=gym,
            user=user,
            height_cm=data.get('height_cm'),
            weight_kg=data.get('weight_kg'),
            fitness_goal=data.get('fitness_goal', ''),
            medical_notes=data.get('medical_notes', ''),
            emergency_contact=data.get('emergency_contact', ''),
        )

        # ── Welcome notification (async, non-blocking) ───────────────────────
        try:
            from apps.notifications.tasks.dispatch import send_welcome_notification
            send_welcome_notification.delay(
                user_id=str(user.id),
                gym_id=str(gym.id),
            )
        except Exception:
            pass

        return Response(
            {
                'detail': 'Successfully joined the gym.',
                'role':    UserGymRoleSerializer(role).data,
                'profile': MemberProfileSerializer(profile).data,
            },
            status=status.HTTP_201_CREATED,
        )
