import random
from django.db import models
from django.utils import timezone
from datetime import timedelta


class EmailOtpVerification(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='otps')
    otp = models.CharField(max_length=6)
    purpose = models.CharField(max_length=50)  # 'registration', 'password_reset', 'email_change'
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired

    @classmethod
    def generate(cls, user, purpose):
        # Invalidate all previous OTPs for this user and purpose
        cls.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)

        otp_code = str(random.randint(100000, 999999))

        return cls.objects.create(
            user=user,
            otp=otp_code,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

    @classmethod
    def verify(cls, user, otp_code, purpose):
        try:
            otp_obj = cls.objects.get(
                user=user,
                otp=otp_code,
                purpose=purpose,
                is_used=False,
            )
        except cls.DoesNotExist:
            return False

        if otp_obj.is_expired:
            return False

        otp_obj.is_used = True
        otp_obj.save()
        return True
