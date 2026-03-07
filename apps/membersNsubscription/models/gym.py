import uuid
from django.db import models


class Gym(models.Model):
    """
    apps/membersandsubscriptions/models/gym.py

    The top-level tenant entity. Every single gym-scoped model in this
    app has a ForeignKey pointing to this table.

    slug is UNIQUE — used in URLs and JWT claims to identify a gym
    without exposing the UUID (e.g. /gyms/fitzone-algiers/).

    timezone is used for scheduling: course start_time/end_time are
    stored as TIMESTAMPTZ (UTC) and displayed in the gym's local timezone.

    currency is the default for MembershipPlan.currency in this gym.

    is_active = False → gym is suspended/closed. Every view that calls
    get_object_or_404(Gym, id=gym_id, is_active=True) will return 404
    for inactive gyms, effectively locking out all access.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100, unique=True)
    address = models.TextField(blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    country = models.CharField(max_length=3, blank=True, default="")   # ISO 3166-1 alpha-3
    phone = models.CharField(max_length=30, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    logo_url = models.URLField(blank=True, default="")
    timezone = models.CharField(
        max_length=64,
        default="Africa/Algiers",
        help_text="IANA timezone name, e.g. 'Africa/Algiers', 'Europe/Paris'.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.slug})"