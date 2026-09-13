"""Helper functions for the auth endpoints (nothing in here returns a Response)."""
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode


def build_activation_link(user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f'{settings.FRONTEND_URL}/pages/auth/activate.html?uid={uidb64}&token={token}'


def send_activation_email(user):
    context = {'user': user, 'activation_link': build_activation_link(user)}
    html_body = render_to_string('auth_app/activation_email.html', context)
    message = EmailMultiAlternatives(
        subject='Confirm your email',
        body=f'Activate your account: {context["activation_link"]}',
        to=[user.email],
    )
    message.attach_alternative(html_body, 'text/html')
    message.send()


def get_user_from_uidb64(uidb64):
    try:
        user_id = urlsafe_base64_decode(uidb64).decode()
        return User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None
