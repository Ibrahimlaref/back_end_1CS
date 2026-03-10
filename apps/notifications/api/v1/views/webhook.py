from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.services import InvalidEmailWebhookPayload, process_email_delivery_webhook


@method_decorator(csrf_exempt, name="dispatch")
class EmailDeliveryWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(request=None, responses={200: None})
    def post(self, request):
        try:
            updated_logs = process_email_delivery_webhook(request.data)
        except InvalidEmailWebhookPayload as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"updated": len(updated_logs)}, status=status.HTTP_200_OK)
