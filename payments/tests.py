import pytest
import uuid
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from bookings.models import Booking, BookingStatusChoices
from diagnostics.models import DiagnosticCentre, DiagnosticTest, CentreTest
from payments.models import Payment, PaymentStatusChoices


class TestPaymentCreation:
    """Tests for creating payments."""

    @pytest.mark.django_db
    def test_create_payment_authenticated(self, authenticated_client, booking_for_payment):
        """Test creating a payment as authenticated user."""
        data = {'booking_id': booking_for_payment.id}
        response = authenticated_client.post('/api/v1/payments/', data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['booking_id'] == booking_for_payment.id
        assert response.data['amount'] == '500.00'
        assert response.data['status'] == 'PENDING'

    @pytest.mark.django_db
    def test_create_payment_unauthenticated(self, api_client, booking_for_payment):
        """Test creating a payment without authentication."""
        data = {'booking_id': booking_for_payment.id}
        response = api_client.post('/api/v1/payments/', data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_create_payment_invalid_booking(self, authenticated_client):
        """Test creating a payment for non-existent booking."""
        data = {'booking_id': 9999}
        response = authenticated_client.post('/api/v1/payments/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'booking_id' in response.data

    @pytest.mark.django_db
    def test_create_payment_other_users_booking(self, db, authenticated_client):
        """Test creating a payment for another user's booking."""
        User = get_user_model()
        other_user = User.objects.create_user(email='other@example.com', password='pass123')
        centre = DiagnosticCentre.objects.create(
            name='Centre', address='123', city='City', phone='1111111111'
        )
        test = DiagnosticTest.objects.create(name='Test')
        CentreTest.objects.create(centre=centre, test=test, price='500')

        booking = Booking.objects.create(
            user=other_user,
            centre=centre,
            test=test,
            appointment_date=timezone.now() + timedelta(days=7),
            amount='500',
            status=BookingStatusChoices.PENDING
        )

        data = {'booking_id': booking.id}
        response = authenticated_client.post('/api/v1/payments/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_create_duplicate_payment(self, authenticated_client, booking_for_payment):
        """Test creating duplicate payment for the same booking."""
        data = {'booking_id': booking_for_payment.id}

        # First payment
        response1 = authenticated_client.post('/api/v1/payments/', data, format='json')
        assert response1.status_code == status.HTTP_201_CREATED

        # Second payment attempt
        response2 = authenticated_client.post('/api/v1/payments/', data, format='json')
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert 'A payment already exists' in str(response2.data)


class TestPaymentIdempotency:
    """Tests for payment idempotency."""

    @pytest.mark.django_db
    def test_idempotency_key_same_request(self, authenticated_client, booking_for_payment):
        """Test that same idempotency_key returns the same payment."""
        idempotency_key = str(uuid.uuid4())
        data = {
            'booking_id': booking_for_payment.id,
            'idempotency_key': idempotency_key
        }

        # First request
        response1 = authenticated_client.post('/api/v1/payments/', data, format='json')
        assert response1.status_code == status.HTTP_201_CREATED
        payment_id_1 = response1.data['id']

        # Second request with same idempotency_key
        response2 = authenticated_client.post('/api/v1/payments/', data, format='json')
        assert response2.status_code == status.HTTP_201_CREATED
        payment_id_2 = response2.data['id']

        # Should be the same payment
        assert payment_id_1 == payment_id_2

    @pytest.mark.django_db
    def test_idempotency_key_unique(self, api_client, authenticated_user, centre_with_test):
        """Test that different idempotency_keys create different payments."""
        centre, test, _ = centre_with_test
        api_client.force_authenticate(user=authenticated_user)

        booking1 = Booking.objects.create(
            user=authenticated_user, centre=centre, test=test,
            appointment_date=timezone.now() + timedelta(days=7),
            amount='500', status=BookingStatusChoices.PENDING
        )
        booking2 = Booking.objects.create(
            user=authenticated_user, centre=centre, test=test,
            appointment_date=timezone.now() + timedelta(days=8),
            amount='500', status=BookingStatusChoices.PENDING
        )

        # Payment 1
        response1 = api_client.post('/api/v1/payments/', {
            'booking_id': booking1.id,
            'idempotency_key': str(uuid.uuid4())
        }, format='json')

        # Payment 2
        response2 = api_client.post('/api/v1/payments/', {
            'booking_id': booking2.id,
            'idempotency_key': str(uuid.uuid4())
        }, format='json')

        assert response1.data['id'] != response2.data['id']


class TestPaymentProcessing:
    """Tests for payment processing."""

    @pytest.mark.django_db
    def test_process_payment_success(self, authenticated_client, booking_for_payment):
        """Test processing a payment as SUCCESS."""
        # Create payment
        create_response = authenticated_client.post(
            '/api/v1/payments/',
            {'booking_id': booking_for_payment.id},
            format='json'
        )
        payment_id = create_response.data['id']

        # Process as SUCCESS
        process_response = authenticated_client.post(
            '/api/v1/payments/process/',
            {'payment_id': payment_id, 'status': 'SUCCESS'},
            format='json'
        )

        assert process_response.status_code == status.HTTP_200_OK
        assert process_response.data['status'] == 'SUCCESS'
        assert process_response.data['external_transaction_id'] is not None

    @pytest.mark.django_db
    def test_process_payment_failed(self, authenticated_client, booking_for_payment):
        """Test processing a payment as FAILED."""
        # Create payment
        create_response = authenticated_client.post(
            '/api/v1/payments/',
            {'booking_id': booking_for_payment.id},
            format='json'
        )
        payment_id = create_response.data['id']

        # Process as FAILED
        process_response = authenticated_client.post(
            '/api/v1/payments/process/',
            {
                'payment_id': payment_id,
                'status': 'FAILED',
                'reason': 'Insufficient funds'
            },
            format='json'
        )

        assert process_response.status_code == status.HTTP_200_OK
        assert process_response.data['status'] == 'FAILED'
        assert process_response.data['reason'] == 'Insufficient funds'

    @pytest.mark.django_db
    def test_process_payment_updates_booking(self, authenticated_client, booking_for_payment):
        """Test that processing payment SUCCESS updates booking to CONFIRMED."""
        # Create payment
        create_response = authenticated_client.post(
            '/api/v1/payments/',
            {'booking_id': booking_for_payment.id},
            format='json'
        )
        payment_id = create_response.data['id']

        # Process as SUCCESS
        authenticated_client.post(
            '/api/v1/payments/process/',
            {'payment_id': payment_id, 'status': 'SUCCESS'},
            format='json'
        )

        # Check booking status
        booking = Booking.objects.get(id=booking_for_payment.id)
        assert booking.status == BookingStatusChoices.CONFIRMED

    @pytest.mark.django_db
    def test_process_payment_already_processed(self, authenticated_client, booking_for_payment):
        """Test that processing a payment twice fails."""
        # Create payment
        create_response = authenticated_client.post(
            '/api/v1/payments/',
            {'booking_id': booking_for_payment.id},
            format='json'
        )
        payment_id = create_response.data['id']

        # Process as SUCCESS
        authenticated_client.post(
            '/api/v1/payments/process/',
            {'payment_id': payment_id, 'status': 'SUCCESS'},
            format='json'
        )

        # Try to process again
        response = authenticated_client.post(
            '/api/v1/payments/process/',
            {'payment_id': payment_id, 'status': 'SUCCESS'},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_process_payment_invalid_status(self, authenticated_client, booking_for_payment):
        """Test processing payment with invalid status."""
        # Create payment
        create_response = authenticated_client.post(
            '/api/v1/payments/',
            {'booking_id': booking_for_payment.id},
            format='json'
        )
        payment_id = create_response.data['id']

        # Try with invalid status
        response = authenticated_client.post(
            '/api/v1/payments/process/',
            {'payment_id': payment_id, 'status': 'INVALID'},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_process_payment_authorization(self, api_client, booking_for_payment):
        """Test that users cannot process others' payments."""
        User = get_user_model()
        other_user = User.objects.create_user(email='other@example.com', password='pass123')

        payment = Payment.objects.create(
            booking=booking_for_payment,
            amount='500',
            status=PaymentStatusChoices.PENDING
        )

        api_client.force_authenticate(user=other_user)

        response = api_client.post(
            '/api/v1/payments/process/',
            {'payment_id': payment.id, 'status': 'SUCCESS'},
            format='json'
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestPaymentValidation:
    """Tests for payment validation."""

    @pytest.mark.django_db
    def test_payment_amount_matches_booking(self, authenticated_client, booking_for_payment):
        """Test that payment amount matches booking amount."""
        from decimal import Decimal
        response = authenticated_client.post(
            '/api/v1/payments/',
            {'booking_id': booking_for_payment.id},
            format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert Decimal(response.data['amount']) == booking_for_payment.amount