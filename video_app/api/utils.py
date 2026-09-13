"""Path checks for the streaming endpoints; nothing here returns a Response."""
import re

from ..utils import RESOLUTIONS, hls_directory

ALLOWED_FILE = re.compile(r'^(index\.m3u8|\d{3}\.ts)$')


def checked_hls_file(movie_id, resolution, filename):
    """
    Returns the path only for a whitelisted file inside a known resolution folder.

    The three URL parts come straight from the browser, so a request like
    ``../../../etc/passwd`` must not be able to escape the media folder.
    """
    if filename_is_invalid(filename) or resolution_is_invalid(resolution):
        return None
    path = hls_directory(movie_id, resolution.rstrip('p')) / filename
    return path if path.is_file() else None


def filename_is_invalid(filename):
    """A name that does not match the pattern cannot contain a path at all."""
    return ALLOWED_FILE.match(filename) is None


def resolution_is_invalid(resolution):
    """Only the three qualities the frontend offers are served."""
    return resolution not in [f'{value}p' for value in RESOLUTIONS]
