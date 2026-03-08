from rest_framework import serializers
from apps.membersNsubscription.models import Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "gym", "name", "description", "price",
                  "stock_quantity", "is_active", "created_at"]
        read_only_fields = ["id", "gym", "created_at"]

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

    def validate_stock_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock quantity cannot be negative.")
        return value
