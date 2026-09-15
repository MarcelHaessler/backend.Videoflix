"""Routes of the video endpoints, mounted below /api/ by core.urls."""
from django.urls import path

from .views import HLSPlaylistView, HLSSegmentView, VideoListView

urlpatterns = [
    path('video/', VideoListView.as_view(), name='video-list'),
    path('video/<int:movie_id>/<str:resolution>/index.m3u8', HLSPlaylistView.as_view(),
         name='hls-playlist'),
    # The docs spell the segment path with a trailing slash, while hls.js resolves
    # it relative to the playlist and sends it without. Both spellings are routed.
    path('video/<int:movie_id>/<str:resolution>/<str:segment>/', HLSSegmentView.as_view(),
         name='hls-segment'),
    path('video/<int:movie_id>/<str:resolution>/<str:segment>', HLSSegmentView.as_view(),
         name='hls-segment-no-slash'),
]
