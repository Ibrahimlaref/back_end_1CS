import json
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
<<<<<<< HEAD
    ForgotPasswordConfirmSerializer,
=======
    forgot_password_confirm_Serializer,
    TOTPVerifySerializer,
    TOTPSetupConfirmSerializer,
    TOTPRecoverSerializer,
>>>>>>> 51dcb10 (feat:add 2 factor authentication)
)
from apps.users.services.jwt_service import (
    generate_tokens,
    create_session,
    revoke_session,
    revoke_all_sessions,
    decode_refresh_token,
)
from apps.users.services.totp_service import (
    generate_totp_secret,
    get_totp_uri,
    generate_qr_code_base64,
    verify_totp_code,
    verify_backup_code,
    enable_2fa,
    disable_2fa,
)
from apps.users.tasks import send_email_task

import redis
from django.conf import settings as django_settings

_redis = redis.from_url(django_settings.REDIS_URL)
TOTP_PENDING_TTL = 300  # 5 minutes to complete 2FA after password check


class AuthService:
    REGISTRATION_PURPOSE = 'registration'

    # ── REGISTER ──────────────────────────────────────────────────────────────

    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        email    = serializer.validated_data['email']
        password = serializer.validated_data['password']

        existing_user = User.objects.filter(email=email).first()

        if existing_user:
            if existing_user.email_verified:
                return Response(
                    {'error': 'An account with this email already exists.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
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
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        email    = serializer.validated_data['email']
        otp_code = serializer.validated_data['otp']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'No account found with this email.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            EmailOtpVerification.verify(user, otp_code, purpose=self.REGISTRATION_PURPOSE)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        user.email_verified = True
        user.save(update_fields=['email_verified'])

        return Response({'message': 'Email verified successfully. You can now log in.'}, status=status.HTTP_200_OK)

    # ── RESEND OTP ────────────────────────────────────────────────────────────

    def resend_otp(self, request):
        serializer = ResendOtpSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
<<<<<<< HEAD
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'No account found with this email.'},
                status=status.HTTP_404_NOT_FOUND
            )

=======
        user  = User.objects.get(email=email)
>>>>>>> 51dcb10 (feat:add 2 factor authentication)
        self._send_otp(user, purpose=self.REGISTRATION_PURPOSE)

        return Response({'message': 'OTP resent. Check your email.'}, status=status.HTTP_200_OK)

    # ── LOGIN ─────────────────────────────────────────────────────────────────

    def login(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        email    = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response({'error': 'Invalid email or password.'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.email_verified:
            return Response({'error': 'Please verify your email before logging in.'}, status=status.HTTP_403_FORBIDDEN)

        # ── 2FA CHECK ─────────────────────────────────────────────────────────
        if user.totp_enabled:
            pending_key = f"2fa_pending:{user.id}"
            gym_id, role = self._resolve_role(user)
            pending_payload = json.dumps({
                'gym_id': gym_id,
                'role': role,
            })
            _redis.set(pending_key, pending_payload, ex=TOTP_PENDING_TTL)

            return Response(
                {
                    'requires_2fa': True,
                    'user_id': str(user.id),
                    'message': 'Enter your 2FA code to complete login.',
                },
                status=status.HTTP_200_OK
            )

        # No 2FA — issue tokens directly
        return self._issue_tokens(user, request)

    # ── 2FA VERIFY (complete login) ───────────────────────────────────────────

    def verify_2fa(self, request):
        serializer = TOTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        user_id = serializer.validated_data['user_id']
        code    = serializer.validated_data['code']

        # Check pending key exists in Redis
        pending_key = f"2fa_pending:{user_id}"
        pending_payload = _redis.get(pending_key)
        if not pending_payload:
            return Response(
                {'error': 'Session expired. Please log in again.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not verify_totp_code(user.totp_secret, code):
            return Response({'error': 'Invalid or expired 2FA code.'}, status=status.HTTP_401_UNAUTHORIZED)

        # Clear pending key
        _redis.delete(pending_key)
        pending_data = json.loads(pending_payload)
        gym_id = pending_data.get('gym_id')
        role = pending_data.get('role')

        return self._issue_tokens(user, request, gym_id=gym_id, role=role)

    # ── 2FA SETUP ─────────────────────────────────────────────────────────────

    def setup_2fa(self, request):
        """Step 1: Generate secret and QR code. User scans QR, then calls enable_2fa."""
        try:
            user = User.objects.get(id=request.user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        if user.totp_enabled:
            return Response({'error': '2FA is already enabled.'}, status=status.HTTP_400_BAD_REQUEST)

        secret = generate_totp_secret()
        uri    = get_totp_uri(user, secret)
        qr     = generate_qr_code_base64(uri)

        # Store secret temporarily in Redis until user confirms setup
        _redis.set(f"2fa_setup:{user.id}", secret, ex=600)  # 10 minutes

        return Response(
            {
                'qr_code': f"data:image/png;base64,{qr}",
                'secret':  secret,  # for manual entry in authenticator app
                'message': 'Scan the QR code with your authenticator app, then confirm with your first code.',
            },
            status=status.HTTP_200_OK
        )

    def confirm_2fa_setup(self, request):
        """Step 2: User submits first TOTP code to confirm setup. Generates backup codes."""
        serializer = TOTPSetupConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data['code']

        try:
            user = User.objects.get(id=request.user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Retrieve temp secret from Redis
        secret = _redis.get(f"2fa_setup:{user.id}")
        if not secret:
            return Response(
                {'error': 'Setup session expired. Please start again.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        secret = secret.decode() if isinstance(secret, bytes) else secret

        if not verify_totp_code(secret, code):
            return Response({'error': 'Invalid code. Please try again.'}, status=status.HTTP_400_BAD_REQUEST)

        # Enable 2FA and generate backup codes
        backup_codes = enable_2fa(user, secret)
        _redis.delete(f"2fa_setup:{user.id}")

        return Response(
            {
                'message': '2FA enabled successfully.',
                'backup_codes': backup_codes,
                'warning': 'Save these backup codes somewhere safe. They will not be shown again.',
            },
            status=status.HTTP_200_OK
        )

    def disable_2fa_view(self, request):
        """Disable 2FA after verifying current TOTP code."""
        serializer = TOTPSetupConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=request.user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not user.totp_enabled:
            return Response({'error': '2FA is not enabled.'}, status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data['code']
        if not verify_totp_code(user.totp_secret, code):
            return Response({'error': 'Invalid 2FA code.'}, status=status.HTTP_401_UNAUTHORIZED)

        disable_2fa(user)
        return Response({'message': '2FA disabled successfully.'}, status=status.HTTP_200_OK)

    # ── 2FA RECOVERY ─────────────────────────────────────────────────────────

    def recover_2fa(self, request):
        """Login using a backup code instead of TOTP. Revokes all sessions."""
        serializer = TOTPRecoverSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        user_id     = serializer.validated_data['user_id']
        backup_code = serializer.validated_data['backup_code']

        # Check pending key exists
        pending_key = f"2fa_pending:{user_id}"
        if not _redis.exists(pending_key):
            return Response(
                {'error': 'Session expired. Please log in again.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # verify_backup_code also revokes all sessions internally
        if not verify_backup_code(user, backup_code):
            return Response({'error': 'Invalid or already used backup code.'}, status=status.HTTP_401_UNAUTHORIZED)

        _redis.delete(pending_key)

        # Issue fresh tokens
        return self._issue_tokens(user, request)

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
                pass

        response = Response({'message': 'Logout successful.'}, status=status.HTTP_200_OK)
        response.delete_cookie('refresh_token', samesite='Strict')
        return response

    # ── REFRESH TOKEN ─────────────────────────────────────────────────────────

    def refresh(self, request):
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            return Response({'error': 'No refresh token found.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            payload = decode_refresh_token(refresh_token)
            user    = User.objects.get(id=payload['user_id'])
            jti     = payload['jwt_jti']

            session = SessionLog.objects.filter(jwt_jti=jti, is_revoked=False).first()
            if not session:
                return Response({'error': 'Session revoked. Please log in again.'}, status=status.HTTP_401_UNAUTHORIZED)

            revoke_session(jti)

            role_obj = UserGymRole.objects.filter(user=user, status=UserGymRole.Status.ACTIVE).first()
            if not role_obj:
                return Response({'error': 'No active gym membership found.'}, status=status.HTTP_403_FORBIDDEN)

            tokens = generate_tokens(user, gym_id=role_obj.gym_id, role=role_obj.role)
            create_session(user, role_obj.gym_id, jti=tokens['jti'], request=request)

            response = Response({'message': 'Token refreshed.', 'access': tokens['access']}, status=status.HTTP_200_OK)
            response.set_cookie(
                key='refresh_token', value=tokens['refresh'],
                httponly=True, secure=True, samesite='Strict', max_age=60 * 60 * 24 * 7,
            )
            return response

        except jwt.ExpiredSignatureError:
            return Response({'error': 'Refresh token expired. Please log in again.'}, status=status.HTTP_401_UNAUTHORIZED)
        except (jwt.InvalidTokenError, User.DoesNotExist):
            return Response({'error': 'Invalid refresh token.'}, status=status.HTTP_401_UNAUTHORIZED)

    # ── ME ────────────────────────────────────────────────────────────────────

    def me(self, request):
        try:
            user = User.objects.get(id=request.user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            {
                'id':            str(user.id),
                'email':         user.email,
                'first_name':    user.first_name,
                'last_name':     user.last_name,
                'phone':         user.phone,
                'email_verified': user.email_verified,
                'totp_enabled':  user.totp_enabled,
            },
            status=status.HTTP_200_OK
        )
    # ── reset password ────────────────────────────────────────────────────────────────────────────
    def reset_password(self, request):
        # This method would handle password reset logic, including:
        # 1. Verifying the OTP for password reset
        # 2. Allowing the user to set a new password
        # 3. Revoking all existing sessions after password change
        serializer = ForgotPasswordConfirmSerializer(data=request.data)
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
        otp_obj = EmailOtpVerification.generate(user, purpose=purpose)
        send_email_task.delay(
            to_email=user.email,
            subject='Your verification code',
            message=f'Your OTP is: {otp_obj.otp}\nExpires in 10 minutes.',
        )

    def _resolve_role(self, user):
        role_obj = UserGymRole.objects.filter(
            user=user, status=UserGymRole.Status.ACTIVE
        ).select_related('gym').first()

<<<<<<< HEAD
    
=======
        if not role_obj:
            return None, 'onboarding'

        return str(role_obj.gym_id), role_obj.role


    def _issue_tokens(self, user, request, gym_id=None, role=None):
        """Build tokens and session after successful authentication."""
        if gym_id is None or role is None:
            gym_id, role = self._resolve_role(user)

        tokens = generate_tokens(user, gym_id=gym_id, role=role)
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
            key='refresh_token', value=tokens['refresh'],
            httponly=True, secure=True, samesite='Strict', max_age=60 * 60 * 24 * 7,
        )
        return response
>>>>>>> 51dcb10 (feat:add 2 factor authentication)
