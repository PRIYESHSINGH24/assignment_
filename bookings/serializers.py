from rest_framework import serializers
from django.utils import timezone
from bookings.models import Booking, BookingStatusChoices
from diagnostics.models import DiagnosticCentre, DiagnosticTest, CentreTest


class BookingSerializer(serializers.ModelSerializer):
    """Serializer for booking details."""

    test_name = serializers.CharField(source='test.name', read_only=True)
    centre_name = serializers.CharField(source='centre.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'user', 'user_email', 'centre', 'centre_name',
            'test', 'test_name', 'appointment_date', 'amount',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'user_email', 'amount',
            'created_at', 'updated_at'
        ]


class BookingCreateSerializer(serializers.Serializer):
    """Serializer for creating bookings with server-calculated pricing."""

    centre_id = serializers.IntegerField()
    test_id = serializers.IntegerField()
    appointment_date = serializers.DateTimeField()

    def validate_centre_id(self, value):
        """Validate centre exists."""
        try:
            DiagnosticCentre.objects.get(id=value)
        except DiagnosticCentre.DoesNotExist:
            raise serializers.ValidationError('Diagnostic centre not found.')
        return value

    def validate_test_id(self, value):
        """Validate test exists."""
        try:
            DiagnosticTest.objects.get(id=value)
        except DiagnosticTest.DoesNotExist:
            raise serializers.ValidationError('Diagnostic test not found.')
        return value

    def validate_appointment_date(self, value):
        """Validate appointment date is in the future."""
        if value <= timezone.now():
            raise serializers.ValidationError('Appointment date must be in the future.')
        return value

    def validate(self, data):
        """Validate that the test is offered at the centre."""
        centre = DiagnosticCentre.objects.get(id=data['centre_id'])
        test = DiagnosticTest.objects.get(id=data['test_id'])

        try:
            centre_test = CentreTest.objects.get(centre=centre, test=test, available=True)
        except CentreTest.DoesNotExist:
            raise serializers.ValidationError(
                'This test is not available at the selected centre.'
            )

        data['centre'] = centre
        data['test'] = test
        data['price'] = centre_test.price
        return data

    def create(self, validated_data):
        """Create the booking."""
        booking = Booking.objects.create(
            user=self.context['request'].user,
            centre=validated_data['centre'],
            test=validated_data['test'],
            appointment_date=validated_data['appointment_date'],
            amount=validated_data['price'],
            status=BookingStatusChoices.PENDING
        )
        return booking

    def to_representation(self, instance):
        """Return the created booking using the detail serializer."""
        return BookingSerializer(instance).data


class BookingCancelSerializer(serializers.Serializer):
    """Serializer for cancelling a booking."""

    def save(self, booking):
        """Cancel the booking."""
        booking.cancel()
        return booking

    def to_representation(self, instance):
        """Return the updated booking."""
        return BookingSerializer(instance).data