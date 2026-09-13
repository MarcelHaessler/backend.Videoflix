"""Endpoints for account creation and for the cookie based JWT session."""
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (LoginSerializer, PasswordConfirmSerializer,
                          PasswordResetSerializer, RegistrationSerializer)
from .utils import (blacklist_refresh_token, delete_auth_cookies, get_user_from_uidb64,
                    send_activation_email, send_password_reset_email, set_access_cookie,
                    set_auth_cookies)

LOGOUT_MESSAGE = ('Logout successful! All tokens will be deleted. '
                  'Refresh token is now invalid.')
MISSING_REFRESH = {'detail': 'Refresh token not found.'}
INVALID_REFRESH = {'detail': 'Refresh token invalid.'}
RESET_SENT_MESSAGE = 'An email has been sent to reset your password.'
RESET_DONE_MESSAGE = 'Your Password has been successfully reset.'


class RegistrationView(APIView):
    """Creates the account and triggers the activation mail."""

    permission_classes = [AllowAny]

    def post(self, request):
        """The returned token is informational only; the frontend uses the mailed link."""
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_activation_email(user)
        return Response({
            'user': {'id': user.id, 'email': user.email},
            'token': default_token_generator.make_token(user)
        }, status=status.HTTP_201_CREATED)


class ActivationView(APIView):
    """Unlocks an account when the link from the activation mail is opened."""

    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        """A tampered link or a token that no longer matches the user ends in 400."""
        user = get_user_from_uidb64(uidb64)
        if user is None or not default_token_generator.check_token(user, token):
            return Response({'message': 'Activation failed.'}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = True
        user.save()
        return Response({'message': 'Account successfully activated.'}, status=status.HTTP_200_OK)


class LoginView(APIView):
    """Issues the JWT pair and hands it to the browser as HttpOnly cookies."""

    permission_classes = [AllowAny]

    def post(self, request):
        """The response is built first, because both cookies are attached to it afterwards."""
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        response = Response({
            'detail': 'Login successful',
            'user': {'id': user.id, 'username': user.username},
        }, status=status.HTTP_200_OK)
        set_auth_cookies(response, refresh.access_token, refresh)
        return response


class LogoutView(APIView):
    """Blacklists the refresh token so it cannot be traded for new access tokens."""

    permission_classes = [AllowAny]

    def post(self, request):
        """An expired token still logs the user out; only a missing cookie is an error."""
        raw_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'])
        if raw_token is None:
            return Response(MISSING_REFRESH, status=status.HTTP_400_BAD_REQUEST)
        blacklist_refresh_token(raw_token)
        response = Response({'detail': LOGOUT_MESSAGE}, status=status.HTTP_200_OK)
        delete_auth_cookies(response)
        return response


class CookieTokenRefreshView(APIView):
    """Hands out a fresh access token, which the frontend asks for every 20 minutes."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Reads the refresh token from the cookie, since the frontend cannot send a body."""
        raw_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'])
        if raw_token is None:
            return Response(MISSING_REFRESH, status=status.HTTP_400_BAD_REQUEST)
        try:
            refresh = RefreshToken(raw_token)
        except TokenError:
            return Response(INVALID_REFRESH, status=status.HTTP_401_UNAUTHORIZED)
        access = refresh.access_token
        payload = {'detail': 'Token refreshed', 'access': str(access)}
        response = Response(payload, status=status.HTTP_200_OK)
        set_access_cookie(response, access)
        return response


class PasswordResetView(APIView):
    """Sends the reset mail without telling the caller whether the account exists."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Always answers 200, otherwise the endpoint would reveal registered addresses."""
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email=serializer.validated_data['email']).first()
        if user is not None:
            send_password_reset_email(user)
        return Response({'detail': RESET_SENT_MESSAGE}, status=status.HTTP_200_OK)


class PasswordConfirmView(APIView):
    """Stores the new password once the link from the mail proves to be valid."""

    permission_classes = [AllowAny]

    def post(self, request, uidb64, token):
        """Same link check as the activation; a used or tampered link ends in 400."""
        serializer = PasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_user_from_uidb64(uidb64)
        if user is None or not default_token_generator.check_token(user, token):
            return Response({'detail': 'Reset failed.'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'detail': RESET_DONE_MESSAGE}, status=status.HTTP_200_OK)
