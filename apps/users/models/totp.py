import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class TOTPBackupCode(models.Model):
    """Single-use backup code for 2FA recovery.

    8 codes are generated when the user enables 2FA.
    Each code can only be used once.
    Using any backup code revokes all sessions (security measure).
    Codes are stored hashed — never in plain text.
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='backup_codes')
    code_hash  = models.TextField()  # bcrypt hash of the plain code
    used       = models.BooleanField(default=False)
    used_at    = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'totp_backup_codes'

    def __str__(self):
        return f"BackupCode: {self.user} ({'used' if self.used else 'available'})"