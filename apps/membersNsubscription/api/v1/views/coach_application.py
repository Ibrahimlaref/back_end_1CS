from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.users.models.user import CoachApplication, User
from apps.gyms.models import Gym
from apps.membersNsubscription.api.v1.serializers.coach_application import (
    CoachApplicationSubmitSerializer,
    CoachApplicationResponseSerializer,
)


class CoachApplicationView(APIView):
    """
    POST   /gyms/<gym_id>/coach-applications/   — submit application
    DELETE /gyms/<gym_id>/coach-applications/<application_id>/  — withdraw
    """

    def post(self, request, gym_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)

        try:
            user = User.objects.get(id=request.user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # AC-6: already accepted → 409
        already_accepted = CoachApplication.objects.filter(
            gym=gym,
            user=user,
            status=CoachApplication.Status.ACCEPTED,
        ).exists()

        if already_accepted:
            return Response(
                {'error': 'You are already an accepted coach at this gym.'},
                status=status.HTTP_409_CONFLICT,
            )

        # AC-2: PARTIAL UNIQUE — block duplicate pending application
        pending_exists = CoachApplication.objects.filter(
            gym=gym,
            user=user,
            status=CoachApplication.Status.PENDING,
        ).exists()

        if pending_exists:
            return Response(
                {'error': 'You already have a pending application for this gym.'},
                status=status.HTTP_409_CONFLICT,
            )

        # AC-5: withdrawn applicants can reapply — no block needed, falls through

        serializer = CoachApplicationSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        # AC-1: create application with status=pending
        application = CoachApplication.objects.create(
            gym=gym,
            user=user,
            status=CoachApplication.Status.PENDING,
            cover_letter=serializer.validated_data.get('cover_letter', ''),
        )

        # AC-3: notify gym admins via email + in-app (async via Celery)
        self._notify_admins(gym, user, application)

        return Response(
            {
                'message': 'Application submitted successfully.',
                'application': CoachApplicationResponseSerializer(application).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request, gym_id, application_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)

        try:
            user = User.objects.get(id=request.user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # AC-4: applicant can withdraw — must own the application and it must be pending
        application = CoachApplication.objects.filter(
            id=application_id,
            gym=gym,
            user=user,
            status=CoachApplication.Status.PENDING,
        ).first()

        if not application:
            return Response(
                {'error': 'No pending application found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        application.status = CoachApplication.Status.WITHDRAWN
        application.save(update_fields=['status'])

        return Response(
            {'message': 'Application withdrawn successfully.'},
            status=status.HTTP_200_OK,
        )

    # ── PRIVATE ───────────────────────────────────────────────────────────────

    @staticmethod
    def _notify_admins(gym, applicant: User, application: CoachApplication):
        """Fire email + in-app notification to all active admins of the gym."""
        try:
            from apps.users.models.user import UserGymRole
            from apps.notifications.services import NotificationDispatcher
            from apps.notifications.models import NotificationLog

            admins = UserGymRole.objects.filter(
                gym=gym,
                role=UserGymRole.Role.ADMIN,
                status=UserGymRole.Status.ACTIVE,
            ).select_related('user')

            title   = 'New Coach Application'
            message = (
                f"{applicant.first_name} {applicant.last_name} ({applicant.email}) "
                f"has applied to become a coach at {gym.name}."
            )

            for admin_role in admins:
                NotificationDispatcher.dispatch(
                    gym=gym,
                    user=admin_role.user,
                    notif_type='general',
                    channels=[
                        NotificationLog.Channel.IN_APP,
                        NotificationLog.Channel.EMAIL,
                    ],
                    title=title,
                    message=message,
                )
        except Exception:
            # Never let a notification failure roll back the application creation
            pass
