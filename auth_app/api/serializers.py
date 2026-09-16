"""Serializers for sign-up and login; both keep their error messages generic."""
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed

GENERIC_ERROR = 'Please check your input and try again.'


class RegistrationSerializer(serializers.ModelSerializer):
    """Validates the sign-up form and creates an account that stays locked."""

    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'confirmed_password']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
        }

    def validate_email(self, value):
        """Django allows duplicate emails, so the uniqueness check has to happen here."""

        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(GENERIC_ERROR)
        return value

    def validate(self, attrs):
        """Compares both password fields before any user is written to the database."""

        if attrs['password'] != attrs['confirmed_password']:
            raise serializers.ValidationError(GENERIC_ERROR)
        return attrs

    def create(self, validated_data):
        """Stores the email as username too, because the login form has no username."""

        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            is_active=False,
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Checks the credentials from the login form (email + password)."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """One shared message covers wrong credentials and accounts that are not active."""

        user = authenticate(username=attrs['email'], password=attrs['password'])
        if user is None:
            raise AuthenticationFailed(GENERIC_ERROR)
        attrs['user'] = user
        return attrs


class PasswordResetSerializer(serializers.Serializer):
    """Takes only the address; whether it exists is deliberately not revealed."""

    email = serializers.EmailField()


class PasswordConfirmSerializer(serializers.Serializer):
    """Validates the two password fields that the reset form sends."""

    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Both fields have to match before the old password is replaced."""

        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError(GENERIC_ERROR)
        return attrs
