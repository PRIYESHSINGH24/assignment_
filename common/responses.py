from rest_framework.response import Response
from rest_framework import status as http_status
from rest_framework.exceptions import APIException
from django.http import Http404
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Custom exception handler for consistent error responses."""

    # Handle Django's Http404
    if isinstance(exc, Http404):
        return Response({'detail': 'Not found.'}, status=http_status.HTTP_404_NOT_FOUND)

    if isinstance(exc, APIException):
        status_code = exc.status_code
        detail = exc.detail
    else:
        status_code = http_status.HTTP_500_INTERNAL_SERVER_ERROR
        detail = 'An error occurred.'
        logger.error(f"Unhandled exception: {exc}", exc_info=context)

    if isinstance(detail, (dict, list)):
        return Response(detail, status=status_code)

    return Response({'detail': str(detail)}, status=status_code)
