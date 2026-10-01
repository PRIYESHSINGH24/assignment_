import pytest
import django
from django.conf import settings
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta


def pytest_configure():
    """Configure Django settings before running tests."""
    if not settings.configured:
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
        django.setup()


@pytest.fixture
def api_client():
    """Fixture for REST API client."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_user(db):
    """Fixture for an authenticated user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(
        email='test@example.com',
        password='testpass123'
    )
    return user


@pytest.fixture
def authenticated_client(api_client, authenticated_user):
    """Fixture for an authenticated API client."""
    api_client.force_authenticate(user=authenticated_user)
    return api_client


@pytest.fixture
def staff_user(db):
    """Create a staff user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(
        email='staff@example.com',
        password='testpass123',
        is_staff=True
    )
    return user


@pytest.fixture
def staff_client(api_client, staff_user):
    """Create an authenticated staff client."""
    api_client.force_authenticate(user=staff_user)
    return api_client


@pytest.fixture
def sample_centre(db):
    """Create a sample diagnostic centre."""
    from diagnostics.models import DiagnosticCentre
    return DiagnosticCentre.objects.create(
        name='Apollo Diagnostics',
        address='123 Medical St',
        city='Mumbai',
        phone='9876543210'
    )


@pytest.fixture
def sample_test(db):
    """Create a sample diagnostic test."""
    from diagnostics.models import DiagnosticTest
    return DiagnosticTest.objects.create(
        name='Blood Test',
        description='Complete blood count'
    )


@pytest.fixture
def sample_centre_test(db, sample_centre, sample_test):
    """Create a centre-test relationship."""
    from diagnostics.models import CentreTest
    return CentreTest.objects.create(
        centre=sample_centre,
        test=sample_test,
        price=Decimal('500.00')
    )


@pytest.fixture
def centre_with_test(db):
    """Create a centre with a test."""
    from diagnostics.models import DiagnosticCentre, DiagnosticTest, CentreTest
    centre = DiagnosticCentre.objects.create(
        name='Test Centre',
        address='123 Test St',
        city='Test City',
        phone='1234567890'
    )
    test = DiagnosticTest.objects.create(name='Test A')
    centre_test = CentreTest.objects.create(
        centre=centre,
        test=test,
        price=Decimal('500.00')
    )
    return centre, test, centre_test


@pytest.fixture
def future_appointment():
    """Return a future appointment datetime."""
    return timezone.now() + timedelta(days=7)


@pytest.fixture
def booking_for_payment(db, authenticated_user):
    """Create a booking for payment testing."""
    from bookings.models import Booking, BookingStatusChoices
    from diagnostics.models import DiagnosticCentre, DiagnosticTest, CentreTest

    centre = DiagnosticCentre.objects.create(
        name='Test Centre',
        address='123 Test St',
        city='Test City',
        phone='1234567890'
    )
    test = DiagnosticTest.objects.create(name='Test A')
    CentreTest.objects.create(
        centre=centre,
        test=test,
        price=Decimal('500.00')
    )

    booking = Booking.objects.create(
        user=authenticated_user,
        centre=centre,
        test=test,
        appointment_date=timezone.now() + timedelta(days=7),
        amount=Decimal('500.00'),
        status=BookingStatusChoices.PENDING
    )
    return booking


@pytest.fixture
def payment_ready_for_webhook(db, authenticated_user):
    """Create a payment in PENDING status ready for webhook."""
    from bookings.models import Booking, BookingStatusChoices
    from diagnostics.models import DiagnosticCentre, DiagnosticTest, CentreTest
    from payments.models import Payment, PaymentStatusChoices

    centre = DiagnosticCentre.objects.create(
        name='Centre',
        address='123',
        city='City',
        phone='1111111111'
    )
    test = DiagnosticTest.objects.create(name='Test')
    CentreTest.objects.create(centre=centre, test=test, price=Decimal('500.00'))

    booking = Booking.objects.create(
        user=authenticated_user,
        centre=centre,
        test=test,
        appointment_date=timezone.now() + timedelta(days=7),
        amount=Decimal('500.00'),
        status=BookingStatusChoices.PENDING
    )

    payment = Payment.objects.create(
        booking=booking,
        amount=Decimal('500.00'),
        status=PaymentStatusChoices.PENDING
    )

    return payment