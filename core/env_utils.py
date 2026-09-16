"""Helpers that turn raw environment values into settings."""


def pick_sender_address(configured, host_user, fallback='noreply@videoflix.local'):
    """
    Chooses the address the mails are sent from.

    .env.template ships placeholders like "default_from_email". Those are set,
    but they are not addresses, so a plain "is it set" check would let them
    through and every send would fail on the mail server.
    """

    if configured and '@' in configured:
        return configured
    if host_user and '@' in host_user:
        return host_user
    return fallback
