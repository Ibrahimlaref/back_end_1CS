from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.gyms.models import Gym
from apps.membersNsubscription.models import Product
from apps.membersNsubscription.api.v1.serializers.products import ProductSerializer
from apps.membersNsubscription.api.v1.permissions import IsGymAdmin, IsActiveMember


class ProductListCreateView(APIView):
    """
    GET  /gyms/{gym_id}/products/   → list active products (any active member)
    POST /gyms/{gym_id}/products/   → create product (admin only)
    US-077 — Manage Gym Shop Products.
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsGymAdmin()]
        return [IsAuthenticated(), IsActiveMember()]

    def get(self, request, gym_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)
        products = Product.objects.filter(gym=gym, is_active=True).order_by("name")
        return Response(ProductSerializer(products, many=True).data)

    def post(self, request, gym_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)
        serializer = ProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save(gym=gym)
        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)


class ProductDetailView(APIView):
    """
    GET    /gyms/{gym_id}/products/{product_id}/
    PATCH  /gyms/{gym_id}/products/{product_id}/   (admin only)
    DELETE /gyms/{gym_id}/products/{product_id}/   (admin only — soft delete)
    """

    def get_permissions(self):
        if self.request.method in ("PATCH", "DELETE"):
            return [IsAuthenticated(), IsGymAdmin()]
        return [IsAuthenticated(), IsActiveMember()]

    def _get(self, gym_id, product_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)
        return get_object_or_404(Product, id=product_id, gym=gym)

    def get(self, request, gym_id, product_id):
        return Response(ProductSerializer(self._get(gym_id, product_id)).data)

    def patch(self, request, gym_id, product_id):
        product = self._get(gym_id, product_id)
        serializer = ProductSerializer(product, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(ProductSerializer(serializer.save()).data)

    def delete(self, request, gym_id, product_id):
        product = self._get(gym_id, product_id)
        product.is_active = False
        product.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)
