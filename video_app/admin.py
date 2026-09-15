"""Admin access is the only way videos enter the system; the API has no upload."""
from django.contrib import admin

from .models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    """Upload form for new movies and a filterable list of the catalogue."""

    list_display = ('title', 'category', 'created_at')
    list_filter = ('category',)
    search_fields = ('title', 'description')
    readonly_fields = ('created_at',)
