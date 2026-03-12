from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.users.models.user import User
from apps.gyms.models import Gym
from apps.membersNsubscription.models import MemberProfile
from apps.membersNsubscription.api.v1.serializers.member_profile import (
    MemberProfileUpdateSerializer,
    MemberProfileResponseSerializer,
    MemberProfilePublicSerializer,
)


class MyMemberProfileView(APIView):
    """
    PATCH /gyms/<gym_id>/my-profile/

    Updates the MemberProfile for the authenticated user at the given gym.

    AC-1: scoped to (gym_id, user_id) — never touches another gym's profile
    AC-2: each gym has its own independent MemberProfile row
    AC-3: height_cm and weight_kg validated as positive numerics
    AC-4: medical_notes visible only to coaches/admins of that gym
    AC-5: emergency_contact stored as free-text, no validation
    """

    @extend_schema(
        request=MemberProfileUpdateSerializer,
        responses={
            200: MemberProfileResponseSerializer,
            400: OpenApiResponse(description='Validation error.'),
            403: OpenApiResponse(description='Not a member of this gym.'),
            404: OpenApiResponse(description='Gym or profile not found.'),
        },
        description=(
            'Update your health profile at a specific gym. '
            'All fields are optional — only provided fields are updated. '
            'Each gym profile is fully independent.'
        )
    )
    def patch(self, request, gym_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)

        try:
            user = User.objects.get(id=request.user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # AC-1 + AC-2: fetch profile scoped to this exact (gym_id, user_id)
        profile = MemberProfile.objects.filter(
            gym=gym,
            user=user,
        ).first()

        if not profile:
            return Response(
                {'error': 'You do not have a member profile at this gym.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = MemberProfileUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        if not data:
            return Response(
                {'error': 'No fields provided to update.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Apply only the fields that were sent
        updated_fields = []
        for field, value in data.items():
            setattr(profile, field, value)
            updated_fields.append(field)

        profile.save(update_fields=updated_fields)

        # AC-4: medical_notes only visible to the member themselves, coaches, and admins
        role = getattr(request, 'role', None)
        if role in ('coach', 'admin') or str(request.user_id) == str(user.id):
            response_data = MemberProfileResponseSerializer(profile).data
        else:
            response_data = MemberProfilePublicSerializer(profile).data

        return Response(
            {
                'message': 'Profile updated successfully.',
                'profile': response_data,
            },
            status=status.HTTP_200_OK,
        )
