from rest_framework.response import Response
from rest_framework import status

from apps.users.models.user import User, MemberProfile, CoachProfile
from apps.users.services.jwt_service import revoke_all_sessions


class UserService:

    # ── GET PROFILE ───────────────────────────────────────────────────────────

    def get_profile(self, request):
        """
        Returns profile based on role from JWT.
        - member → MemberProfile
        - coach  → CoachProfile
        - admin  → basic user info only

        user_id, gym_id, role all come from JWT via JWTAuthMiddleware.
        TenantMiddleware + RLS already filters by gym_id at DB level.
        """
        try:
            user = User.objects.get(id=request.user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Base user data — same for all roles
        data = {
            'id':             str(user.id),
            'email':          user.email,
            'first_name':     user.first_name,
            'last_name':      user.last_name,
            'phone':          user.phone,
            'date_of_birth':  str(user.date_of_birth) if user.date_of_birth else None,
            'photo_url':      user.photo_url,
            'email_verified': user.email_verified,
            'role':           request.role,
            'gym_id':         str(request.gym_id),
        }

        role = request.role

        # ── MEMBER ────────────────────────────────────────────────────────
        if role == 'member':
            profile = MemberProfile.objects.filter(
                user=user,
                gym_id=request.gym_id   # tenant filter + RLS double safety
            ).first()

            if profile:
                data['member_profile'] = {
                    'height_cm':         str(profile.height_cm) if profile.height_cm else None,
                    'weight_kg':         str(profile.weight_kg) if profile.weight_kg else None,
                    'fitness_goal':      profile.fitness_goal,
                    'medical_notes':     profile.medical_notes,
                    'emergency_contact': profile.emergency_contact,
                    'warning_count':     profile.warning_count,
                    'suspended_until':   str(profile.suspended_until) if profile.suspended_until else None,
                }
            else:
                data['member_profile'] = None

        # ── COACH ─────────────────────────────────────────────────────────
        elif role == 'coach':
            profile = CoachProfile.objects.filter(
                user=user,
                gym_id=request.gym_id   # tenant filter + RLS double safety
            ).first()

            if profile:
                data['coach_profile'] = {
                    'specialties':      profile.specialties,
                    'biography':        profile.biography,
                    'experience_years': profile.experience_years,
                    'is_active':        profile.is_active,
                }
            else:
                data['coach_profile'] = None

        return Response(data, status=status.HTTP_200_OK)

    # ── UPDATE PROFILE ────────────────────────────────────────────────────────

    def update_profile(self, request):
        """
        Updates MemberProfile or CoachProfile based on role from JWT.
        Never touches the User table — that is update_account_info().

        user_id, gym_id, role all come from JWT via JWTAuthMiddleware.
        TenantMiddleware + RLS already filters by gym_id at DB level.
        """
        try:
            user = User.objects.get(id=request.user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        role = request.role

        # ── MEMBER ────────────────────────────────────────────────────────
        if role == 'member':
            profile = MemberProfile.objects.filter(
                user=user,
                gym_id=request.gym_id
            ).first()

            if not profile:
                return Response(
                    {'error': 'Member profile not found.'},
                    status=status.HTTP_404_NOT_FOUND
                )

            allowed_fields = [
                'height_cm',
                'weight_kg',
                'fitness_goal',
                'medical_notes',
                'emergency_contact',
            ]

            updated_fields = self._apply_updates(profile, allowed_fields, request.data)

            if not updated_fields:
                return Response(
                    {'error': 'No valid fields provided.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            profile.save(update_fields=updated_fields)

            return Response(
                {'message': 'Member profile updated successfully.'},
                status=status.HTTP_200_OK
            )

        # ── COACH ─────────────────────────────────────────────────────────
        elif role == 'coach':
            profile = CoachProfile.objects.filter(
                user=user,
                gym_id=request.gym_id
            ).first()

            if not profile:
                return Response(
                    {'error': 'Coach profile not found.'},
                    status=status.HTTP_404_NOT_FOUND
                )

            allowed_fields = [
                'specialties',
                'biography',
                'experience_years',
            ]

            updated_fields = self._apply_updates(profile, allowed_fields, request.data)

            if not updated_fields:
                return Response(
                    {'error': 'No valid fields provided.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            profile.save(update_fields=updated_fields)

            return Response(
                {'message': 'Coach profile updated successfully.'},
                status=status.HTTP_200_OK
            )

        # ── ADMIN ──────────────────────────────────────────────────────────
        else:
            return Response(
                {'error': 'Profile update not available for this role.'},
                status=status.HTTP_403_FORBIDDEN
            )

    # ── UPDATE ACCOUNT INFO ───────────────────────────────────────────────────

    def update_account_info(self, request):
        """
        Updates User table fields only — name, phone, date_of_birth, photo_url.
        Available to all roles.
        NOT for profile-specific fields like height, specialties etc.
        """
        try:
            user = User.objects.get(id=request.user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        allowed_fields = [
            'first_name',
            'last_name',
            'phone',
            'date_of_birth',
            'photo_url',
        ]

        updated_fields = self._apply_updates(user, allowed_fields, request.data)

        if not updated_fields:
            return Response(
                {'error': 'No valid fields provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.save(update_fields=updated_fields)

        return Response(
            {'message': 'Account info updated successfully.'},
            status=status.HTTP_200_OK
        )

    # ── CHANGE PASSWORD ───────────────────────────────────────────────────────

    def change_password(self, request):
        """
        Authenticated user changes their own password.
        Revokes all sessions after change — forces re-login on all devices.
        user_id comes from JWT via JWTAuthMiddleware.
        """
        current_password     = request.data.get('current_password')
        new_password         = request.data.get('new_password')
        new_password_confirm = request.data.get('new_password_confirm')

        if not all([current_password, new_password, new_password_confirm]):
            return Response(
                {'error': 'current_password, new_password and new_password_confirm are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password != new_password_confirm:
            return Response(
                {'error': 'New passwords do not match.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=request.user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not user.check_password(current_password):
            return Response(
                {'error': 'Current password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if current_password == new_password:
            return Response(
                {'error': 'New password must be different from current password.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save(update_fields=['password'])

        # Revoke all sessions — security best practice after password change
        revoke_all_sessions(user)

        return Response(
            {'message': 'Password changed successfully. Please log in again.'},
            status=status.HTTP_200_OK
        )

    # ── DELETE ACCOUNT ────────────────────────────────────────────────────────

    def delete_account(self, request):
        """
        Permanently deletes user account.
        Requires password confirmation for security.
        CASCADE automatically deletes:
        MemberProfile, CoachProfile, UserGymRole,
        SessionLog, Warning, CoachApplication, EmailOtpVerification
        """
        password = request.data.get('password')

        if not password:
            return Response(
                {'error': 'Password is required to delete your account.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=request.user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not user.check_password(password):
            return Response(
                {'error': 'Incorrect password.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # One delete — CASCADE handles everything else
        user.delete()

        return Response(
            {'message': 'Account deleted successfully.'},
            status=status.HTTP_200_OK
        )

    # ── PRIVATE HELPERS ───────────────────────────────────────────────────────

    def _apply_updates(self, instance, allowed_fields, data):
        """
        Apply only the allowed fields from data to instance.
        Returns list of updated field names.
        """
        updated_fields = []
        for field in allowed_fields:
            if field in data:
                setattr(instance, field, data[field])
                updated_fields.append(field)
        return updated_fields