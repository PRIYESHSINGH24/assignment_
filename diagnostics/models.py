from django.db import models
from django.core.validators import MinValueValidator
from django.core.cache import cache
from decimal import Decimal


class DiagnosticCentre(models.Model):
    """Diagnostic centre."""

    name = models.CharField(max_length=255, unique=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._invalidate_cache()

    def delete(self, *args, **kwargs):
        self._invalidate_cache()
        super().delete(*args, **kwargs)

    @staticmethod
    def _invalidate_cache():
        cache.delete_many([
            'diagnostic_centre_list',
            'diagnostic_centre_by_city',
        ])


class DiagnosticTest(models.Model):
    """Diagnostic test."""

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._invalidate_cache()

    def delete(self, *args, **kwargs):
        self._invalidate_cache()
        super().delete(*args, **kwargs)

    @staticmethod
    def _invalidate_cache():
        cache.delete_many([
            'diagnostic_test_list',
        ])


class CentreTest(models.Model):
    """Relationship between a centre and a test with centre-specific pricing."""

    centre = models.ForeignKey(
        DiagnosticCentre,
        on_delete=models.CASCADE,
        related_name='centre_tests'
    )
    test = models.ForeignKey(
        DiagnosticTest,
        on_delete=models.CASCADE,
        related_name='centre_tests'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('centre', 'test')
        verbose_name_plural = 'Centre tests'
        ordering = ['centre', 'test']

    def __str__(self):
        return f"{self.test.name} at {self.centre.name} - {self.price}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._invalidate_cache()

    def delete(self, *args, **kwargs):
        self._invalidate_cache()
        super().delete(*args, **kwargs)

    @classmethod
    def get_price_cached(cls, centre_id, test_id):
        """Get cached price for a centre-test combination."""
        cache_key = f'centre_test_price:{centre_id}:{test_id}'
        price = cache.get(cache_key)

        if price is None:
            try:
                centre_test = cls.objects.get(centre_id=centre_id, test_id=test_id)
                price = centre_test.price
                cache.set(cache_key, price, 1800)
            except cls.DoesNotExist:
                return None

        return price

    @staticmethod
    def _invalidate_cache():
        cache.delete_many([
            'centre_test_list',
            'centre_tests_by_centre',
        ])