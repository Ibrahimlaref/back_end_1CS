from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.membersNsubscription.models import Gym, Room
from apps.membersNsubscription.api.v1.serializers.rooms import RoomSerializer
from apps.membersNsubscription.api.v1.permissions import IsGymAdmin, IsActiveMember


class RoomListCreateView(APIView):
    """
    GET  /gyms/{gym_id}/rooms/   → list active rooms (any active member)
    POST /gyms/{gym_id}/rooms/   → create room (admin only)
    US-044 — Manage Gym Rooms.
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsGymAdmin()]
        return [IsAuthenticated(), IsActiveMember()]

    def get(self, request, gym_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)
        rooms = Room.objects.filter(gym=gym, is_active=True).order_by("name")
        return Response(RoomSerializer(rooms, many=True).data)

    def post(self, request, gym_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)
        serializer = RoomSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room = serializer.save(gym=gym)
        return Response(RoomSerializer(room).data, status=status.HTTP_201_CREATED)


class RoomDetailView(APIView):
    """
    GET    /gyms/{gym_id}/rooms/{room_id}/
    PATCH  /gyms/{gym_id}/rooms/{room_id}/   (admin only)
    DELETE /gyms/{gym_id}/rooms/{room_id}/   (admin only — soft deactivate)
    """

    def get_permissions(self):
        if self.request.method in ("PATCH", "DELETE"):
            return [IsAuthenticated(), IsGymAdmin()]
        return [IsAuthenticated(), IsActiveMember()]

    def _get_room(self, gym_id, room_id):
        gym = get_object_or_404(Gym, id=gym_id, is_active=True)
        return get_object_or_404(Room, id=room_id, gym=gym)

    def get(self, request, gym_id, room_id):
        return Response(RoomSerializer(self._get_room(gym_id, room_id)).data)

    def patch(self, request, gym_id, room_id):
        room = self._get_room(gym_id, room_id)
        serializer = RoomSerializer(room, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(RoomSerializer(serializer.save()).data)

    def delete(self, request, gym_id, room_id):
        room = self._get_room(gym_id, room_id)
        room.is_active = False
        room.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)
