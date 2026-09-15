# Videoflix Backend

REST API for the Videoflix video streaming platform. It handles user accounts,
sends activation and password reset mails, converts uploaded movies into HLS
streams with ffmpeg and serves those streams to the frontend.

Built with Django and the Django REST Framework. The whole project runs in
Docker: Django with Gunicorn, PostgreSQL as database, Redis as cache and queue
backend, and a Django RQ worker that does the video conversion in the
background.

## Table of contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Getting started](#getting-started)
- [Environment variables](#environment-variables)
- [Adding videos](#adding-videos)
- [API endpoints](#api-endpoints)
- [Authentication](#authentication)
- [Running the tests](#running-the-tests)
- [Project structure](#project-structure)
- [Frontend](#frontend)

## Features

- Registration with an activation mail; accounts stay locked until the link in
  that mail is opened.
- Login, logout and token refresh, all based on JWTs stored in HttpOnly cookies.
- Password reset by mail, with a link that can only be used once.
- Uploaded videos are converted to HLS in 480p, 720p and 1080p, and a thumbnail
  is taken from the movie itself. The conversion runs as a background job, so
  the upload form returns immediately.
- The dashboard list and every HLS file require a valid session.

## Tech stack

| Component | Version |
| --- | --- |
| Python | 3.12 |
| Django | 5.2 LTS |
| Django REST Framework | 3.18 |
| Simple JWT | 5.5 |
| PostgreSQL | latest image |
| Redis | latest image |
| Django RQ | 4.2 |
| ffmpeg | installed inside the image |

## Getting started

### Requirements

- Docker with Docker Compose. Everything else runs inside the containers, so no
  local Python, PostgreSQL, Redis or ffmpeg installation is needed.
- Git.

### Setup

Clone the repository:

```bash
git clone https://github.com/MarcelHaessler/backend.Videoflix.git
```

Change into the project folder:

```bash
cd backend.Videoflix
```

Create your environment file from the template:

```bash
cp .env.template .env
```

Open `.env` and replace at least `SECRET_KEY` with a value of your own. The
database credentials and the mail settings can stay as they are for a local
run. Do not rename any variable, the containers look them up by name.

Build and start everything:

```bash
docker compose up --build
```

The API is then available at http://localhost:8000 and the Django admin at
http://localhost:8000/admin/.

The startup script waits for PostgreSQL, applies all migrations, creates the
superuser from the `DJANGO_SUPERUSER_*` variables and starts both the RQ worker
and Gunicorn.

### Mails during development

`.env.template` sets `EMAIL_BACKEND` to Django's console backend. Activation and
reset mails are printed to the container log instead of being sent, which keeps
the setup working without an SMTP account:

```bash
docker compose logs web
```

To send real mails, remove that line from `.env` and fill in the `EMAIL_HOST`,
`EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` variables.

## Environment variables

| Name | Description | Default |
| --- | --- | --- |
| `DJANGO_SUPERUSER_USERNAME` | Admin account created on first start | `admin` |
| `DJANGO_SUPERUSER_PASSWORD` | Password of that account | `adminpassword` |
| `DJANGO_SUPERUSER_EMAIL` | Mail address of that account | `admin@example.com` |
| `SECRET_KEY` | Django cryptographic key, replace it | none |
| `DEBUG` | Debug mode; media files are only served while this is `True` | `True` |
| `ALLOWED_HOSTS` | Comma separated host names | `localhost` |
| `CSRF_TRUSTED_ORIGINS` | Comma separated frontend origins; also used for CORS | `http://localhost:4200` |
| `FRONTEND_URL` | Base address used in the links inside the mails | `http://127.0.0.1:5500` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | PostgreSQL credentials | see template |
| `DB_HOST`, `DB_PORT` | Database location inside the compose network | `db`, `5432` |
| `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_LOCATION` | Redis for cache and queue | `redis`, `6379`, `0` |
| `EMAIL_BACKEND` | Console backend for development, SMTP otherwise | console |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP settings | see template |
| `EMAIL_USE_TLS`, `EMAIL_USE_SSL` | Transport encryption | `True`, `False` |
| `DEFAULT_FROM_EMAIL` | Sender address of the mails | `EMAIL_HOST_USER` |
| `AUTH_COOKIE_SECURE` | Set to `True` when serving over HTTPS | `False` |
| `AUTH_COOKIE_SAMESITE` | SameSite policy of the JWT cookies | `Lax` |

## Adding videos

The API has no upload endpoint by design. Movies are added through the Django
admin:

1. Open http://localhost:8000/admin/ and log in with the superuser.
2. Choose **Videos**, then **Add video**.
3. Fill in title, description and category and pick a video file.

Saving queues a background job. The worker encodes the movie into the three
qualities, cuts a thumbnail one second in and stores its path on the record.
Progress and errors show up in the log:

```bash
docker compose logs -f web
```

The queue can also be inspected at http://localhost:8000/django-rq/ while logged
in as superuser.

Rendition sizes follow the shorter side of the picture. A landscape movie
becomes 854x480, 1280x720 and 1920x1080, a portrait clip becomes 480x854,
720x1280 and 1080x1920.

## API endpoints

All routes live below `/api/`.

### Accounts

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `register/` | Creates a locked account and sends the activation mail |
| GET | `activate/<uidb64>/<token>/` | Unlocks the account behind the link |
| POST | `login/` | Checks the credentials and sets both cookies |
| POST | `logout/` | Blacklists the refresh token and clears the cookies |
| POST | `token/refresh/` | Issues a new access token from the refresh cookie |
| POST | `password_reset/` | Sends the reset mail |
| POST | `password_confirm/<uidb64>/<token>/` | Stores the new password |

### Videos

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `video/` | Catalogue for the dashboard, newest entry first |
| GET | `video/<id>/<resolution>/index.m3u8` | HLS playlist of one quality |
| GET | `video/<id>/<resolution>/<segment>/` | One HLS segment, for example `000.ts` |

`resolution` is one of `480p`, `720p` or `1080p`. Any other value, and any file
name that is not a playlist or a numbered segment, answers with 404.

## Authentication

The frontend never receives the tokens. Login puts both of them into HttpOnly
cookies named `access_token` and `refresh_token`, and the browser sends them
along automatically. JavaScript cannot read them, which is why no request
carries an Authorization header.

Two consequences worth knowing:

- Requests from the frontend need `credentials: 'include'`, and the frontend
  origin has to be listed in `CSRF_TRUSTED_ORIGINS`.
- Open the frontend on the same host name as the API. `127.0.0.1` and
  `localhost` count as different sites for cookies, so mixing them silently
  drops the session.

Error responses stay deliberately vague. A wrong password, an unknown address
and a locked account all produce the same message, so the API cannot be used to
find out which addresses are registered.

## Running the tests

`coverage` and `flake8` are development tools and are not part of
`requirements.txt`. Install them inside the running container:

```bash
docker compose exec web pip install coverage flake8
```

Run the test suite:

```bash
docker compose exec web python manage.py test
```

Measure the coverage:

```bash
docker compose exec web coverage run --source='.' --omit='*/migrations/*,manage.py,*/tests.py,core/test_utils.py,core/wsgi.py,core/asgi.py' manage.py test
```

Show the report:

```bash
docker compose exec web coverage report
```

Check the code style:

```bash
docker compose exec web flake8 auth_app/ video_app/ core/
```

The suite contains 42 tests and covers 99 percent of the project. ffmpeg is
replaced by a mock during the tests, so no encoding happens and the suite
finishes in a few seconds.

## Project structure

```
backend.Videoflix/
├── core/                    Project settings, root URLs, shared test helpers
├── auth_app/
│   ├── api/                 Serializers, views, cookie authentication, helpers
│   ├── templates/auth_app/  HTML bodies of the activation and reset mails
│   └── tests.py
├── video_app/
│   ├── api/                 Serializers, views and path checks for HLS
│   ├── models.py            The Video model
│   ├── tasks.py             Background job: renditions and thumbnail
│   ├── utils.py             ffmpeg command builders
│   ├── signals.py           Queues the job when a video is uploaded
│   └── tests.py
├── backend.Dockerfile       Image with Python, ffmpeg and PostgreSQL client
├── backend.entrypoint.sh    Migrations, superuser, RQ worker, Gunicorn
├── docker-compose.yml       Services web, db and redis
└── .env.template            Template for your own .env
```

Helper functions live in `utils.py` files, so views only build responses.

## Frontend

The matching frontend is a separate project and is not part of this repository.
It was provided by the Developer Akademie. Serve it on the origin configured in
`CSRF_TRUSTED_ORIGINS` and `FRONTEND_URL`, by default http://127.0.0.1:5500.
