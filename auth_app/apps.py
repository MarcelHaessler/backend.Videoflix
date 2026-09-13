"""App registration for the account and session endpoints."""
from django.apps import AppConfig


class AuthAppConfig(AppConfig):
    """Accounts: registration, mail activation, password reset and JWT cookie sessions."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'auth_app'
