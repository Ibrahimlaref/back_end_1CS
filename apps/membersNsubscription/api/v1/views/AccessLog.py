from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..serializers.AccessLog import AccessScanSerializer
from ....services.AccessLog import handle_gym_scan

class GymScanView(APIView):
    def post (self ,request):
        serializer=AccessScanSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        result=handle_gym_scan(
            gym=serializer.validated_data['gym'],
            user=serializer.validated_data['user'],
            entry_type=serializer.validated_data["entry_type"],
            method=serializer.validated_data["method"],
            device_id=serializer.validated_data.get("device_id","")
        )

        if not result['allowed']:
            return Response(
                {'detail':result['reason']},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return Response({"detail":"access granted"}, status=status.HTTP_200_OK)