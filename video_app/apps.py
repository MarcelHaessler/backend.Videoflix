"""App registration for the video catalogue and the HLS delivery."""
from django.apps import AppConfig


class VideoAppConfig(AppConfig):
    """Videos, their ffmpeg conversion and the streaming endpoints."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'video_app'
