"""Tests for the catalogue, the HLS delivery and the background conversion."""
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from core.test_utils import auth_client
from video_app.models import Video
from video_app.tasks import convert_video
from video_app.utils import build_hls_command, hls_directory, run_ffmpeg, scale_filter

MEDIA_FOR_TESTS = tempfile.mkdtemp()


def tearDownModule():
    """Removes the throwaway media folder once every test in this file has run."""
    shutil.rmtree(MEDIA_FOR_TESTS, ignore_errors=True)


def create_video(title='Testfilm', category='drama'):
    """A catalogue entry with a fake upload; nothing here is a real movie file."""
    return Video.objects.create(
        title=title,
        description='Eine Beschreibung.',
        category=category,
        video_file=SimpleUploadedFile('film.mp4', b'keine echten videodaten'),
    )


class QueueFreeTestCase(APITestCase):
    """
    Base class that keeps the conversion job out of the way.

    Saving a Video fires the post_save signal, which would push a job into Redis
    and make the real worker try to convert a fake file. Patching the queue turns
    that into a harmless mock.
    """

    def setUp(self):
        """addCleanup stops the patch again, even if the test fails midway."""
        patcher = patch('video_app.signals.django_rq.get_queue')
        self.queue = patcher.start()
        self.addCleanup(patcher.stop)


@override_settings(MEDIA_ROOT=MEDIA_FOR_TESTS)
class VideoModelTests(QueueFreeTestCase):
    """The model decides how entries are named and in which order they arrive."""

    def test_str_returns_title(self):
        """__str__ shows up in the admin list, so it has to be the title."""
        video = create_video(title='Gardasee')
        self.assertEqual(str(video), 'Gardasee')

    def test_newest_video_comes_first(self):
        """The dashboard shows the first entry as hero teaser, so it has to be the latest."""

        create_video(title='Alt')
        create_video(title='Neu')
        self.assertEqual(Video.objects.first().title, 'Neu')


@override_settings(MEDIA_ROOT=MEDIA_FOR_TESTS)
class VideoListTests(QueueFreeTestCase):
    """The dashboard list is the only endpoint that returns catalogue data."""

    def setUp(self):
        """One entry plus a logged in client, as the dashboard would have it."""
        super().setUp()
        self.video = create_video()
        self.url = reverse('video-list')

    def test_list_requires_login(self):
        """A fresh client has no cookie, so the list must answer 401."""
        response = APIClient().get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_entry(self):
        """The dashboard shows the title, description, category and thumbnail URL."""

        response = auth_client().get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_thumbnail_url_is_absolute(self):
        """The API returns a full URL, because the frontend runs on a different port."""

        self.video.thumbnail.name = 'thumbnails/1.jpg'
        self.video.save(update_fields=['thumbnail'])
        response = auth_client().get(self.url)
        url = response.data[0]['thumbnail_url']
        self.assertTrue(url.startswith('http'))

    def test_thumbnail_url_is_none_before_conversion(self):
        """The API returns None, because the background job has not yet created a thumbnail."""

        self.video.thumbnail = None
        self.video.save(update_fields=['thumbnail'])
        response = auth_client().get(self.url)
        self.assertIsNone(response.data[0]['thumbnail_url'])


@override_settings(MEDIA_ROOT=MEDIA_FOR_TESTS)
class HLSDeliveryTests(QueueFreeTestCase):
    """Playlist and segments, including the checks that block made up paths."""

    def setUp(self):
        """Writes a fake playlist and a fake segment where the views look for them."""
        super().setUp()
        self.video = create_video()
        self.client = auth_client()
        directory = hls_directory(self.video.id, 480)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'index.m3u8').write_text('#EXTM3U')
        (directory / '000.ts').write_bytes(b'segmentdaten')

    def test_playlist_is_delivered(self):
        """The player fetches this file first, so it has to arrive as a whole."""
        url = reverse('hls-playlist', args=[self.video.id, '480p'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(b''.join(response.streaming_content), b'#EXTM3U')

    def test_segment_is_delivered(self):
        """The player fetches this file next, so it has to arrive as a whole."""

        url = reverse('hls-segment', args=[self.video.id, '480p', '000.ts'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unknown_resolution_is_not_found(self):
        """The player only asks for the three qualities the frontend offers."""

        args = [self.video.id, '360p']
        url = reverse('hls-playlist', args=args)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_segment_is_not_found(self):
        """The player only asks for segments that actually exist."""

        args = [self.video.id, '480p', '999.ts']
        url = reverse('hls-segment', args=args)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_playlist_requires_login(self):
        """The player has no cookie, so the list must answer 401."""

        response = APIClient().get(reverse('hls-playlist', args=[self.video.id, '480p']))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(MEDIA_ROOT=MEDIA_FOR_TESTS)
class ConversionTests(QueueFreeTestCase):
    """
    The conversion job, with ffmpeg replaced by a mock.

    Running the real encoder would take minutes and needs a real movie file.
    Patching run_ffmpeg lets us check WHICH commands would be executed instead.
    """

    def setUp(self):
        """One entry to convert, plus a patch that swallows every ffmpeg call."""
        super().setUp()
        self.video = create_video()
        patcher = patch('video_app.tasks.run_ffmpeg')
        self.ffmpeg = patcher.start()
        self.addCleanup(patcher.stop)

    def test_every_resolution_is_encoded(self):
        """Three qualities plus one thumbnail means four calls, not three."""
        convert_video(self.video.id)
        self.assertEqual(self.ffmpeg.call_count, 4)

    def test_thumbnail_is_stored_on_the_model(self):
        """The API returns the relative path, which the frontend turns into a URL."""

        convert_video(self.video.id)
        self.video.refresh_from_db()
        self.assertEqual(self.video.thumbnail.name, f'thumbnails/{self.video.id}.jpg')

    def test_command_contains_the_resolution(self):
        """The scale filter is the only place where the quality is mentioned."""

        command = build_hls_command('quelle.mp4', Path('/tmp'), 720)
        self.assertIn('720', ' '.join(command))

    def test_portrait_is_scaled_by_its_shorter_side(self):
        """The scale filter has to keep the aspect ratio, not stamp the clip down."""

        self.assertEqual(scale_filter(480),
                         "scale='if(gt(iw,ih),-2,480)':'if(gt(iw,ih),480,-2)'")

    def test_failing_ffmpeg_raises(self):
        """The worker log must show the reason, not just a generic RuntimeError."""

        patcher = patch('video_app.utils.subprocess.run')
        fake = patcher.start()
        self.addCleanup(patcher.stop)
        fake.return_value.returncode = 1
        fake.return_value.stderr = 'kaputt'
        with self.assertRaises(RuntimeError):
            run_ffmpeg(['ffmpeg'])


@override_settings(MEDIA_ROOT=MEDIA_FOR_TESTS)
class SignalTests(QueueFreeTestCase):
    """The signal decides when a job is queued, and just as importantly when not."""

    def test_new_upload_is_queued(self):
        """Uploading has to trigger exactly one job."""
        create_video()
        self.queue.return_value.enqueue.assert_called_once()

    def test_editing_does_not_requeue(self):
        """Changing the title must not start a new conversion job."""

        video = create_video()
        self.queue.reset_mock()
        video.title = 'Neuer Titel'
        video.save()
        self.queue.return_value.enqueue.assert_not_called()
