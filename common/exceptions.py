from rest_framework.exceptions import APIException
from rest_framework import status


class BookingConflict(APIException):
    """Raised when booking state is invalid."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Booking state conflict.'
    default_code = 'booking_conflict'


class PaymentConflict(APIException):
    """Raised when payment state is invalid."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Payment state conflict.'
    default_code = 'payment_conflict'


class InsufficientPermission(APIException):
    """Raised when user lacks permission for resource."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'You do not have permission to access this resource.'
    default_code = 'insufficient_permission'