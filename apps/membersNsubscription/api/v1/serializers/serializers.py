from rest_framework import serializers

class AccessScanSerializer(serializers.Serializer):
    gym_id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    entry_type = serializers.ChoiceField(choices=["entry", "exit"])
    method = serializers.ChoiceField(choices=["nfc", "qr", "manual"])
    device_id = serializers.CharField(required=False, default="")
