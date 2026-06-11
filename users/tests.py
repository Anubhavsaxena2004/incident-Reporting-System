from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class UserAuthTests(APITestCase):
    def setUp(self):
        self.register_url = reverse('auth_register')
        self.login_url = reverse('auth_login')
        self.refresh_url = reverse('token_refresh')
        self.logout_url = reverse('auth_logout')
        self.profile_url = reverse('user_profile')

        self.user_data = {
            'username': 'testcitizen',
            'email': 'citizen@test.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '1234567890',
            'role': 'CITIZEN',
            'password': 'SecurePassword123!'
        }

    def test_user_registration_success(self):
        """
        Verify that a new user registers successfully and gets Citizen role by default.
        """
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], self.user_data['username'])
        self.assertEqual(response.data['role'], 'CITIZEN')
        self.assertNotIn('password', response.data)

        # Check in DB
        user_exists = User.objects.filter(username=self.user_data['username']).exists()
        self.assertTrue(user_exists)

    def test_user_registration_missing_fields(self):
        """
        Verify registration fails when mandatory fields like password are omitted.
        """
        bad_data = self.user_data.copy()
        del bad_data['password']
        response = self.client.post(self.register_url, bad_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_user_login_success(self):
        """
        Verify user logins successfully, receiving access and refresh tokens, and profile context.
        """
        # Register first
        self.client.post(self.register_url, self.user_data)

        # Attempt Login
        login_data = {
            'username': self.user_data['username'],
            'password': self.user_data['password']
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], self.user_data['username'])
        self.assertEqual(response.data['user']['role'], 'CITIZEN')

    def test_user_login_wrong_credentials(self):
        """
        Verify login fails with incorrect password.
        """
        self.client.post(self.register_url, self.user_data)

        login_data = {
            'username': self.user_data['username'],
            'password': 'WrongPassword123'
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', response.data)

    def test_token_refresh_success(self):
        """
        Verify issuing a new access token via a refresh token.
        """
        self.client.post(self.register_url, self.user_data)
        login_data = {
            'username': self.user_data['username'],
            'password': self.user_data['password']
        }
        login_response = self.client.post(self.login_url, login_data)
        refresh_token = login_response.data['refresh']

        # Refresh call
        response = self.client.post(self.refresh_url, {'refresh': refresh_token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_user_profile_authenticated(self):
        """
        Verify fetching and editing profile details for logged in user.
        """
        self.client.post(self.register_url, self.user_data)
        login_data = {
            'username': self.user_data['username'],
            'password': self.user_data['password']
        }
        login_response = self.client.post(self.login_url, login_data)
        access_token = login_response.data['access']

        # Set Bearer Auth Header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Get profile details
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.user_data['username'])

        # Update profile details
        patch_data = {'first_name': 'Jonathan', 'phone_number': '9999999999'}
        response = self.client.patch(self.profile_url, patch_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Jonathan')
        self.assertEqual(response.data['phone_number'], '9999999999')

    def test_user_profile_unauthenticated(self):
        """
        Verify unauthenticated users are blocked from viewing profiles.
        """
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_logout_success(self):
        """
        Verify blacklisting refresh token on logout.
        """
        self.client.post(self.register_url, self.user_data)
        login_data = {
            'username': self.user_data['username'],
            'password': self.user_data['password']
        }
        login_response = self.client.post(self.login_url, login_data)
        access_token = login_response.data['access']
        refresh_token = login_response.data['refresh']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Logout post
        response = self.client.post(self.logout_url, {'refresh': refresh_token})
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

        # Verify old refresh token is blacklisted and cannot be reused to get a new access token
        refresh_response = self.client.post(self.refresh_url, {'refresh': refresh_token})
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)
