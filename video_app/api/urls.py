"""Routes of the video endpoints, mounted below /api/ by core.urls."""
from django.urls import path

from .views import HLSPlaylistView, HLSSegmentView, VideoListView

urlpatterns = [
    path('video/', VideoListView.as_view(), name='video-list'),
    path('video/<int:movie_id>/<str:resolution>/index.m3u8', HLSPlaylistView.as_view(),
         name='hls-playlist'),
    # Die Doku schreibt den Segment-Pfad mit Slash, hls.js hängt ihn relativ zur
    # Playlist an und schickt ihn ohne. Deshalb sind beide Schreibweisen erlaubt.
    path('video/<int:movie_id>/<str:resolution>/<str:segment>/', HLSSegmentView.as_view(),
         name='hls-segment'),
    path('video/<int:movie_id>/<str:resolution>/<str:segment>', HLSSegmentView.as_view(),
         name='hls-segment-no-slash'),
]
