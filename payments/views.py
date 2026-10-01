from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.core.exceptions import ValidationError

from payments.models import Payment, PaymentStatusChoices
from payments.serializers import PaymentCreateSerializer, PaymentSerializer
from payments.services import PaymentWebhookService
from payments.exceptions import WebhookProcessingError, PaymentNotFound
from bookings.models import Booking, BookingStatusChoices

import uuid


class PaymentCreateView(APIView):
    """Create a payment for a booking."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Create a payment."""
        serializer = PaymentCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            payment = serializer.save()
            return Response(
                PaymentSerializer(payment).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentProcessView(APIView):
    """Simulate payment processing (success or failure)."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """Process a payment (simulate success or failure)."""
        payment_id = request.data.get('payment_id')
        payment_status = request.data.get('status', 'SUCCESS')  # SUCCESS or FAILED
        reason = request.data.get('reason', '')

        if not payment_id:
            return Response(
                {'detail': 'payment_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            payment = Payment.objects.select_for_update().get(id=payment_id)
        except Payment.DoesNotExist:
            return Response(
                {'detail': 'Payment not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Ensure the payment belongs to the authenticated user
        if payment.booking.user != request.user:
            return Response(
                {'detail': 'You do not have permission to process this payment.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check payment status
        if payment.status != PaymentStatusChoices.PENDING:
            return Response(
                {'detail': f'Cannot process a {payment.status} payment.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if payment_status == 'SUCCESS':
                # Mark payment as successful
                external_txn_id = f'TXN_{payment.id}_{hash(str(payment.idempotency_key))}'
                payment.mark_success(external_txn_id)

                # Update booking status to CONFIRMED
                booking = payment.booking
                booking.status = BookingStatusChoices.CONFIRMED
                booking.save()

            elif payment_status == 'FAILED':
                # Mark payment as failed
                payment.mark_failed(reason or 'Payment processing failed.')

            else:
                return Response(
                    {'detail': f'Invalid status: {payment_status}. Must be SUCCESS or FAILED.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(
                PaymentSerializer(payment).data,
                status=status.HTTP_200_OK
            )

        except ValidationError as e:
            return Response(
                {'detail': str(e.message)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentWebhookView(APIView):
    """Receive and process payment webhooks."""
    permission_classes = []  # Allow unauthenticated webhook requests (from payment gateway)
    authentication_classes = []

    def post(self, request):
        """
        Process a payment webhook.

        Expected payload:
        {
            "event_id": "evt_123456",
            "payment_id": 1,
            "event_type": "payment.success" | "payment.failed",
            "reason": "optional reason for failures",
            "transaction_id": "optional transaction ID"
        }
        """
        event_id = request.data.get('event_id')
        payment_id = request.data.get('payment_id')
        event_type = request.data.get('event_type')

        # Validate required fields
        if not all([event_id, payment_id, event_type]):
            return Response(
                {'detail': 'event_id, payment_id, and event_type are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            webhook_event = PaymentWebhookService.process_webhook(
                event_id=event_id,
                payment_id=payment_id,
                event_type=event_type,
                payload=request.data
            )

            return Response(
                {
                    'status': 'success',
                    'event_id': webhook_event.event_id,
                    'payment_id': webhook_event.payment.id,
                    'payment_status': webhook_event.payment.status,
                },
                status=status.HTTP_200_OK
            )

        except WebhookProcessingError as e:
            return Response(
                {
                    'status': 'error',
                    'detail': str(e),
                },
                status=status.HTTP_400_BAD_REQUEST
            )