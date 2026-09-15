"""Shared helpers for the test suites of both apps."""
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

TEST_PASSWORD = 'testpass123'


def create_user(email='user@test.de', password=TEST_PASSWORD, is_active=True):
    """Creates a user the way the registration does: the username is the email."""

    return User.objects.create_user(username=email, email=email,
                                    password=password, is_active=is_active)


def auth_client(user=None):
    """An APIClient carrying the access token cookie, just like a logged in browser."""

    client = APIClient()
    refresh = RefreshToken.for_user(user or create_user())
    client.cookies['access_token'] = str(refresh.access_token)
    return client
