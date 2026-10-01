"""Custom exceptions for payment-related operations."""


class WebhookProcessingError(Exception):
    """Exception raised when webhook processing fails."""
    pass


class PaymentNotFound(WebhookProcessingError):
    """Exception raised when a payment is not found."""
    pass
