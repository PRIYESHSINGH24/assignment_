import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.core.cache import cache


class PaymentStatusChoices(models.TextChoices):
    """Payment status choices."""
    PENDING = 'PENDING', 'Pending'
    SUCCESS = 'SUCCESS', 'Success'
    FAILED = 'FAILED', 'Failed'


class Payment(models.Model):
    """Payment for a booking."""

    booking = models.OneToOneField(
        'bookings.Booking',
        on_delete=models.CASCADE,
        related_name='payment'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=PaymentStatusChoices.choices,
        default=PaymentStatusChoices.PENDING
    )
    idempotency_key = models.UUIDField(unique=True, default=uuid.uuid4)
    external_transaction_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True
    )
    reason = models.TextField(blank=True, help_text='Reason for failure, if any')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.id}: {self.booking.id} - {self.amount} - {self.status}"

    def clean(self):
        """Validate payment."""
        if self.amount != self.booking.amount:
            raise ValidationError(
                f'Payment amount ({self.amount}) does not match booking amount ({self.booking.amount}).'
            )

    def mark_success(self, external_transaction_id):
        """Mark payment as successful."""
        if self.status != PaymentStatusChoices.PENDING:
            raise ValidationError(f'Cannot mark a {self.status} payment as success.')

        self.status = PaymentStatusChoices.SUCCESS
        self.external_transaction_id = external_transaction_id
        self.save()
        self._invalidate_user_cache()

    def mark_failed(self, reason=''):
        """Mark payment as failed."""
        if self.status != PaymentStatusChoices.PENDING:
            raise ValidationError(f'Cannot mark a {self.status} payment as failed.')

        self.status = PaymentStatusChoices.FAILED
        self.reason = reason
        self.save()
        self._invalidate_user_cache()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._invalidate_user_cache()

    def _invalidate_user_cache(self):
        """Invalidate cache for booking user."""
        if self.booking_id:
            cache.delete(f'user_bookings:{self.booking.user_id}')


class WebhookEvent(models.Model):
    """Record of a webhook event for idempotency tracking."""

    EVENT_TYPE_CHOICES = (
        ('payment.success', 'Payment Success'),
        ('payment.failed', 'Payment Failed'),
    )

    EVENT_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )

    event_id = models.CharField(max_length=255, unique=True)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='webhook_events'
    )
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    status = models.CharField(
        max_length=20,
        choices=EVENT_STATUS_CHOICES,
        default='PENDING'
    )
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"WebhookEvent {self.event_id}: {self.payment.id} - {self.status}"
