from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.membersNsubscription.models import Gym, MembershipPlan
from apps.membersNsubscription.api.v1.serializers.plans import MembershipPlanSerializer
from apps.membersNsubscription.api.v1.permissions import IsGymAdmin, IsActiveMember


class MembershipPlanListCreateView(APIView):
    """
    GET  /gyms/{gym_id}/plans/   → list active plans (any active member)
    POST /gyms/{gym_id}/plans/   → create plan (admin only)
    US-032 — Create Gym Membership Plans.
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsGymAdmin()]
        return [IsAuthenticated(), IsActiveMember()]

    def get(self, request, gym_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)
        plans = MembershipPlan.objects.filter(gym=gym, is_active=True).order_by("price")
        return Response(MembershipPlanSerializer(plans, many=True).data)

    def post(self, request, gym_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)
        serializer = MembershipPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.save(gym=gym)
        return Response(MembershipPlanSerializer(plan).data, status=status.HTTP_201_CREATED)


class MembershipPlanDetailView(APIView):
    """
    GET    /gyms/{gym_id}/plans/{plan_id}/
    PATCH  /gyms/{gym_id}/plans/{plan_id}/   (admin only)
    DELETE /gyms/{gym_id}/plans/{plan_id}/   (admin only — soft delete)
    """

    def get_permissions(self):
        if self.request.method in ("PATCH", "DELETE"):
            return [IsAuthenticated(), IsGymAdmin()]
        return [IsAuthenticated(), IsActiveMember()]

    def _get_plan(self, gym_id, plan_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)
        return get_object_or_404(MembershipPlan, id=plan_id, gym=gym)

    def get(self, request, gym_id, plan_id):
        return Response(MembershipPlanSerializer(self._get_plan(gym_id, plan_id)).data)

    def patch(self, request, gym_id, plan_id):
        plan = self._get_plan(gym_id, plan_id)
        serializer = MembershipPlanSerializer(plan, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(MembershipPlanSerializer(serializer.save()).data)

    def delete(self, request, gym_id, plan_id):
        plan = self._get_plan(gym_id, plan_id)
        plan.is_active = False
        plan.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)
