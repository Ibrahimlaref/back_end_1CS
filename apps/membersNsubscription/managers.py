from django.db import models


class ActiveMemberManager(models.Manager):
    """
    Default manager for UserGymRole — filters to active members only.
    Usage: UserGymRole.active.filter(gym=gym)
    """
    def get_queryset(self):
        return super().get_queryset().filter(status="active")


class ActivePlanManager(models.Manager):
    """
    Default manager for MembershipPlan — filters to active plans only.
    Usage: MembershipPlan.active.filter(gym=gym)
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class ActiveProductManager(models.Manager):
    """
    Default manager for Product — filters to active (non-soft-deleted) products.
    Usage: Product.active.filter(gym=gym)
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)