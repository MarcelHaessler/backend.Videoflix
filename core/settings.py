"""
Django settings for the Videoflix backend.

Configuration values come from environment variables (see .env.template),
so the same code runs locally and inside the Docker setup.
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv(  # FIX: umgebrochen, die Zeile hatte 114 Zeichen
    'SECRET_KEY',
    default='django-insecure-@#x5h3zj!g+8g1v@2^b6^9$8&f1r7g$@t3v!p4#=g0r5qzj4m3',
)

DEBUG = os.environ.get('DEBUG', default='True') == 'True'

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", default="localhost").split(",")
# FIX: umgebrochen, die Zeile hatte 105 Zeichen
CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS", default="http://localhost:4200"
).split(",")

# The frontend runs on its own origin and sends the JWT cookies along.
CORS_ALLOWED_ORIGINS = CSRF_TRUSTED_ORIGINS
CORS_ALLOW_CREDENTIALS = True

# Base URL of the frontend, used for the links inside activation/reset emails.
FRONTEND_URL = os.environ.get("FRONTEND_URL", default="http://127.0.0.1:5500")


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_rq',
    'rest_framework',
    'corsheaders',
    'rest_framework_simplejwt.token_blacklist',
    'auth_app',
    'video_app',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'auth_app.api.authentication.CookieJWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_COOKIE_ACCESS': 'access_token',
    'AUTH_COOKIE_REFRESH': 'refresh_token',
    'AUTH_COOKIE_SECURE': os.environ.get('AUTH_COOKIE_SECURE', default='False') == 'True',
    'AUTH_COOKIE_SAMESITE': os.environ.get('AUTH_COOKIE_SAMESITE', default='Lax'),
}

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database (PostgreSQL, provided by the "db" service in docker-compose)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", default="videoflix_db"),
        "USER": os.environ.get("DB_USER", default="videoflix_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD", default="supersecretpassword"),
        "HOST": os.environ.get("DB_HOST", default="db"),
        "PORT": os.environ.get("DB_PORT", default=5432)
    }
}


# Redis: cache layer and queue backend for Django RQ

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_LOCATION", default="redis://redis:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient"
        },
        "KEY_PREFIX": "videoflix"
    }
}

RQ_QUEUES = {
    'default': {
        'HOST': os.environ.get("REDIS_HOST", default="redis"),
        'PORT': os.environ.get("REDIS_PORT", default=6379),
        'DB': os.environ.get("REDIS_DB", default=0),
        'DEFAULT_TIMEOUT': 900,
        'REDIS_CLIENT_KWARGS': {},
    },
}


# Email (activation and password reset mails)

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", default="smtp.example.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", default=587))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", default="True") == "True"
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", default="False") == "True"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER)


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static and media files

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
