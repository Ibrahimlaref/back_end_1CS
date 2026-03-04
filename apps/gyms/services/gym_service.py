import logging
from django.db import transaction
from django.db import connection

from gyms.models.gym import Gym, PlatformOwnership, AuditLog
from gyms.tasks import dispatch_welcome_email

logger = logging.getLogger(__name__)


class GymProvisioningError(Exception):
    """Raised when gym provisioning fails at the service layer."""
    pass


class RLSVerificationError(GymProvisioningError):
    """Raised when RLS policies are not active after gym creation."""
    pass


def _verify_rls_active(gym: Gym) -> None:
    """
    AC-3: Verify RLS policies are active on the gyms table post-creation.
    Queries pg_class to confirm row security is enabled.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT relrowsecurity
            FROM   pg_class
            WHERE  relname = %s
            """,
            [Gym._meta.db_table],
        )
        row = cursor.fetchone()

    if not row or not row[0]:
        raise RLSVerificationError(
            f"RLS is NOT active on table '{Gym._meta.db_table}'. "
            "Provisioning aborted to preserve tenant isolation."
        )


def provision_gym(
    *,
    name: str,
    slug: str,
    owner_user,
    role: str = "owner",
    address: str = "",
    city: str = "",
    country: str = "",
    phone: str = "",
    email: str = "",
    logo_url: str = "",
    timezone: str = "UTC",
    ip_address: str | None = None,
    user_agent: str = "",
) -> Gym:
    """
    AC-1: Atomically creates Gym + PlatformOwnership.
    AC-3: Verifies RLS is active post-creation.
    AC-4: Triggers Celery welcome email on commit.
    AC-5: Creates AuditLog entry.

    Returns the newly created Gym instance.
    Raises GymProvisioningError / RLSVerificationError on failure.
    """

    with transaction.atomic():

        # ── 1. Create Gym ────────────────────────────────────────────
        gym = Gym.objects.create(
            name=name,
            slug=slug,
            address=address,
            city=city,
            country=country,
            phone=phone,
            email=email,
            logo_url=logo_url,
            timezone=timezone,
        )
        logger.info("Gym created: %s (slug=%s)", gym.id, gym.slug)

        # ── 2. Create PlatformOwnership atomically ───────────────────
        PlatformOwnership.objects.create(
            user=owner_user,
            gym=gym,
            role=role,
        )
        logger.info("PlatformOwnership created: user=%s → gym=%s", owner_user.id, gym.id)

        # ── 3. Verify RLS is active (AC-3) ───────────────────────────
        _verify_rls_active(gym)

        # ── 4. Write AuditLog (AC-5) ─────────────────────────────────
        AuditLog.objects.create(
            gym=gym,
            actor=owner_user,
            target_id=gym.id,
            target_table=Gym._meta.db_table,
            action=AuditLog.Action.CREATE,
            new_values={
                "name":     gym.name,
                "slug":     gym.slug,
                "timezone": gym.timezone,
                "owner":    str(owner_user.id),
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        logger.info("AuditLog entry created for gym=%s", gym.id)

        # ── 5. Dispatch Celery welcome email on commit (AC-4) ─────────
        # on_commit ensures the task fires ONLY after the transaction
        # commits successfully — never on rollback.
        transaction.on_commit(
            lambda: dispatch_welcome_email.delay(
                gym_id=str(gym.id),
                owner_email=owner_user.email,
                owner_name=getattr(owner_user, "full_name", owner_user.email),
                gym_name=gym.name,
            )
        )

    return gym
