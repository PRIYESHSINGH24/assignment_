import pytest
from django.core.cache import cache
from django.test import TestCase
from diagnostics.models import DiagnosticCentre, DiagnosticTest, CentreTest
from bookings.models import Booking
from decimal import Decimal
from unittest.mock import patch


class CacheUtilsTests(TestCase):
    """Tests for cache utilities."""

    def test_cache_result_decorator(self):
        """Test the cache_result decorator."""
        from common.cache_utils import cache_result

        call_count = 0

        @cache_result(timeout=100)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call should execute the function
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented

    def test_cache_key_generation(self):
        """Test cache key generation."""
        from common.cache_utils import cache_key

        key1 = cache_key('prefix', 'arg1', 'arg2')
        key2 = cache_key('prefix', 'arg1', 'arg2')

        assert key1 == key2
        assert 'prefix' in key1

    def test_cache_key_with_long_args(self):
        """Test cache key generation with very long arguments."""
        from common.cache_utils import cache_key

        long_arg = 'x' * 500
        key = cache_key('prefix', long_arg)

        # Should use MD5 hash for long keys
        assert len(key) < 300


class DiagnosticsCacheTests(TestCase):
    """Tests for diagnostics app caching."""

    def setUp(self):
        cache.clear()
        self.centre = DiagnosticCentre.objects.create(
            name='Test Centre',
            address='123 Main St',
            city='Mumbai',
            phone='1234567890'
        )
        self.test = DiagnosticTest.objects.create(
            name='Blood Test',
            description='Complete blood count'
        )
        self.centre_test = CentreTest.objects.create(
            centre=self.centre,
            test=self.test,
            price=Decimal('500.00')
        )

    def tearDown(self):
        cache.clear()

    def test_centre_price_caching(self):
        """Test CentreTest.get_price_cached method."""
        # First call should query database
        with patch.object(CentreTest.objects, 'get') as mock_get:
            mock_get.return_value = self.centre_test
            price1 = CentreTest.get_price_cached(self.centre.id, self.test.id)

        assert price1 == Decimal('500.00')
        assert mock_get.call_count == 1

        # Second call should use cache
        with patch.object(CentreTest.objects, 'get') as mock_get:
            price2 = CentreTest.get_price_cached(self.centre.id, self.test.id)

        assert price2 == Decimal('500.00')
        assert mock_get.call_count == 0  # Not called

    def test_cache_invalidation_on_centre_save(self):
        """Test cache invalidation when centre is updated."""
        cache.set('diagnostic_centre_list', [self.centre])
        assert cache.get('diagnostic_centre_list') is not None

        # Update centre
        self.centre.name = 'Updated Centre'
        self.centre.save()

        # Cache should be invalidated
        assert cache.get('diagnostic_centre_list') is None

    def test_cache_invalidation_on_test_save(self):
        """Test cache invalidation when test is updated."""
        cache.set('diagnostic_test_list', [self.test])
        assert cache.get('diagnostic_test_list') is not None

        # Update test
        self.test.name = 'Updated Test'
        self.test.save()

        # Cache should be invalidated
        assert cache.get('diagnostic_test_list') is None

    def test_cache_invalidation_on_centre_test_save(self):
        """Test cache invalidation when centre-test is updated."""
        cache.set('centre_test_list', [self.centre_test])
        assert cache.get('centre_test_list') is not None

        # Update centre-test price
        self.centre_test.price = Decimal('600.00')
        self.centre_test.save()

        # Cache should be invalidated
        assert cache.get('centre_test_list') is None


class BookingsCacheTests(TestCase):
    """Tests for bookings app caching."""

    def setUp(self):
        cache.clear()
        from django.contrib.auth import get_user_model
        User = get_user_model()

        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.centre = DiagnosticCentre.objects.create(
            name='Test Centre',
            address='123 Main St',
            city='Mumbai',
            phone='1234567890'
        )
        self.test = DiagnosticTest.objects.create(
            name='Blood Test',
            description='Complete blood count'
        )
        self.centre_test = CentreTest.objects.create(
            centre=self.centre,
            test=self.test,
            price=Decimal('500.00')
        )

    def tearDown(self):
        cache.clear()

    def test_cache_invalidation_on_booking_save(self):
        """Test cache invalidation when booking is created."""
        from django.utils import timezone
        from datetime import timedelta

        appointment_date = timezone.now() + timedelta(days=1)

        # Pre-populate cache
        cache.set(f'user_bookings:{self.user.id}', [])
        assert cache.get(f'user_bookings:{self.user.id}') is not None

        # Create booking
        booking = Booking.objects.create(
            user=self.user,
            centre=self.centre,
            test=self.test,
            appointment_date=appointment_date,
            amount=Decimal('500.00')
        )

        # Cache should be invalidated
        assert cache.get(f'user_bookings:{self.user.id}') is None

    def test_cache_invalidation_on_booking_cancel(self):
        """Test cache invalidation when booking is cancelled."""
        from django.utils import timezone
        from datetime import timedelta

        appointment_date = timezone.now() + timedelta(days=1)
        booking = Booking.objects.create(
            user=self.user,
            centre=self.centre,
            test=self.test,
            appointment_date=appointment_date,
            amount=Decimal('500.00')
        )

        # Pre-populate cache
        cache.set(f'user_bookings:{self.user.id}', [booking])
        assert cache.get(f'user_bookings:{self.user.id}') is not None

        # Cancel booking
        booking.cancel()

        # Cache should be invalidated
        assert cache.get(f'user_bookings:{self.user.id}') is None


class PaymentsCacheTests(TestCase):
    """Tests for payments app caching."""

    def setUp(self):
        cache.clear()
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        from datetime import timedelta
        from payments.models import Payment

        User = get_user_model()

        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.centre = DiagnosticCentre.objects.create(
            name='Test Centre',
            address='123 Main St',
            city='Mumbai',
            phone='1234567890'
        )
        self.test = DiagnosticTest.objects.create(
            name='Blood Test',
            description='Complete blood count'
        )
        self.centre_test = CentreTest.objects.create(
            centre=self.centre,
            test=self.test,
            price=Decimal('500.00')
        )
        appointment_date = timezone.now() + timedelta(days=1)
        self.booking = Booking.objects.create(
            user=self.user,
            centre=self.centre,
            test=self.test,
            appointment_date=appointment_date,
            amount=Decimal('500.00')
        )
        self.payment = Payment.objects.create(
            booking=self.booking,
            amount=Decimal('500.00')
        )

    def tearDown(self):
        cache.clear()

    def test_payment_cache_invalidation_on_success(self):
        """Test cache invalidation when payment is marked successful."""
        # Pre-populate user's booking cache
        cache.set(f'user_bookings:{self.user.id}', [self.booking])
        assert cache.get(f'user_bookings:{self.user.id}') is not None

        # Mark payment as successful
        self.payment.mark_success('TXN_123')

        # User's cache should be invalidated
        assert cache.get(f'user_bookings:{self.user.id}') is None

    def test_payment_cache_invalidation_on_failure(self):
        """Test cache invalidation when payment is marked failed."""
        # Pre-populate user's booking cache
        cache.set(f'user_bookings:{self.user.id}', [self.booking])
        assert cache.get(f'user_bookings:{self.user.id}') is not None

        # Mark payment as failed
        self.payment.mark_failed('Insufficient funds')

        # User's cache should be invalidated
        assert cache.get(f'user_bookings:{self.user.id}') is None
