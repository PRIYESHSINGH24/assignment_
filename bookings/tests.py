import pytest
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from bookings.models import Booking, BookingStatusChoices
from diagnostics.models import DiagnosticCentre, DiagnosticTest, CentreTest

User = get_user_model()


class TestBookingCreation:
    """Tests for creating bookings."""

    @pytest.mark.django_db
    def test_create_booking_authenticated(self, authenticated_client, authenticated_user, centre_with_test,
                                          future_appointment):
        """Test creating a booking as authenticated user."""
        centre, test, _ = centre_with_test
        data = {
            'centre_id': centre.id,
            'test_id': test.id,
            'appointment_date': future_appointment.isoformat(),
        }
        response = authenticated_client.post('/api/v1/bookings/', data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['user'] == authenticated_user.id
        assert response.data['amount'] == '500.00'  # Server-calculated
        assert response.data['status'] == 'PENDING'

    @pytest.mark.django_db
    def test_create_booking_unauthenticated(self, api_client, centre_with_test, future_appointment):
        """Test creating a booking without authentication."""
        centre, test, _ = centre_with_test
        data = {
            'centre_id': centre.id,
            'test_id': test.id,
            'appointment_date': future_appointment.isoformat(),
        }
        response = api_client.post('/api/v1/bookings/', data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_create_booking_invalid_centre(self, authenticated_client, centre_with_test, future_appointment):
        """Test creating a booking with non-existent centre."""
        _, test, _ = centre_with_test
        data = {
            'centre_id': 9999,
            'test_id': test.id,
            'appointment_date': future_appointment.isoformat(),
        }
        response = authenticated_client.post('/api/v1/bookings/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'centre_id' in response.data

    @pytest.mark.django_db
    def test_create_booking_invalid_test(self, authenticated_client, centre_with_test, future_appointment):
        """Test creating a booking with non-existent test."""
        centre, _, _ = centre_with_test
        data = {
            'centre_id': centre.id,
            'test_id': 9999,
            'appointment_date': future_appointment.isoformat(),
        }
        response = authenticated_client.post('/api/v1/bookings/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'test_id' in response.data

    @pytest.mark.django_db
    def test_create_booking_test_not_at_centre(self, authenticated_client, centre_with_test, future_appointment):
        """Test creating a booking for a test not offered at the centre."""
        centre, _, _ = centre_with_test
        other_test = DiagnosticTest.objects.create(name='Other Test')

        data = {
            'centre_id': centre.id,
            'test_id': other_test.id,
            'appointment_date': future_appointment.isoformat(),
        }
        response = authenticated_client.post('/api/v1/bookings/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'non_field_errors' in response.data

    @pytest.mark.django_db
    def test_create_booking_past_date(self, authenticated_client, centre_with_test):
        """Test creating a booking with a past appointment date."""
        centre, test, _ = centre_with_test
        past_date = timezone.now() - timedelta(days=1)

        data = {
            'centre_id': centre.id,
            'test_id': test.id,
            'appointment_date': past_date.isoformat(),
        }
        response = authenticated_client.post('/api/v1/bookings/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'appointment_date' in response.data

    @pytest.mark.django_db
    def test_create_booking_price_server_calculated(self, authenticated_client, centre_with_test, future_appointment):
        """Test that booking price is server-calculated, not from user input."""
        centre, test, _ = centre_with_test
        data = {
            'centre_id': centre.id,
            'test_id': test.id,
            'appointment_date': future_appointment.isoformat(),
            'amount': 10,  # User tries to set a wrong price
        }
        response = authenticated_client.post('/api/v1/bookings/', data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['amount'] == '500.00'  # Correct price, not 10


class TestBookingAuthorization:
    """Tests for booking authorization."""

    @pytest.mark.django_db
    def test_user_sees_only_own_bookings(self, api_client, centre_with_test, future_appointment):
        """Test that users only see their own bookings."""
        user1 = User.objects.create_user(email='user1@example.com', password='pass123')
        user2 = User.objects.create_user(email='user2@example.com', password='pass123')

        centre, test, _ = centre_with_test

        booking1 = Booking.objects.create(
            user=user1, centre=centre, test=test,
            appointment_date=future_appointment, amount='500', status='PENDING'
        )
        booking2 = Booking.objects.create(
            user=user2, centre=centre, test=test,
            appointment_date=future_appointment, amount='500', status='PENDING'
        )

        # Login as user1
        api_client.force_authenticate(user=user1)
        response = api_client.get('/api/v1/bookings/')

        assert response.status_code == status.HTTP_200_OK
        booking_ids = [b['id'] for b in response.data['results']]
        assert booking1.id in booking_ids
        assert booking2.id not in booking_ids


class TestBookingCancellation:
    """Tests for booking cancellation and status transitions."""

    @pytest.mark.django_db
    def test_cancel_pending_booking(self, authenticated_client, authenticated_user, centre_with_test, future_appointment):
        """Test cancelling a PENDING booking."""
        centre, test, _ = centre_with_test

        booking = Booking.objects.create(
            user=authenticated_user,
            centre=centre, test=test,
            appointment_date=future_appointment,
            amount='500', status=BookingStatusChoices.PENDING
        )

        response = authenticated_client.post(f'/api/v1/bookings/{booking.id}/cancel/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'CANCELLED'

    @pytest.mark.django_db
    def test_cancel_confirmed_booking(self, api_client, centre_with_test, future_appointment):
        """Test cancelling a CONFIRMED booking."""
        centre, test, _ = centre_with_test
        user = User.objects.create_user(email='user@example.com', password='pass123')
        api_client.force_authenticate(user=user)

        booking = Booking.objects.create(
            user=user, centre=centre, test=test,
            appointment_date=future_appointment,
            amount='500', status=BookingStatusChoices.CONFIRMED
        )

        response = api_client.post(f'/api/v1/bookings/{booking.id}/cancel/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'CANCELLED'

    @pytest.mark.django_db
    def test_cannot_cancel_cancelled_booking(self, api_client, centre_with_test, future_appointment):
        """Test that a cancelled booking cannot be cancelled again."""
        centre, test, _ = centre_with_test
        user = User.objects.create_user(email='user@example.com', password='pass123')
        api_client.force_authenticate(user=user)

        booking = Booking.objects.create(
            user=user, centre=centre, test=test,
            appointment_date=future_appointment,
            amount='500', status=BookingStatusChoices.CANCELLED
        )

        response = api_client.post(f'/api/v1/bookings/{booking.id}/cancel/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_cannot_cancel_completed_booking(self, api_client, centre_with_test, future_appointment):
        """Test that a completed booking cannot be cancelled."""
        centre, test, _ = centre_with_test
        user = User.objects.create_user(email='user@example.com', password='pass123')
        api_client.force_authenticate(user=user)

        booking = Booking.objects.create(
            user=user, centre=centre, test=test,
            appointment_date=future_appointment,
            amount='500', status=BookingStatusChoices.COMPLETED
        )

        response = api_client.post(f'/api/v1/bookings/{booking.id}/cancel/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestBookingFiltering:
    """Tests for booking filtering."""

    @pytest.mark.django_db
    def test_filter_bookings_by_status(self, api_client, centre_with_test, future_appointment):
        """Test filtering bookings by status."""
        centre, test, _ = centre_with_test
        user = User.objects.create_user(email='user@example.com', password='pass123')
        api_client.force_authenticate(user=user)

        Booking.objects.create(
            user=user, centre=centre, test=test,
            appointment_date=future_appointment,
            amount='500', status=BookingStatusChoices.PENDING
        )
        Booking.objects.create(
            user=user, centre=centre, test=test,
            appointment_date=future_appointment,
            amount='500', status=BookingStatusChoices.CANCELLED
        )

        response = api_client.get('/api/v1/bookings/?status=PENDING')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['status'] == 'PENDING'