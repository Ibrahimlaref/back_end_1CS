import jwt
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status

from apps.users.models.user import User, UserGymRole, SessionLog
from apps.users.models.otp import EmailOtpVerification
from apps.users.api.v1.serializers.serializers import (
    UserRegistrationSerializer,
    EmailOtpVerificationSerializer,
    ResendOtpSerializer,
    UserLoginSerializer,
    forgot_password_confirm_Serializer
)
from apps.users.services.jwt_service import (
    generate_tokens,
    create_session,
    revoke_session,
    revoke_all_sessions,
    decode_refresh_token,
)
from apps.core.tasks import apply_async_with_correlation
from apps.users.tasks import send_email_task


class AuthService:
    REGISTRATION_PURPOSE = 'registration'

    # ── REGISTER ──────────────────────────────────────────────────────────────

    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        email    = serializer.validated_data['email']
        password = serializer.validated_data['password']

        # Check if user already exists
        existing_user = User.objects.filter(email=email).first()
        print(existing_user)

        if existing_user:
            # Already verified — block re-registration
            if existing_user.email_verified:
            
                return Response(
                    {'error': 'An account with this email already exists.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Not verified — update their info and resend OTP
            existing_user.first_name = serializer.validated_data.get('first_name', existing_user.first_name)
            existing_user.last_name  = serializer.validated_data.get('last_name',  existing_user.last_name)
            """existing_user.phone      = serializer.validated_data.get('phone',      existing_user.phone)"""
            existing_user.set_password(password)
            existing_user.save()
            self._send_otp(existing_user, purpose='registration')
            return Response(
                {'message': 'Account updated. A new OTP has been sent to your email.'},
                status=status.HTTP_200_OK
            )

        # New user — create
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=serializer.validated_data.get('first_name', ''),
            last_name=serializer.validated_data.get('last_name', ''),
            
        )
        self._send_otp(user, purpose='registration')

        return Response(
            {'message': 'Registration successful. Check your email for the OTP.'},
            status=status.HTTP_201_CREATED
        )
    # ── VERIFY OTP ────────────────────────────────────────────────────────────

    def verify_otp(self, request):
        serializer = EmailOtpVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        email    = serializer.validated_data['email']
        otp_code = serializer.validated_data['otp']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'No account found with this email.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            EmailOtpVerification.verify(
                user,
                otp_code,
                purpose=self.REGISTRATION_PURPOSE,
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mark user as verified
        user.email_verified = True
        user.save(update_fields=['email_verified'])

        return Response(
            {'message': 'Email verified successfully. You can now log in.'},
            status=status.HTTP_200_OK
        )

    # ── RESEND OTP ────────────────────────────────────────────────────────────

    def resend_otp(self, request):
        serializer = ResendOtpSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        email = serializer.validated_data['email']
        user  = User.objects.get(email=email)

        self._send_otp(user, purpose=self.REGISTRATION_PURPOSE)

        return Response(
            {'message': 'OTP resent. Check your email.'},
            status=status.HTTP_200_OK
        )

    # ── LOGIN ─────────────────────────────────────────────────────────────────

    def login(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        email    = serializer.validated_data['email']
        password = serializer.validated_data['password']

        # Check credentials
        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response(
                {'error': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Check email verified
        if not user.email_verified:
            return Response(
                {'error': 'Please verify your email before logging in.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get active gym role (optional)
        role_obj = UserGymRole.objects.filter(
            user=user,
            status=UserGymRole.Status.ACTIVE
        ).select_related('gym').first()

        if role_obj:
            gym_id = role_obj.gym_id
            role   = role_obj.role
        else:
            gym_id = None
            role   = 'onboarding'

        # Generate tokens
        tokens = generate_tokens(user, gym_id=gym_id, role=role)

        # Save session
        create_session(user, gym_id, jti=tokens['jti'], request=request)

        response = Response(
            {
                'message': 'Login successful.',
                'access':  tokens['access'],
                'user': {
                    'id':     str(user.id),
                    'email':  user.email,
                    'role':   role,
                    'gym_id': str(gym_id) if gym_id else None,
                }
            },
            status=status.HTTP_200_OK
        )

        response.set_cookie(
            key='refresh_token',
            value=tokens['refresh'],
            httponly=True,
            secure=True,
            samesite='Strict',
            max_age=60 * 60 * 24 * 7,
        )

        return response

    # ── LOGOUT ────────────────────────────────────────────────────────────────

    def logout(self, request):
        refresh_token = request.COOKIES.get('refresh_token')

        if refresh_token:
            try:
                payload     = decode_refresh_token(refresh_token)
                jti         = payload.get('jwt_jti')
                all_devices = request.data.get('all_devices', False)

                if all_devices:
                    user = User.objects.get(id=payload['user_id'])
                    revoke_all_sessions(user)
                else:
                    revoke_session(jti)

            except Exception:
                # Token invalid or expired — still logout
                pass

        response = Response(
            {'message': 'Logout successful.'},
            status=status.HTTP_200_OK
        )
        response.delete_cookie('refresh_token', samesite='Strict')
        return response

    # ── REFRESH TOKEN ─────────────────────────────────────────────────────────

    def refresh(self, request):
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            return Response(
                {'error': 'No refresh token found.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            payload = decode_refresh_token(refresh_token)
            user    = User.objects.get(id=payload['user_id'])
            jti     = payload['jwt_jti']

            # Check session not revoked
            session = SessionLog.objects.filter(
                jwt_jti=jti,
                is_revoked=False
            ).first()

            if not session:
                return Response(
                    {'error': 'Session revoked. Please log in again.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Revoke old session
            revoke_session(jti)

            # Get current gym role
            role_obj = UserGymRole.objects.filter(
                user=user,
                status=UserGymRole.Status.ACTIVE
            ).first()

            if not role_obj:
                return Response(
                    {'error': 'No active gym membership found.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Issue new tokens
            tokens = generate_tokens(user, gym_id=role_obj.gym_id, role=role_obj.role)
            create_session(user, role_obj.gym_id, jti=tokens['jti'], request=request)

            response = Response(
                {
                    'message': 'Token refreshed.',
                    'access':  tokens['access'],
                },
                status=status.HTTP_200_OK
            )

            response.set_cookie(
                key='refresh_token',
                value=tokens['refresh'],
                httponly=True,
                secure=True,
                samesite='Strict',
                max_age=60 * 60 * 24 * 7,
            )
            return response

        except jwt.ExpiredSignatureError:
            return Response(
                {'error': 'Refresh token expired. Please log in again.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except (jwt.InvalidTokenError, User.DoesNotExist):
            return Response(
                {'error': 'Invalid refresh token.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

    # ── ME ────────────────────────────────────────────────────────────────────

    def me(self, request):
        try:
            user = User.objects.get(id=request.user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                'id':           str(user.id),
                'email':        user.email,
                'first_name':   user.first_name,
                'last_name':    user.last_name,
                'phone':        user.phone,
                'email_verified': user.email_verified,
            },
            status=status.HTTP_200_OK
        )
    # ── reset password ────────────────────────────────────────────────────────────────────────────
    def reset_password(self, request):
        # This method would handle password reset logic, including:
        # 1. Verifying the OTP for password reset
        # 2. Allowing the user to set a new password
        # 3. Revoking all existing sessions after password change
        serializer = forgot_password_confirm_Serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        email    = serializer.validated_data['email']
        
        
        user = User.objects.filter(email=email).first()
        if not user:
            return Response(
                {'error': 'No account found with this email.'},
                status=status.HTTP_404_NOT_FOUND
            )
        otp_code = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']
        if not otp_code or not new_password:
            return Response(
                {'error': 'OTP and new password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            EmailOtpVerification.verify(
                user,
                otp_code,
                purpose='password_reset',
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.set_password(new_password)
        user.save()
        revoke_all_sessions(user)
        return Response(
            {'message': 'Password reset successful. Please log in with your new password.'},
            status=status.HTTP_200_OK
        )
    


    # ── PRIVATE HELPERS ───────────────────────────────────────────────────────

    def _send_otp(self, user, purpose):
        """Generate OTP, save to DB, send email via Celery."""
        otp_obj = EmailOtpVerification.generate(user, purpose=purpose)

        apply_async_with_correlation(
            send_email_task,
            kwargs={
                'to_email': user.email,
                'subject': 'Your verification code',
                'message': f'Your OTP is: {otp_obj.otp}\nExpires in 10 minutes.',
            },
        )


    
