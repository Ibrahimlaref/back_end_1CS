from django.core.cache import cache
from django.db import connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        db_status = "ok"
        redis_status = "ok"

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            db_status = "error"

        try:
            cache.get("__health__")
        except Exception:
            redis_status = "error"

        overall_status = "ok" if db_status == "ok" and redis_status == "ok" else "error"
        http_status = status.HTTP_200_OK if overall_status == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(
            {
                "status": overall_status,
                "db": db_status,
                "redis": redis_status,
            },
            status=http_status,
        )
