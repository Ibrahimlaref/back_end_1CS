from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from apps.users.services.auth_service import AuthService
from apps.users.api.v1.serializers.serializers import (
    UserRegistrationSerializer,
    EmailOtpVerificationSerializer,
    UserLoginSerializer,forgot_password_confirm_Serializer
)

service = AuthService()


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


@extend_schema(request=EmailOtpVerificationSerializer)
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
 
@extend_schema(request=forgot_password_confirm_Serializer)
@api_view(['PATCH'])
@permission_classes([AllowAny])
def reset_password_view(request):
    return service.reset_password(request)