"""Dashboard list plus the two endpoints that hand out the HLS files."""
from django.http import FileResponse, Http404
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView

from ..models import Video
from .serializers import VideoSerializer
from .utils import checked_hls_file

PLAYLIST_TYPE = 'application/vnd.apple.mpegurl'
SEGMENT_TYPE = 'video/MP2T'


class VideoListView(ListAPIView):
    """Newest first, because the frontend shows the first entry as hero teaser."""

    queryset = Video.objects.all()
    serializer_class = VideoSerializer


class HLSPlaylistView(APIView):
    """Hands out index.m3u8, the table of contents of one quality level."""

    def get(self, request, movie_id, resolution):
        """The player reads this file first and then requests the segments itself."""

        path = checked_hls_file(movie_id, resolution, 'index.m3u8')
        if path is None:
            raise Http404
        return FileResponse(open(path, 'rb'), content_type=PLAYLIST_TYPE)


class HLSSegmentView(APIView):
    """Hands out a single .ts chunk of about four seconds."""

    def get(self, request, movie_id, resolution, segment):
        """Same pattern as the playlist, only with the segment name from the URL."""

        path = checked_hls_file(movie_id, resolution, segment)
        if path is None:
            raise Http404
        return FileResponse(open(path, 'rb'), content_type=SEGMENT_TYPE)
