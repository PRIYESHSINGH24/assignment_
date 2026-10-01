from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.cache import cache
from decimal import Decimal

User = get_user_model()


class BookingStatusChoices(models.TextChoices):
    """Booking status choices."""
    PENDING = 'PENDING', 'Pending'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class Booking(models.Model):
    """Diagnostic test booking."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    centre = models.ForeignKey('diagnostics.DiagnosticCentre', on_delete=models.CASCADE, related_name='bookings')
    test = models.ForeignKey('diagnostics.DiagnosticTest', on_delete=models.CASCADE, related_name='bookings')
    appointment_date = models.DateTimeField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=BookingStatusChoices.choices,
        default=BookingStatusChoices.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking {self.id}: {self.test.name} at {self.centre.name} - {self.status}"

    def clean(self):
        """Validate the booking."""
        if self.appointment_date and self.appointment_date <= timezone.now():
            raise ValidationError({'appointment_date': 'Appointment date must be in the future.'})

    def can_transition_to(self, new_status):
        """Check if a status transition is valid."""
        valid_transitions = {
            BookingStatusChoices.PENDING: [BookingStatusChoices.CONFIRMED, BookingStatusChoices.CANCELLED],
            BookingStatusChoices.CONFIRMED: [BookingStatusChoices.COMPLETED, BookingStatusChoices.CANCELLED],
            BookingStatusChoices.COMPLETED: [],
            BookingStatusChoices.CANCELLED: [],
        }
        return new_status in valid_transitions.get(self.status, [])

    def cancel(self):
        """Cancel the booking."""
        if not self.can_transition_to(BookingStatusChoices.CANCELLED):
            raise ValidationError(f'Cannot cancel a booking in {self.status} status.')
        self.status = BookingStatusChoices.CANCELLED
        self.save()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._invalidate_user_cache()

    def delete(self, *args, **kwargs):
        self._invalidate_user_cache()
        super().delete(*args, **kwargs)

    def _invalidate_user_cache(self):
        """Invalidate cache for this user's bookings."""
        cache.delete(f'user_bookings:{self.user_id}')