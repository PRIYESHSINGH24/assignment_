from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response


class RootAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({
            'message': 'Healthcare API',
            'version': '1.0',
            'status': 'Running',
            'endpoints': {
                'auth': '/api/v1/auth/',
                'diagnostics': '/api/v1/diagnostics/',
                'bookings': '/api/v1/bookings/',
                'payments': '/api/v1/payments/',
                'docs': '/api/schema/swagger-ui/',
            }
        }, status=status.HTTP_200_OK)