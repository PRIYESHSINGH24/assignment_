import pytest
from django.contrib.auth import get_user_model
from rest_framework import status


class TestSignup:

    @pytest.mark.django_db
    def test_signup_success(self, api_client):
        User = get_user_model()
        data = {
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
            'first_name': 'New',
            'last_name': 'User',
        }
        response = api_client.post('/api/v1/auth/signup/', data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['email'] == 'newuser@example.com'
        assert 'password' not in response.data
        assert User.objects.filter(email='newuser@example.com').exists()

    @pytest.mark.django_db
    def test_signup_duplicate_email(self, api_client, authenticated_user):
        data = {
            'email': authenticated_user.email,
            'password': 'securepass123',
            'password_confirm': 'securepass123',
        }
        response = api_client.post('/api/v1/auth/signup/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data

    @pytest.mark.django_db
    def test_signup_password_mismatch(self, api_client):
        """Test signup with mismatched passwords."""
        data = {
            'email': 'user@example.com',
            'password': 'securepass123',
            'password_confirm': 'differentpass123',
        }
        response = api_client.post('/api/v1/auth/signup/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in response.data

    @pytest.mark.django_db
    def test_signup_short_password(self, api_client):
        """Test signup with password shorter than 8 characters."""
        data = {
            'email': 'user@example.com',
            'password': 'short',
            'password_confirm': 'short',
        }
        response = api_client.post('/api/v1/auth/signup/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestLogin:
    """Tests for user login."""

    @pytest.mark.django_db
    def test_login_success(self, api_client, authenticated_user):
        """Test successful login."""
        data = {
            'email': authenticated_user.email,
            'password': 'testpass123',
        }
        response = api_client.post('/api/v1/auth/login/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert response.data['user']['email'] == authenticated_user.email

    @pytest.mark.django_db
    def test_login_invalid_email(self, api_client):
        """Test login with non-existent email."""
        data = {
            'email': 'nonexistent@example.com',
            'password': 'password123',
        }
        response = api_client.post('/api/v1/auth/login/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'non_field_errors' in response.data

    @pytest.mark.django_db
    def test_login_invalid_password(self, api_client, authenticated_user):
        """Test login with wrong password."""
        data = {
            'email': authenticated_user.email,
            'password': 'wrongpassword',
        }
        response = api_client.post('/api/v1/auth/login/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestProfile:
    """Tests for protected profile endpoint."""

    @pytest.mark.django_db
    def test_profile_authenticated(self, authenticated_client, authenticated_user):
        """Test profile access with authentication."""
        response = authenticated_client.get('/api/v1/auth/profile/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == authenticated_user.email

    @pytest.mark.django_db
    def test_profile_unauthenticated(self, api_client):
        """Test profile access without authentication."""
        response = api_client.get('/api/v1/auth/profile/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'detail' in response.data


class TestTokenRefresh:
    """Tests for token refresh."""

    @pytest.mark.django_db
    def test_token_refresh_success(self, api_client, authenticated_user):
        """Test successful token refresh."""
        # First login to get tokens
        login_data = {
            'email': authenticated_user.email,
            'password': 'testpass123',
        }
        login_response = api_client.post('/api/v1/auth/login/', login_data, format='json')
        refresh_token = login_response.data['refresh']

        # Use refresh token to get new access token
        refresh_data = {'refresh': refresh_token}
        response = api_client.post('/api/v1/auth/token/refresh/', refresh_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    @pytest.mark.django_db
    def test_token_refresh_invalid(self, api_client):
        """Test token refresh with invalid token."""
        data = {'refresh': 'invalid-token'}
        response = api_client.post('/api/v1/auth/token/refresh/', data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED