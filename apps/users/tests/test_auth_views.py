from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient
from unittest.mock import patch


class AuthViewsTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.base_url = "/api/users/v1/auth/"

    def test_register_view_delegates_to_service(self):
        payload = {
            "email": "test@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
            "first_name": "Test",
            "last_name": "User",
            "phone": "+1234567890",
        }
        with patch(
            "apps.users.api.v1.views.auth_views.service.register",
            return_value=Response({"message": "ok"}, status=status.HTTP_201_CREATED),
        ) as mocked_service:
            response = self.client.post(f"{self.base_url}register/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mocked_service.assert_called_once()

    def test_verify_otp_view_delegates_to_service(self):
        payload = {"email": "test@example.com", "otp": "123456"}
        with patch(
            "apps.users.api.v1.views.auth_views.service.verify_otp",
            return_value=Response({"message": "ok"}, status=status.HTTP_200_OK),
        ) as mocked_service:
            response = self.client.post(f"{self.base_url}verify-otp/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_service.assert_called_once()

    def test_resend_otp_view_delegates_to_service(self):
        payload = {"email": "test@example.com"}
        with patch(
            "apps.users.api.v1.views.auth_views.service.resend_otp",
            return_value=Response({"message": "ok"}, status=status.HTTP_200_OK),
        ) as mocked_service:
            response = self.client.post(f"{self.base_url}resend-otp/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_service.assert_called_once()

    def test_login_view_delegates_to_service(self):
        payload = {"email": "test@example.com", "password": "StrongPass123!"}
        with patch(
            "apps.users.api.v1.views.auth_views.service.login",
            return_value=Response({"message": "ok"}, status=status.HTTP_200_OK),
        ) as mocked_service:
            response = self.client.post(f"{self.base_url}login/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_service.assert_called_once()

    def test_token_refresh_view_delegates_to_service(self):
        with patch(
            "apps.users.api.v1.views.auth_views.service.refresh",
            return_value=Response({"message": "ok"}, status=status.HTTP_200_OK),
        ) as mocked_service:
            response = self.client.post(f"{self.base_url}refresh/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_service.assert_called_once()

    def test_logout_view_requires_authentication(self):
        with patch(
            "apps.users.api.v1.views.auth_views.service.logout",
            return_value=Response({"message": "ok"}, status=status.HTTP_200_OK),
        ) as mocked_service:
            response = self.client.post(f"{self.base_url}logout/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        mocked_service.assert_not_called()
