from rest_framework.permissions import BasePermission
from apps.membersNsubscription.models.gym_role  import UserGymRole


def _gym_id(view):
    """All gym-scoped URLs use /gyms/{gym_id}/... — extract from kwargs."""
    return view.kwargs.get("gym_id")


class IsGymAdmin(BasePermission):
    """role='admin' + status='active' in the gym from the URL."""
    message = "You must be a gym administrator to perform this action."

    def has_permission(self, request, view):
        gym_id = _gym_id(view)
        if not gym_id or not request.user.is_authenticated:
            return False
        return UserGymRole.objects.filter(
            gym_id=gym_id, user=request.user,
            role="admin", status="active",
        ).exists()


class IsCoach(BasePermission):
    """role in ['coach','admin'] + status='active' in the gym from the URL."""
    message = "You must be a coach or admin in this gym."

    def has_permission(self, request, view):
        gym_id = _gym_id(view)
        if not gym_id or not request.user.is_authenticated:
            return False
        return UserGymRole.objects.filter(
            gym_id=gym_id, user=request.user,
            role__in=["coach", "admin"], status="active",
        ).exists()


class IsActiveMember(BasePermission):
    """Any role + status='active' in the gym from the URL."""
    message = "You must be an active member of this gym."

    def has_permission(self, request, view):
        gym_id = _gym_id(view)
        if not gym_id or not request.user.is_authenticated:
            return False
        return UserGymRole.objects.filter(
            gym_id=gym_id, user=request.user,
            status="active",
        ).exists()