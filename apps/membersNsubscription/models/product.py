import uuid
from django.db import models


class Product(models.Model):
    """
    A gym shop product (supplements, gear, apparel, etc.).

    price          → current price; changing it never affects existing
                     OrderItem rows (unit_price snapshotted at order time, US-078).
    stock_quantity → decremented atomically via SELECT FOR UPDATE (US-078).
    is_active      → soft-delete; preserves OrderItem FK history.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gym = models.ForeignKey(
        "membersandsubscriptions.Gym",
        on_delete=models.CASCADE,
        related_name="products",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["gym", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} (stock:{self.stock_quantity}) @ {self.gym}"