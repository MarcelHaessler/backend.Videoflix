"""Background jobs. The RQ worker inside the Docker container executes them."""
from pathlib import Path

from django.conf import settings

from .models import Video
from .utils import (RESOLUTIONS, build_hls_command, build_thumbnail_command, hls_directory,
                    run_ffmpeg)


def convert_video(video_id):
    """Queue entry point. Takes the id, not the object, because jobs are serialised."""
    video = Video.objects.get(pk=video_id)
    source = Path(video.video_file.path)
    for resolution in RESOLUTIONS:
        create_rendition(source, video_id, resolution)
    create_thumbnail(video, source)


def create_rendition(source, video_id, resolution):
    """One quality level; the folder has to exist before ffmpeg writes into it."""
    target_dir = hls_directory(video_id, resolution)
    target_dir.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(build_hls_command(source, target_dir, resolution))


def create_thumbnail(video, source):
    """Writes the frame and stores its relative path, which the API turns into a URL."""
    target = Path(settings.MEDIA_ROOT) / 'thumbnails' / f'{video.id}.jpg'
    target.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(build_thumbnail_command(source, target))
    video.thumbnail.name = f'thumbnails/{video.id}.jpg'
    video.save(update_fields=['thumbnail'])
