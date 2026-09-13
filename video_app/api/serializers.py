"""Serializer for the dashboard list; the player talks to the HLS views instead."""
from rest_framework import serializers

from ..models import Video


class VideoSerializer(serializers.ModelSerializer):
    """Delivers exactly the fields the dashboard renders, nothing more."""

    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = ['id', 'created_at', 'title', 'description', 'thumbnail_url', 'category']

    def get_thumbnail_url(self, obj):
        if not obj.thumbnail:
            return None
        request = self.context['request']
        return request.build_absolute_uri(obj.thumbnail.url)