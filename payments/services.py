from django.db import transaction, IntegrityError
from django.utils import timezone
from django.core.exceptions import ValidationError
from payments.models import Payment, WebhookEvent, PaymentStatusChoices
from payments.exceptions import WebhookProcessingError, PaymentNotFound
from bookings.models import Booking, BookingStatusChoices
import logging

logger = logging.getLogger(__name__)


class PaymentWebhookService:
    """Service for processing payment webhooks idempotently."""

    @staticmethod
    @transaction.atomic
    def process_webhook(event_id, payment_id, event_type, payload):
        """
        Process a payment webhook event idempotently.

        Args:
            event_id: Unique event ID from payment gateway
            payment_id: ID of the payment
            event_type: 'payment.success' or 'payment.failed'
            payload: Original webhook payload

        Returns:
            WebhookEvent: The processed webhook event

        Raises:
            WebhookProcessingError: If processing fails
        """

        try:
            # Try to create a new webhook event record
            # If event_id already exists, the unique constraint will raise IntegrityError
            webhook_event = WebhookEvent.objects.create(
                event_id=event_id,
                payment_id=payment_id,
                event_type=event_type,
                payload=payload,
                status='PENDING'
            )
        except IntegrityError:
            # Event already exists—this is a duplicate delivery
            webhook_event = WebhookEvent.objects.get(event_id=event_id)

            # Return cached result regardless of status to prevent duplicate processing
            if webhook_event.status == 'COMPLETED':
                logger.info(f"Duplicate webhook event {event_id} already processed.")
                return webhook_event

            if webhook_event.status == 'FAILED':
                logger.warning(f"Duplicate webhook event {event_id} previously failed.")
                raise WebhookProcessingError(f"Event {event_id} failed previously.")

            if webhook_event.status == 'PENDING':
                logger.warning(f"Duplicate webhook event {event_id} is still being processed.")
                raise WebhookProcessingError(f"Event {event_id} is still being processed. Please retry.")

        try:
            # Lock the payment row to prevent concurrent updates
            try:
                payment = Payment.objects.select_for_update().get(id=payment_id)
            except Payment.DoesNotExist:
                raise PaymentNotFound(f"Payment {payment_id} not found.")

            # Validate payment exists and is in a valid state
            if payment.status != PaymentStatusChoices.PENDING:
                raise WebhookProcessingError(
                    f"Payment {payment_id} is in {payment.status} status, "
                    f"cannot process webhook for {event_type}."
                )

            # Process based on event type
            if event_type == 'payment.success':
                PaymentWebhookService._handle_success(payment, webhook_event)

            elif event_type == 'payment.failed':
                reason = payload.get('reason', 'Payment failed')
                PaymentWebhookService._handle_failure(payment, webhook_event, reason)

            else:
                raise WebhookProcessingError(f"Unknown event type: {event_type}")

            # Mark webhook event as completed
            webhook_event.status = 'COMPLETED'
            webhook_event.processed_at = timezone.now()
            webhook_event.save()

            logger.info(f"Webhook event {event_id} processed successfully.")
            return webhook_event

        except (ValidationError, WebhookProcessingError) as e:
            webhook_event.status = 'FAILED'
            webhook_event.processed_at = timezone.now()
            webhook_event.payload['error'] = str(e)
            webhook_event.save()
            logger.error(f"Webhook event {event_id} failed: {e}")
            raise WebhookProcessingError(str(e))

    @staticmethod
    def _handle_success(payment, webhook_event):
        """Handle a payment.success event."""
        external_txn_id = webhook_event.payload.get('transaction_id', f'WEBHOOK_{webhook_event.event_id}')

        payment.mark_success(external_txn_id)

        # Update booking to CONFIRMED
        booking = payment.booking
        if booking.status != BookingStatusChoices.PENDING:
            raise ValidationError(
                f"Booking {booking.id} is in {booking.status} status, cannot confirm."
            )

        booking.status = BookingStatusChoices.CONFIRMED
        booking.save()

    @staticmethod
    def _handle_failure(payment, webhook_event, reason):
        """Handle a payment.failed event."""
        payment.mark_failed(reason)