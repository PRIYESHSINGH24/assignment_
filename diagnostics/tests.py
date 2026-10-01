import pytest
from rest_framework import status
from diagnostics.models import DiagnosticCentre, DiagnosticTest, CentreTest


class TestDiagnosticCentreList:
    """Tests for listing diagnostic centres."""

    @pytest.mark.django_db
    def test_list_centres_unauthenticated(self, api_client, sample_centre):
        """Test listing centres without authentication."""
        response = api_client.get('/api/v1/diagnostics/centres/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) > 0
        assert response.data['results'][0]['name'] == 'Apollo Diagnostics'

    @pytest.mark.django_db
    def test_list_centres_filter_by_city(self, api_client):
        """Test filtering centres by city."""
        DiagnosticCentre.objects.create(
            name='Centre A', address='123', city='Mumbai', phone='1111111111'
        )
        DiagnosticCentre.objects.create(
            name='Centre B', address='456', city='Delhi', phone='2222222222'
        )

        response = api_client.get('/api/v1/diagnostics/centres/?city=Mumbai')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['city'] == 'Mumbai'

    @pytest.mark.django_db
    def test_list_centres_search_by_name(self, api_client):
        """Test searching centres by name."""
        DiagnosticCentre.objects.create(
            name='Apollo Diagnostics', address='123', city='Mumbai', phone='1111111111'
        )
        DiagnosticCentre.objects.create(
            name='Max Healthcare', address='456', city='Delhi', phone='2222222222'
        )

        response = api_client.get('/api/v1/diagnostics/centres/?search=Apollo')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == 'Apollo Diagnostics'


class TestDiagnosticCentreDetail:
    """Tests for retrieving centre details."""

    @pytest.mark.django_db
    def test_retrieve_centre_detail(self, api_client, sample_centre_test):
        """Test retrieving centre with tests."""
        response = api_client.get(f'/api/v1/diagnostics/centres/{sample_centre_test.centre.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Apollo Diagnostics'
        assert len(response.data['centre_tests']) == 1
        assert response.data['centre_tests'][0]['test_name'] == 'Blood Test'
        assert response.data['centre_tests'][0]['price'] == '500.00'

    @pytest.mark.django_db
    def test_retrieve_centre_not_found(self, api_client):
        """Test retrieving non-existent centre."""
        response = api_client.get('/api/v1/diagnostics/centres/9999/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDiagnosticCentreCreate:
    """Tests for creating centres."""

    @pytest.mark.django_db
    def test_create_centre_unauthenticated(self, api_client):
        """Test creating centre without authentication."""
        data = {
            'name': 'New Centre',
            'address': '789 New St',
            'city': 'Bangalore',
            'phone': '9876543213'
        }
        response = api_client.post('/api/v1/diagnostics/centres/', data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_create_centre_non_staff(self, authenticated_client):
        """Test creating centre as non-staff user."""
        data = {
            'name': 'New Centre',
            'address': '789 New St',
            'city': 'Bangalore',
            'phone': '9876543213'
        }
        response = authenticated_client.post('/api/v1/diagnostics/centres/', data, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_create_centre_staff(self, staff_client):
        """Test creating centre as staff user."""
        data = {
            'name': 'New Centre',
            'address': '789 New St',
            'city': 'Bangalore',
            'phone': '9876543213'
        }
        response = staff_client.post('/api/v1/diagnostics/centres/', data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Centre'
        assert DiagnosticCentre.objects.filter(name='New Centre').exists()

    @pytest.mark.django_db
    def test_create_centre_duplicate_phone(self, staff_client, sample_centre):
        """Test creating centre with duplicate phone."""
        data = {
            'name': 'Another Centre',
            'address': '789 New St',
            'city': 'Bangalore',
            'phone': sample_centre.phone  # Duplicate
        }
        response = staff_client.post('/api/v1/diagnostics/centres/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'phone' in response.data


class TestDiagnosticTestList:
    """Tests for listing diagnostic tests."""

    @pytest.mark.django_db
    def test_list_tests(self, api_client, sample_test):
        """Test listing tests."""
        response = api_client.get('/api/v1/diagnostics/tests/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) > 0

    @pytest.mark.django_db
    def test_search_tests_by_name(self, api_client):
        """Test searching tests by name."""
        DiagnosticTest.objects.create(name='Blood Test', description='Count')
        DiagnosticTest.objects.create(name='ECG', description='Heart')

        response = api_client.get('/api/v1/diagnostics/tests/?search=Blood')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == 'Blood Test'


class TestCentreTestRelationship:
    """Tests for centre-test relationships."""

    @pytest.mark.django_db
    def test_list_centre_tests(self, api_client, sample_centre_test):
        """Test listing centre-test relationships."""
        response = api_client.get('/api/v1/diagnostics/centre-tests/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) > 0

    @pytest.mark.django_db
    def test_filter_centre_tests_by_centre(self, api_client):
        """Test filtering centre-tests by centre."""
        centre1 = DiagnosticCentre.objects.create(
            name='Centre 1', address='123', city='City1', phone='1111111111'
        )
        centre2 = DiagnosticCentre.objects.create(
            name='Centre 2', address='456', city='City2', phone='2222222222'
        )
        test = DiagnosticTest.objects.create(name='Test A')

        CentreTest.objects.create(centre=centre1, test=test, price='500')
        CentreTest.objects.create(centre=centre2, test=test, price='600')

        response = api_client.get(f'/api/v1/diagnostics/centre-tests/?centre={centre1.id}')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['price'] == '500.00'

    @pytest.mark.django_db
    def test_centre_test_unique_constraint(self, staff_client, sample_centre_test):
        """Test that centre-test pairs are unique."""
        data = {
            'centre': sample_centre_test.centre.id,
            'test': sample_centre_test.test.id,
            'price': '600'
        }
        response = staff_client.post('/api/v1/diagnostics/centre-tests/', data, format='json')

        # Should fail due to unique constraint
        assert response.status_code == status.HTTP_400_BAD_REQUEST