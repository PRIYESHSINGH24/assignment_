import pytest
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from bookings.models import Booking, BookingStatusChoices
from diagnostics.models import DiagnosticCentre, DiagnosticTest, CentreTest
from payments.models import Payment, PaymentStatusChoices, WebhookEvent
from payments.services import PaymentWebhookService, WebhookProcessingError


class TestWebhookSuccess:
    """Tests for successful payment webhooks."""

    @pytest.mark.django_db
    def test_webhook_success(self, api_client, payment_ready_for_webhook):
        """Test processing a payment.success webhook."""
        data = {
            'event_id': 'evt_success_001',
            'payment_id': payment_ready_for_webhook.id,
            'event_type': 'payment.success',
            'transaction_id': 'TXN_12345'
        }
        response = api_client.post('/api/v1/payments/webhook/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'
        assert response.data['payment_status'] == 'SUCCESS'

        # Verify payment status changed
        payment = Payment.objects.get(id=payment_ready_for_webhook.id)
        assert payment.status == PaymentStatusChoices.SUCCESS

        # Verify booking status changed
        booking = payment.booking
        assert booking.status == BookingStatusChoices.CONFIRMED

    @pytest.mark.django_db
    def test_webhook_failed(self, api_client, payment_ready_for_webhook):
        """Test processing a payment.failed webhook."""
        data = {
            'event_id': 'evt_failed_001',
            'payment_id': payment_ready_for_webhook.id,
            'event_type': 'payment.failed',
            'reason': 'Insufficient funds'
        }
        response = api_client.post('/api/v1/payments/webhook/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['payment_status'] == 'FAILED'

        # Verify payment status changed
        payment = Payment.objects.get(id=payment_ready_for_webhook.id)
        assert payment.status == PaymentStatusChoices.FAILED
        assert payment.reason == 'Insufficient funds'

        # Verify booking status did not change
        booking = payment.booking
        assert booking.status == BookingStatusChoices.PENDING


class TestWebhookIdempotency:
    """Tests for webhook idempotency."""
    @pytest.mark.django_db(transaction=True)
    def test_duplicate_webhook_success(self, api_client, payment_ready_for_webhook):
        """Test that first webhook succeeds."""
        import uuid
        event_id = f'evt_idempotent_{uuid.uuid4().hex[:8]}'
        data = {
            'event_id': event_id,
            'payment_id': payment_ready_for_webhook.id,
            'event_type': 'payment.success',
            'transaction_id': 'TXN_12345'
        }

        # First webhook should succeed
        response1 = api_client.post('/api/v1/payments/webhook/', data, format='json')
        assert response1.status_code == status.HTTP_200_OK

        # Verify webhook event was created
        assert WebhookEvent.objects.filter(event_id=event_id).count() == 1

    @pytest.mark.django_db
    def test_duplicate_event_id_unique_constraint(self, api_client, payment_ready_for_webhook):
        """Test that event_id is unique in the database."""
        import uuid
        event_id = f'evt_unique_{uuid.uuid4().hex[:8]}'

        # Create first webhook event
        WebhookEvent.objects.create(
            event_id=event_id,
            payment=payment_ready_for_webhook,
            event_type='payment.success',
            status='COMPLETED'
        )

        # Verify the event was created
        assert WebhookEvent.objects.filter(event_id=event_id).count() == 1


class TestWebhookValidation:
    """Tests for webhook validation."""

    @pytest.mark.django_db
    def test_webhook_missing_event_id(self, api_client, payment_ready_for_webhook):
        """Test webhook without event_id."""
        data = {
            'payment_id': payment_ready_for_webhook.id,
            'event_type': 'payment.success'
        }
        response = api_client.post('/api/v1/payments/webhook/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'event_id' in response.data['detail']

    @pytest.mark.django_db
    def test_webhook_missing_payment_id(self, api_client):
        """Test webhook without payment_id."""
        data = {
            'event_id': 'evt_001',
            'event_type': 'payment.success'
        }
        response = api_client.post('/api/v1/payments/webhook/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_webhook_missing_event_type(self, api_client, payment_ready_for_webhook):
        """Test webhook without event_type."""
        data = {
            'event_id': 'evt_001',
            'payment_id': payment_ready_for_webhook.id
        }
        response = api_client.post('/api/v1/payments/webhook/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_webhook_invalid_payment(self, api_client):
        """Test webhook for non-existent payment."""
        import uuid
        data = {
            'event_id': f'evt_invalid_{uuid.uuid4().hex[:8]}',
            'payment_id': 9999,
            'event_type': 'payment.success'
        }
        response = api_client.post('/api/v1/payments/webhook/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_webhook_invalid_event_type(self, api_client, payment_ready_for_webhook):
        """Test webhook with invalid event_type."""
        data = {
            'event_id': 'evt_invalid_type',
            'payment_id': payment_ready_for_webhook.id,
            'event_type': 'invalid.event'
        }
        response = api_client.post('/api/v1/payments/webhook/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestWebhookStateTransitions:
    """Tests for webhook state transition validation."""

    @pytest.mark.django_db
    def test_webhook_on_already_confirmed_payment(self, api_client, booking_for_payment):
        """Test webhook for a payment that's already confirmed."""
        payment = Payment.objects.create(
            booking=booking_for_payment,
            amount='500',
            status=PaymentStatusChoices.SUCCESS  # Already successful
        )

        data = {
            'event_id': 'evt_already_confirmed',
            'payment_id': payment.id,
            'event_type': 'payment.success'
        }
        response = api_client.post('/api/v1/payments/webhook/', data, format='json')

        # Should fail because payment is already SUCCESS
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestWebhookConcurrency:
    """Tests for webhook concurrent delivery handling."""

    @pytest.mark.django_db(transaction=True)
    def test_concurrent_webhook_service_call(self, payment_ready_for_webhook):
        """Test that concurrent webhook service calls are idempotent."""
        import uuid

        event_id = f'evt_concurrent_{uuid.uuid4().hex[:8]}'

        # First call creates the webhook event and processes it
        webhook1 = PaymentWebhookService.process_webhook(
            event_id=event_id,
            payment_id=payment_ready_for_webhook.id,
            event_type='payment.success',
            payload={'transaction_id': 'TXN_123'}
        )

        assert webhook1.status == 'COMPLETED'

        # Second call (duplicate) should return the cached result
        webhook2 = PaymentWebhookService.process_webhook(
            event_id=event_id,
            payment_id=payment_ready_for_webhook.id,
            event_type='payment.success',
            payload={'transaction_id': 'TXN_123'}
        )

        # Both should be the same event
        assert webhook1.event_id == webhook2.event_id
        assert webhook1.id == webhook2.id
        assert webhook2.status == 'COMPLETED'

        # Payment should only be updated once
        payment = Payment.objects.get(id=payment_ready_for_webhook.id)
        assert payment.status == PaymentStatusChoices.SUCCESS

    @pytest.mark.django_db(transaction=True)
    def test_duplicate_webhook_during_processing(self, payment_ready_for_webhook):
        """Test that duplicate webhook arriving during processing is rejected."""
        import uuid
        from unittest.mock import patch

        event_id = f'evt_during_processing_{uuid.uuid4().hex[:8]}'

        # Simulate a webhook that is stuck in PENDING status
        WebhookEvent.objects.create(
            event_id=event_id,
            payment=payment_ready_for_webhook,
            event_type='payment.success',
            status='PENDING',
            payload={'transaction_id': 'TXN_123'}
        )

        # A duplicate webhook arriving while first is still PENDING should raise error
        with pytest.raises(WebhookProcessingError) as exc_info:
            PaymentWebhookService.process_webhook(
                event_id=event_id,
                payment_id=payment_ready_for_webhook.id,
                event_type='payment.success',
                payload={'transaction_id': 'TXN_123'}
            )

        assert "still being processed" in str(exc_info.value)

    @pytest.mark.django_db(transaction=True)
    def test_duplicate_webhook_api_endpoint(self, api_client, payment_ready_for_webhook):
        """Test webhook idempotency through API endpoint."""
        import uuid

        event_id = f'evt_api_duplicate_{uuid.uuid4().hex[:8]}'
        data = {
            'event_id': event_id,
            'payment_id': payment_ready_for_webhook.id,
            'event_type': 'payment.success',
            'transaction_id': 'TXN_API_123'
        }

        # First webhook request
        response1 = api_client.post('/api/v1/payments/webhook/', data, format='json')
        assert response1.status_code == status.HTTP_200_OK
        assert response1.data['payment_status'] == 'SUCCESS'

        # Second identical webhook request (duplicate)
        response2 = api_client.post('/api/v1/payments/webhook/', data, format='json')
        assert response2.status_code == status.HTTP_200_OK
        assert response2.data['payment_status'] == 'SUCCESS'

        # Both responses should have same event_id
        assert response1.data['event_id'] == response2.data['event_id']

        # Only one webhook event should exist
        webhook_count = WebhookEvent.objects.filter(event_id=event_id).count()
        assert webhook_count == 1

        # Payment should only have one successful webhook
        payment = Payment.objects.get(id=payment_ready_for_webhook.id)
        assert payment.webhook_events.filter(status='COMPLETED').count() == 1