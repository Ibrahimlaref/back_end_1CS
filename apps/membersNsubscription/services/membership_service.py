from django.db import transaction

from apps.membersNsubscription.models.gym_role import UserGymRole
from apps.membersNsubscription.models.member_profile import MemberProfile


class MembershipService:
    """
    Business logic for joining a gym (US-023).
    Extracted from the view so it can be reused by signals, management
    commands, or other services without going through HTTP.
    """

    @staticmethod
    @transaction.atomic
    def join_gym(user, gym, health_data: dict = None) -> tuple:
        """
        Creates UserGymRole + MemberProfile in a single atomic transaction.

        Returns:
            (role: UserGymRole, profile: MemberProfile, created: bool)
            created=False means the user was already a member (idempotent).
        """
        health_data = health_data or {}

        # Idempotency check
        existing_role = UserGymRole.objects.filter(gym=gym, user=user).first()
        if existing_role:
            profile = MemberProfile.objects.filter(gym=gym, user=user).first()
            return existing_role, profile, False

        role = UserGymRole.objects.create(
            gym=gym,
            user=user,
            role="member",
            status="active",
        )

        profile = MemberProfile.objects.create(
            gym=gym,
            user=user,
            height_cm=health_data.get("height_cm"),
            weight_kg=health_data.get("weight_kg"),
            fitness_goal=health_data.get("fitness_goal", ""),
            medical_notes=health_data.get("medical_notes", ""),
            emergency_contact=health_data.get("emergency_contact", ""),
        )

        return role, profile, True