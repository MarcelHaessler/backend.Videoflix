"""ffmpeg helpers: they only build and run commands, they never touch the database."""
import subprocess
from pathlib import Path

from django.conf import settings

RESOLUTIONS = [480, 720, 1080]
SEGMENT_SECONDS = 4


def hls_directory(video_id, resolution):
    """Target folder of one rendition: media/hls/<id>/<resolution>p/."""

    return Path(settings.MEDIA_ROOT) / 'hls' / str(video_id) / f'{resolution}p'


def scale_filter(resolution):
    """Scales by the shorter side, so a portrait clip does not end up stamp sized."""

    # Both expressions need the single quotes. Without them ffmpeg reads the
    # commas inside if(...) as separators between two filters.
    width = f"'if(gt(iw,ih),-2,{resolution})'"
    height = f"'if(gt(iw,ih),{resolution},-2)'"
    return f'scale={width}:{height}'


def build_hls_command(source, target_dir, resolution):
    """Encodes one rendition into numbered .ts segments plus its index.m3u8."""

    return [
        'ffmpeg', '-y', '-i', str(source),
        '-vf', scale_filter(resolution),
        '-c:v', 'libx264', '-c:a', 'aac',
        '-hls_time', str(SEGMENT_SECONDS),
        '-hls_playlist_type', 'vod',
        '-hls_segment_filename', str(target_dir / '%03d.ts'),
        str(target_dir / 'index.m3u8'),
    ]


def build_thumbnail_command(source, target):
    """Grabs a single frame one second in; that frame becomes the dashboard image."""

    return ['ffmpeg', '-y', '-ss', '1', '-i', str(source), '-vframes', '1', str(target)]


def run_ffmpeg(command):
    """Fails with ffmpeg's own message, so the reason shows up in the worker log."""

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-500:])
