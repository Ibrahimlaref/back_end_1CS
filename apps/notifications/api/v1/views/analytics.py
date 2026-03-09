from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.api.v1.serializers import OpenRateMetricSerializer, OpenRateQuerySerializer
from apps.notifications.services import open_rate_by_type


class NotificationOpenRateAnalyticsView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        parameters=[OpenRateQuerySerializer],
        responses=OpenRateMetricSerializer(many=True),
    )
    def get(self, request):
        serializer = OpenRateQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        metrics = open_rate_by_type(days=serializer.validated_data["days"])
        return Response(OpenRateMetricSerializer(metrics, many=True).data)
