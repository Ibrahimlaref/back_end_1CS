from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.users.models.user import User
from apps.gyms.models import Gym, AuditLog
from apps.membersNsubscription.models import UserGymRole
from apps.membersNsubscription.api.v1.serializers.membership_status import (
    MembershipStatusSerializer,
    UserGymRoleStatusResponseSerializer,
)


class MembershipStatusView(APIView):
    """
    PATCH /gyms/<gym_id>/members/<user_id>/status/

    Admin-only. Deactivate or reactivate a member's gym access.

    AC-1: Sets UserGymRole.status = inactive/active, deactivated_at = NOW()/None
    AC-2: Login flow already checks status=active — inactive members are blocked
    AC-3: Data preserved — only status field is touched, nothing deleted
    AC-4: Reactivation restores status=active, clears deactivated_at
    AC-5: AuditLog entry created for both actions
    """

    @extend_schema(
        request=MembershipStatusSerializer,
        responses={
            200: UserGymRoleStatusResponseSerializer,
            400: OpenApiResponse(description='Invalid action or member already in that state.'),
            403: OpenApiResponse(description='Not an admin of this gym.'),
            404: OpenApiResponse(description='Gym or member role not found.'),
        },
        description=(
            'Admin only. Deactivate or reactivate a member\'s access to this gym. '
            'Data is preserved — only the role status changes. '
            'Deactivated members cannot log in to this gym context.'
        )
    )
    def patch(self, request, gym_id, user_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)

        # ── Admin check ───────────────────────────────────────────────────────
        if getattr(request, 'role', None) != 'admin':
            return Response(
                {'error': 'Only gym admins can change member status.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ── Validate request body ─────────────────────────────────────────────
        serializer = MembershipStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        action = serializer.validated_data['action']
        reason = serializer.validated_data.get('reason', '')

        # ── Fetch the target member's role ────────────────────────────────────
        role_obj = UserGymRole.objects.filter(
            gym=gym,
            user_id=user_id,
        ).first()

        if not role_obj:
            return Response(
                {'error': 'This user has no role at this gym.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── Fetch admin user for AuditLog ─────────────────────────────────────
        try:
            admin_user = User.objects.get(id=request.user_id)
        except User.DoesNotExist:
            return Response({'error': 'Admin user not found.'}, status=status.HTTP_404_NOT_FOUND)

        # ── Apply action ──────────────────────────────────────────────────────
        if action == 'deactivate':
            # AC-1
            if role_obj.status == UserGymRole.STATUS_CHOICES[2][0]:  # 'inactive'
                return Response(
                    {'error': 'Member is already inactive.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            old_status = role_obj.status
            role_obj.status         = 'inactive'
            role_obj.deactivated_at = timezone.now()
            role_obj.save(update_fields=['status', 'deactivated_at'])

            audit_action = AuditLog.Action.UPDATE
            new_values   = {'status': 'inactive', 'deactivated_at': str(role_obj.deactivated_at)}

        elif action == 'reactivate':
            # AC-4
            if role_obj.status == 'active':
                return Response(
                    {'error': 'Member is already active.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            old_status = role_obj.status
            role_obj.status         = 'active'
            role_obj.deactivated_at = None
            role_obj.save(update_fields=['status', 'deactivated_at'])

            audit_action = AuditLog.Action.UPDATE
            new_values   = {'status': 'active', 'deactivated_at': None}

        # ── AC-5: AuditLog ────────────────────────────────────────────────────
        AuditLog.objects.create(
            gym          = gym,
            actor        = admin_user,
            target_id    = role_obj.id,
            target_table = 'user_gym_roles',
            action       = audit_action,
            old_values   = {'status': old_status, 'reason': reason},
            new_values   = new_values,
            ip_address   = request.META.get('REMOTE_ADDR'),
            user_agent   = request.META.get('HTTP_USER_AGENT', ''),
        )

        return Response(
            {
                'message': f'Member successfully {action}d.',
                'role': UserGymRoleStatusResponseSerializer({
                    'id':             role_obj.id,
                    'user_id':        role_obj.user_id,
                    'gym_id':         gym.id,
                    'role':           role_obj.role,
                    'status':         role_obj.status,
                    'deactivated_at': role_obj.deactivated_at,
                    'joined_at':      role_obj.joined_at,
                }).data,
            },
            status=status.HTTP_200_OK,
        )
