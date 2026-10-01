from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.core.cache import cache

from diagnostics.models import DiagnosticCentre, DiagnosticTest, CentreTest
from diagnostics.serializers import (
    DiagnosticCentreListSerializer,
    DiagnosticCentreDetailSerializer,
    DiagnosticCentreCreateUpdateSerializer,
    DiagnosticTestSerializer,
    CentreTestSerializer,
)
from common.permissions import IsStaffOrReadOnly
from common.cache_utils import cache_queryset


class DiagnosticCentreViewSet(viewsets.ModelViewSet):
    """ViewSet for diagnostic centres."""

    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['city']
    search_fields = ['name', 'city']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'retrieve':
            return DiagnosticCentreDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return DiagnosticCentreCreateUpdateSerializer
        return DiagnosticCentreListSerializer

    @cache_queryset('diagnostic_centre_list', timeout=3600)
    def get_queryset(self):
        """Return centres queryset with caching."""
        return DiagnosticCentre.objects.all()

    @action(detail=True, methods=['get'])
    def tests(self, request, pk=None):
        """Get all tests available at a specific centre with caching."""
        cache_key = f'centre_available_tests:{pk}'
        serializer_data = cache.get(cache_key)

        if serializer_data is None:
            centre = self.get_object()
            centre_tests = centre.centre_tests.filter(available=True)
            serializer = CentreTestSerializer(centre_tests, many=True)
            serializer_data = serializer.data
            cache.set(cache_key, serializer_data, 1800)

        return Response(serializer_data)


class DiagnosticTestViewSet(viewsets.ModelViewSet):
    """ViewSet for diagnostic tests."""

    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        return DiagnosticTestSerializer

    @cache_queryset('diagnostic_test_list', timeout=3600)
    def get_queryset(self):
        """Return tests queryset with caching."""
        return DiagnosticTest.objects.all()


class CentreTestViewSet(viewsets.ModelViewSet):
    """ViewSet for centre-test relationships."""

    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['centre', 'test', 'available']
    search_fields = ['test__name', 'centre__name']

    def get_serializer_class(self):
        return CentreTestSerializer

    @cache_queryset('centre_test_list', timeout=1800)
    def get_queryset(self):
        """Return centre-tests with caching."""
        return CentreTest.objects.select_related('centre', 'test')