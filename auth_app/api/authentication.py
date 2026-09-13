"""JWT authentication that reads the token from an HttpOnly cookie."""
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    The frontend never sees the token, so no Authorization header arrives.
    The access token is taken from the cookie that the login view has set.
    """

    def authenticate(self, request):
        """Without a cookie this returns None; a present but invalid token raises 401."""
        cookie_name = settings.SIMPLE_JWT['AUTH_COOKIE_ACCESS']
        raw_token = request.COOKIES.get(cookie_name)
        if raw_token is None:
            return None
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
