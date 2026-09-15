"""Helper functions for the auth endpoints (nothing in here returns a Response)."""
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


def build_frontend_link(user, page):
    """Both mails link to the frontend, which then calls this API with uid and token."""

    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f'{settings.FRONTEND_URL}/pages/auth/{page}?uid={uidb64}&token={token}'


def send_html_email(subject, template, context, recipient):
    """Sends the mail as HTML with a plain-text fallback for clients without HTML."""

    html_body = render_to_string(template, context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=context['plain_text'],
        to=[recipient],
    )
    message.attach_alternative(html_body, 'text/html')
    message.send()


def send_activation_email(user):
    """Asks the user to confirm the address before the locked account is opened."""

    link = build_frontend_link(user, 'activate.html')
    context = {'user': user, 'activation_link': link,
               'plain_text': f'Activate your account: {link}'}
    send_html_email('Confirm your email', 'auth_app/activation_email.html', context, user.email)


def send_password_reset_email(user):
    """Sends the reset link; the token dies on its own once the password changed."""

    link = build_frontend_link(user, 'confirm_password.html')
    context = {'user': user, 'reset_link': link,
               'plain_text': f'Reset your password: {link}'}
    send_html_email('Reset your Password', 'auth_app/password_reset_email.html',
                    context, user.email)


def get_user_from_uidb64(uidb64):
    """Reverses the encoding from the mail link; any tampered value yields None, not a 500."""

    try:
        user_id = urlsafe_base64_decode(uidb64).decode()
        return User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None


def set_access_cookie(response, access_token):
    """Store the access token as an HttpOnly cookie (never readable by JavaScript)."""

    response.set_cookie(
        key=settings.SIMPLE_JWT['AUTH_COOKIE_ACCESS'],
        value=str(access_token),
        httponly=True,
        secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
    )


def set_refresh_cookie(response, refresh_token):
    """Store the refresh token, which is only ever sent back to the auth endpoints."""

    response.set_cookie(
        key=settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'],
        value=str(refresh_token),
        httponly=True,
        secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
    )


def set_auth_cookies(response, access_token, refresh_token):
    """Attach both JWT cookies to a login response."""

    set_access_cookie(response, access_token)
    set_refresh_cookie(response, refresh_token)


def delete_auth_cookies(response):
    """Remove both JWT cookies so the browser is logged out afterwards."""

    response.delete_cookie(settings.SIMPLE_JWT['AUTH_COOKIE_ACCESS'])
    response.delete_cookie(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'])


def blacklist_refresh_token(raw_token):
    """Writes the token to the blacklist table; a token that is already dead is ignored."""

    try:
        refresh = RefreshToken(raw_token)
        refresh.blacklist()
    except TokenError:
        pass
