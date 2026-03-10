from rest_framework import serializers


class OpenRateQuerySerializer(serializers.Serializer):
    days = serializers.IntegerField(required=False, min_value=1, default=30)


class OpenRateMetricSerializer(serializers.Serializer):
    type = serializers.CharField()
    sent = serializers.IntegerField()
    opened = serializers.IntegerField()
    open_rate_pct = serializers.FloatField()
