from rest_framework.decorators import api_view
from apps.users.services.user_service import UserService

service = UserService()


@api_view(['GET'])
def me_view(request):
    return service.get_profile(request)


@api_view(['PATCH'])
def update_profile_view(request):
    return service.update_profile(request)


@api_view(['PATCH'])
def update_account_view(request):
    return service.update_account_info(request)


@api_view(['POST'])
def change_password_view(request):
    return service.change_password(request)


@api_view(['DELETE'])
def delete_account_view(request):
    return service.delete_account(request)