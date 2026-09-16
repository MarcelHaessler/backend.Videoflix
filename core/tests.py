"""Tests for the helpers that translate environment values into settings."""
from django.test import SimpleTestCase

from core.env_utils import pick_sender_address


class SenderAddressTests(SimpleTestCase):
    """The sender has to be a real address, whatever the .env contains."""

    def test_configured_address_wins(self):
        """An address in DEFAULT_FROM_EMAIL is used as it is."""

        self.assertEqual(pick_sender_address('info@videoflix.de', 'user@web.de'),
                         'info@videoflix.de')

    def test_placeholder_falls_back_to_host_user(self):
        """.env.template ships "default_from_email", which is not an address."""

        self.assertEqual(pick_sender_address('default_from_email', 'user@web.de'),
                         'user@web.de')

    def test_empty_value_falls_back_to_host_user(self):
        """The template now leaves the variable empty on purpose."""

        self.assertEqual(pick_sender_address('', 'user@web.de'), 'user@web.de')

    def test_two_placeholders_end_in_the_fallback(self):
        """Without any usable address the mail still needs a sender."""

        self.assertEqual(pick_sender_address('', 'your_email_user'),
                         'noreply@videoflix.local')
