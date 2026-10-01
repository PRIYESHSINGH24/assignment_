from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.core.exceptions import ValidationError

from bookings.models import Booking, BookingStatusChoices
from bookings.serializers import (
    BookingSerializer,
    BookingCreateSerializer,
    BookingCancelSerializer,
)
from common.permissions import IsStaffOrReadOnly
from common.cache_utils import cache_user_queryset


class BookingViewSet(viewsets.ModelViewSet):
    """ViewSet for bookings."""

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'centre', 'test']
    ordering_fields = ['appointment_date', 'created_at']
    ordering = ['-created_at']

    @cache_user_queryset('user_bookings', timeout=300)
    def get_queryset(self):
        """Return only the user's own bookings with caching."""
        return Booking.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'create':
            return BookingCreateSerializer
        elif self.action == 'cancel':
            return BookingCancelSerializer
        return BookingSerializer

    def create(self, request, *args, **kwargs):
        """Create a new booking."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return Response(
            BookingSerializer(booking).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking."""
        booking = self.get_object()

        try:
            booking.cancel()
            return Response(
                BookingSerializer(booking).data,
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            return Response(
                {'detail': str(e.message)},
                status=status.HTTP_400_BAD_REQUEST
            )
