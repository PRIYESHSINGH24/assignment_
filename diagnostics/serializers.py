from rest_framework import serializers
from diagnostics.models import DiagnosticCentre, DiagnosticTest, CentreTest


class DiagnosticTestSerializer(serializers.ModelSerializer):
    """Serializer for diagnostic tests."""

    class Meta:
        model = DiagnosticTest
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class CentreTestSerializer(serializers.ModelSerializer):
    """Serializer for centre-test relationships with pricing."""

    test_name = serializers.CharField(source='test.name', read_only=True)
    centre_name = serializers.CharField(source='centre.name', read_only=True)

    class Meta:
        model = CentreTest
        fields = ['id', 'centre', 'centre_name', 'test', 'test_name', 'price', 'available', 'created_at']
        read_only_fields = ['id', 'created_at']


class DiagnosticCentreListSerializer(serializers.ModelSerializer):
    """Serializer for listing diagnostic centres."""

    class Meta:
        model = DiagnosticCentre
        fields = ['id', 'name', 'city', 'phone', 'created_at']
        read_only_fields = ['id', 'created_at']


class DiagnosticCentreDetailSerializer(serializers.ModelSerializer):
    """Serializer for centre details including tests and pricing."""

    centre_tests = serializers.SerializerMethodField()

    class Meta:
        model = DiagnosticCentre
        fields = ['id', 'name', 'address', 'city', 'phone', 'centre_tests', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_centre_tests(self, obj):
        """Return available tests at this centre."""
        centre_tests = obj.centre_tests.filter(available=True)
        return CentreTestSerializer(centre_tests, many=True).data


class DiagnosticCentreCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating centres."""

    class Meta:
        model = DiagnosticCentre
        fields = ['name', 'address', 'city', 'phone']