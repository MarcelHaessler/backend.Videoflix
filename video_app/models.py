"""Database model for the movies that the dashboard offers."""
from django.db import models

# The dashboard groups by category. The frontend lowercases the value itself,
# so the stored value is on the left and the admin label on the right.
CATEGORY_CHOICES = [
    ('drama', 'Drama'),
    ('romance', 'Romance'),
    ('comedy', 'Comedy'),
    ('documentary', 'Documentary'),
    ('action', 'Action'),
]


class Video(models.Model):
    """One uploaded movie together with the files ffmpeg derives from it."""

    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    video_file = models.FileField(upload_to='videos/')
    thumbnail = models.FileField(upload_to='thumbnails/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        """The title is what identifies an entry in the admin list."""

        return self.title
