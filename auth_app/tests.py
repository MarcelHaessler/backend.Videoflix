"""Tests for registration, activation and the cookie based session."""
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from core.test_utils import TEST_PASSWORD, create_user


class RegistrationTests(APITestCase):
    """Covers the sign-up endpoint including its two validation errors."""

    def setUp(self):
        """Runs before every single test, so each one starts from the same state."""
        self.url = reverse('register')
        self.payload = {
            'email': 'neu@test.de',
            'password': TEST_PASSWORD,
            'confirmed_password': TEST_PASSWORD,
        }

    def test_registration_creates_inactive_user(self):
        """The account must exist but stay locked until the mail link is used."""
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email='neu@test.de')
        self.assertFalse(user.is_active)

    def test_registration_sends_activation_email(self):
        """The mail is sent to the address from the form, not to a hard-coded one."""

        self.client.post(self.url, self.payload)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['neu@test.de'])

    def test_registration_rejects_duplicate_email(self):
        """Django allows duplicate emails, so the uniqueness check has to happen here."""

        create_user(email='neu@test.de')
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_rejects_mismatched_passwords(self):
        """The form has two password fields to avoid typos; they must match."""

        self.payload['confirmed_password'] = 'anderes123'
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email='neu@test.de').exists())


def activation_url(user):
    """Builds the same link the activation mail contains, but as a backend route."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return reverse('activate', args=[uidb64, token])


class ActivationTests(APITestCase):
    """Covers the link check: only an untouched link unlocks the account."""

    def setUp(self):
        """Every test starts with a locked account, as registration leaves it."""
        self.user = create_user(email='locked@test.de', is_active=False)

    def test_valid_link_activates_account(self):
        """After the call the flag in the database has to be True."""
        response = self.client.get(activation_url(self.user))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_wrong_token_is_rejected(self):
        """A token that no longer matches the user ends in 400, not 500."""

        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        url = reverse('activate', args=[uidb64, 'kaputt-token'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_broken_uid_is_rejected(self):
        """A tampered uidb64 yields None from get_user_from_uidb64, which ends in 400."""

        url = reverse('activate', args=['kaputt-uid', 'irgendein-token'])
        self.assertEqual(self.client.get(url).status_code, status.HTTP_400_BAD_REQUEST)

    def test_link_stays_valid_after_activation(self):
        """
        Activating twice is harmless and stays at 200.

        Django hashes pk, password, last_login and email into the token. None of
        those change when is_active is set, so the link keeps working. The reset
        link behaves differently because the password hash changes there.
        """
        url = activation_url(self.user)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)


class LoginTests(APITestCase):
    """Login has to hand out both cookies and stay vague about the reason for failures."""

    def setUp(self):
        """An activated account, because a locked one can never log in."""
        self.url = reverse('login')
        self.user = create_user(email='aktiv@test.de')
        self.credentials = {'email': 'aktiv@test.de', 'password': TEST_PASSWORD}

    def test_login_sets_both_cookies(self):
        """The frontend never sees the tokens, so they have to arrive as cookies."""
        response = self.client.post(self.url, self.credentials)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)

    def test_cookies_are_httponly(self):
        """The browser cannot read the tokens, so JavaScript cannot steal them."""

        response = self.client.post(self.url, self.credentials)
        self.assertTrue(response.cookies['access_token']['httponly'])

    def test_wrong_password_is_rejected(self):
        """The error message is the same as for inactive accounts, so no hints are given."""

        self.credentials['password'] = 'falsch123'
        response = self.client.post(self.url, self.credentials)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_user_cannot_log_in(self):
        """The error message is the same as for wrong passwords, so no hints are given."""

        create_user(email='gesperrt@test.de', is_active=False)
        response = self.client.post(self.url, {'email': 'gesperrt@test.de',
                                               'password': TEST_PASSWORD})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SessionTests(APITestCase):
    """Logout and refresh, both of which read the refresh token from the cookie."""

    def setUp(self):
        """Logging in first, because the test client keeps the cookies afterwards."""
        self.user = create_user(email='session@test.de')
        self.client.post(reverse('login'), {'email': 'session@test.de',
                                            'password': TEST_PASSWORD})

    def test_logout_clears_cookies(self):
        """An empty cookie value is how the browser is told to drop it."""
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.cookies['access_token'].value, '')

    def test_refresh_returns_new_access_token(self):
        """The refresh token is only ever sent to the auth endpoints, not to the frontend."""

        response = self.client.post(reverse('token_refresh'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_refresh_fails_after_logout(self):
        """Logout empties the cookie, and an empty token counts as missing, not invalid."""

        self.client.post(reverse('logout'))
        refresh_response = self.client.post(reverse('token_refresh'))
        self.assertEqual(refresh_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_without_cookie_is_bad_request(self):
        """The refresh token is missing, so the call ends in 400 Bad Request."""

        fresh = APIClient()  # ein Client ganz ohne Cookies
        response = fresh.post(reverse('logout'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_refresh_with_broken_cookie_is_unauthorized(self):
        """A token that is present but unusable is 401, unlike a missing one, which is 400."""
        fresh = APIClient()
        fresh.cookies['refresh_token'] = 'kaputt'
        response = fresh.post(reverse('token_refresh'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


def confirm_url(user):
    """The link from the reset mail, pointing at the backend route this time."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return reverse('password_confirm', args=[uidb64, token])


class PasswordResetRequestTests(APITestCase):
    """The request endpoint must not reveal which addresses are registered."""

    def setUp(self):
        """One existing account to contrast with an address nobody uses."""
        self.url = reverse('password_reset')
        self.user = create_user(email='bekannt@test.de')

    def test_known_address_receives_mail(self):
        """The happy path: status 200 and exactly one mail in the outbox."""
        response = self.client.post(self.url, {'email': 'bekannt@test.de'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

    def test_unknown_address_looks_identical(self):
        """Same status as for a known address, so nobody can probe for accounts."""
        response = self.client.post(self.url, {'email': 'niemand@test.de'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)


class PasswordConfirmTests(APITestCase):
    """Setting the new password, including the checks that protect the link."""

    def setUp(self):
        """A normal account plus the payload the reset form sends."""
        self.user = create_user(email='reset@test.de')
        self.payload = {'new_password': 'ganzneu123', 'confirm_password': 'ganzneu123'}

    def test_password_is_changed(self):
        """One call only: the second one would already run against a changed hash."""
        response = self.client.post(confirm_url(self.user), self.payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('ganzneu123'))

    def test_old_password_stops_working(self):
        """Replacing the password has to invalidate the previous one."""
        self.client.post(confirm_url(self.user), self.payload)
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password(TEST_PASSWORD))

    def test_mismatched_passwords_are_rejected(self):
        """A rejected form must leave the stored password untouched."""
        self.payload['confirm_password'] = 'anders123'
        response = self.client.post(confirm_url(self.user), self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(TEST_PASSWORD))

    def test_link_works_only_once(self):
        """set_password changes the hash, and the hash is part of the token."""
        url = confirm_url(self.user)
        first = self.client.post(url, self.payload)
        second = self.client.post(url, self.payload)
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
