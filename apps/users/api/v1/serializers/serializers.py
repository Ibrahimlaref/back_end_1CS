import re
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


# ─── AUTH SERIALIZERS ─────────────────────────────────────────────────────────

class UserRegistrationSerializer(serializers.ModelSerializer):
    email            = serializers.EmailField(validators=[])
    password         = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model  = User
        fields = ['email', 'password', 'password_confirm', 'first_name', 'last_name', 'phone']

    def validate_email(self, value):
        return value.lower().strip()

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class EmailOtpVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp   = serializers.CharField(min_length=6, max_length=6)

    def validate_email(self, value):
        return value.lower().strip()

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP must be a 6-digit number.")
        return value


class ResendOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()

    """def validate_email(self, value):
        value = value.lower().strip()
        user  = User.objects.filter(email=value).first()
        if not user:
            raise serializers.ValidationError("No account found with this email.")
        if user.email_verified:
            raise serializers.ValidationError("This email is already verified.")
        return value"""


class UserLoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        return value.lower().strip()


class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh     = serializers.CharField()
    all_devices = serializers.BooleanField(default=False)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower().strip()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token            = serializers.CharField()
    password         = serializers.CharField(min_length=8, write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs


# ─── 2FA SERIALIZERS ──────────────────────────────────────────────────────────

class TOTPVerifySerializer(serializers.Serializer):
    """Used during login to submit the 6-digit TOTP code."""
    user_id = serializers.UUIDField()
    code    = serializers.CharField(min_length=6, max_length=6)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Code must be 6 digits.")
        return value


class TOTPSetupConfirmSerializer(serializers.Serializer):
    """Used to confirm 2FA setup or disable 2FA — requires current TOTP code."""
    code = serializers.CharField(min_length=6, max_length=6)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Code must be 6 digits.")
        return value


class TOTPRecoverSerializer(serializers.Serializer):
    """Used during login to recover access via a backup code."""
    user_id     = serializers.UUIDField()
    backup_code = serializers.CharField()

    def validate_backup_code(self, value):
        return value.strip().upper()


# ─── PROFILE SERIALIZERS ──────────────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model       = User
        fields      = ['id', 'email', 'first_name', 'last_name']
        read_only_fields = fields


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'phone', 'date_of_birth', 'photo_url',
            'email_verified', 'totp_enabled', 'created_at',
        ]
        read_only_fields = fields


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'phone', 'date_of_birth', 'photo_url']

    def validate_phone(self, value):
        if value and not re.match(r'^\+?[\d\s\-]{7,20}$', value):
            raise serializers.ValidationError("Enter a valid phone number.")
        return value


class PasswordChangeSerializer(serializers.Serializer):
    current_password     = serializers.CharField(write_only=True)
    new_password         = serializers.CharField(min_length=8, write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'New passwords do not match.'})
        return attrs

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
<<<<<<< HEAD
        return value

class ForgotPasswordConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password = serializers.CharField(min_length=8, write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)
    otp = serializers.CharField(min_length=6, max_length=6)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Passwords do not match.'})
        return attrs
=======
        return value
>>>>>>> e8e0f09 (feat:add 2 factor authentication)
