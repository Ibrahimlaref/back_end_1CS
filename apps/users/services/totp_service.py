import pyotp
import qrcode
import secrets
import hashlib
import io
import base64

from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.users.models.totp import TOTPBackupCode
from apps.users.services.jwt_service import revoke_all_sessions

User = get_user_model()

# Number of backup codes to generate on 2FA setup
BACKUP_CODE_COUNT = 8


def _hash_code(plain: str) -> str:
    """SHA-256 hash a backup code for safe storage."""
    return hashlib.sha256(plain.strip().upper().encode()).hexdigest()


def generate_totp_secret() -> str:
    """Generate a new random TOTP secret key."""
    return pyotp.random_base32()


def get_totp_uri(user: User, secret: str) -> str:
    """Build the otpauth:// URI used to generate the QR code."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(
        name=user.email,
        issuer_name='FitTech',
    )


def generate_qr_code_base64(uri: str) -> str:
    """Generate a QR code image from the TOTP URI and return as base64 PNG."""
    img = qrcode.make(uri)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')


def verify_totp_code(secret: str, code: str) -> bool:
    """Verify a 6-digit TOTP code against a secret.
    
    Allows 1 window of clock drift (±30 seconds).
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def generate_backup_codes(user: User) -> list[str]:
    """Generate 8 single-use backup codes, store them hashed, return plain codes.

    Deletes any existing backup codes for the user first.
    Plain codes are returned ONCE — they are never stored in plain text.
    """
    # Remove old codes
    TOTPBackupCode.objects.filter(user=user).delete()

    plain_codes = []
    for _ in range(BACKUP_CODE_COUNT):
        # Format: XXXX-XXXX (easy to read and copy)
        plain = f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"
        plain_codes.append(plain)
        TOTPBackupCode.objects.create(
            user=user,
            code_hash=_hash_code(plain),
        )

    return plain_codes


def verify_backup_code(user: User, plain_code: str) -> bool:
    """Check if the given backup code is valid and unused.

    If valid: marks it as used, revokes all user sessions.
    Returns True if valid, False otherwise.
    """
    code_hash = _hash_code(plain_code)

    backup = TOTPBackupCode.objects.filter(
        user=user,
        code_hash=code_hash,
        used=False,
    ).first()

    if not backup:
        return False

    # Mark code as used
    backup.used = True
    backup.used_at = timezone.now()
    backup.save(update_fields=['used', 'used_at'])

    # Revoke all sessions (security: assume phone was lost)
    revoke_all_sessions(user)

    return True


def enable_2fa(user: User, secret: str) -> list[str]:
    """Finalize 2FA setup: save secret, mark enabled, generate backup codes.

    Returns plain backup codes — show these to the user once.
    """
    user.totp_secret = secret
    user.totp_enabled = True
    user.save(update_fields=['totp_secret', 'totp_enabled'])

    return generate_backup_codes(user)


def disable_2fa(user: User) -> None:
    """Disable 2FA and remove all backup codes."""
    user.totp_secret = ''
    user.totp_enabled = False
    user.save(update_fields=['totp_secret', 'totp_enabled'])
    TOTPBackupCode.objects.filter(user=user).delete()