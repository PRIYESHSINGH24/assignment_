from rest_framework import serializers
from django.db import transaction
from bookings.models import Booking
from payments.models import Payment, PaymentStatusChoices


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payment details."""

    booking_id = serializers.IntegerField(read_only=True)
    test_name = serializers.CharField(source='booking.test.name', read_only=True)
    centre_name = serializers.CharField(source='booking.centre.name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'booking_id', 'test_name', 'centre_name',
            'amount', 'status', 'external_transaction_id',
            'reason', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'amount', 'status', 'external_transaction_id',
            'reason', 'created_at', 'updated_at'
        ]


class PaymentCreateSerializer(serializers.Serializer):
    """Serializer for creating payments."""

    booking_id = serializers.IntegerField()
    idempotency_key = serializers.CharField(required=False, allow_blank=True)

    def validate_booking_id(self, value):
        """Validate that the booking exists and belongs to the user."""
        try:
            booking = Booking.objects.get(id=value)
        except Booking.DoesNotExist:
            raise serializers.ValidationError('Booking not found.')

        # Ensure the booking belongs to the authenticated user
        if booking.user != self.context['request'].user:
            raise serializers.ValidationError('You do not have permission to pay for this booking.')

        return value

    @transaction.atomic
    def create(self, validated_data):
        """Create or retrieve a payment with idempotency."""
        booking_id = validated_data['booking_id']
        booking = Booking.objects.get(id=booking_id)
        idempotency_key = validated_data.get('idempotency_key')

        # Try to get an existing payment with the same idempotency key
        if idempotency_key:
            try:
                payment = Payment.objects.get(idempotency_key=idempotency_key)
                return payment
            except Payment.DoesNotExist:
                pass

        # Check if a payment already exists for this booking
        try:
            payment = Payment.objects.get(booking=booking)
            # If it exists and has the same idempotency key, return it
            if idempotency_key and str(payment.idempotency_key) == idempotency_key:
                return payment
            # Otherwise, raise an error—a booking can only have one payment
            raise serializers.ValidationError('A payment already exists for this booking.')
        except Payment.DoesNotExist:
            pass

        # Create a new payment
        payment = Payment.objects.create(
            booking=booking,
            amount=booking.amount,
            idempotency_key=idempotency_key or Payment._meta.get_field('idempotency_key').default(),
            status=PaymentStatusChoices.PENDING
        )
        return payment

    def to_representation(self, instance):
        """Return the payment using the detail serializer."""
        return PaymentSerializer(instance).data