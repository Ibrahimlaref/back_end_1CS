from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from apps.users.services.auth_service import AuthService
from apps.users.api.v1.serializers.serializers import (
    UserRegistrationSerializer,
    EmailOtpVerificationSerializer,
    ResendOtpSerializer,
    UserLoginSerializer,
    ForgotPasswordConfirmSerializer,
    UserLoginSerializer,ForgotPasswordConfirmSerializer,
    UserLoginSerializer,
    TOTPVerifySerializer,
    TOTPSetupConfirmSerializer,
    TOTPRecoverSerializer,
)

service = AuthService()


# ─── STANDARD AUTH ────────────────────────────────────────────────────────────

@extend_schema(request=UserRegistrationSerializer)
@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    return service.register(request)


@extend_schema(request=EmailOtpVerificationSerializer)
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp_view(request):
    return service.verify_otp(request)


@extend_schema(request=ResendOtpSerializer)
@api_view(['POST'])
@permission_classes([AllowAny])
def resend_otp_view(request):
    return service.resend_otp(request)


@extend_schema(request=UserLoginSerializer)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    return service.login(request)


@extend_schema(request=None)
@api_view(['POST'])
def logout_view(request):
    return service.logout(request)


@extend_schema(request=None)
@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh_view(request):
    return service.refresh(request)
 
@extend_schema(request=ForgotPasswordConfirmSerializer)
@api_view(['PATCH'])
@permission_classes([AllowAny])
def reset_password_view(request):
    return service.reset_password(request)


# ─── 2FA VIEWS ────────────────────────────────────────────────────────────────

@extend_schema(request=TOTPVerifySerializer)
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_2fa_view(request):
    """Step 2 of login when 2FA is enabled. Submit 6-digit TOTP code."""
    return service.verify_2fa(request)


@extend_schema(request=None)
@api_view(['GET'])
@permission_classes([AllowAny])
def setup_2fa_view(request):
    """Get QR code and secret to set up 2FA in an authenticator app."""
    return service.setup_2fa(request)


@extend_schema(request=TOTPSetupConfirmSerializer)
@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_2fa_view(request):
    """Confirm 2FA setup by submitting the first TOTP code. Returns backup codes."""
    return service.confirm_2fa_setup(request)


@extend_schema(request=TOTPSetupConfirmSerializer)
@api_view(['POST'])
@permission_classes([AllowAny])
def disable_2fa_view(request):
    """Disable 2FA by submitting current TOTP code."""
    return service.disable_2fa_view(request)


@extend_schema(request=TOTPRecoverSerializer)
@api_view(['POST'])
@permission_classes([AllowAny])
def recover_2fa_view(request):
    """Login using a backup code when TOTP device is unavailable. Revokes all sessions."""
    return service.recover_2fa(request)
