"""Database model for the movies that the dashboard offers."""
from django.db import models

# Die Kategorien gruppieren das Dashboard. Das Frontend kleinschreibt sie selbst,
# deshalb steht links der gespeicherte Wert und rechts die Anzeige im Admin.
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
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    video_file = models.FileField(upload_to='videos/')
    thumbnail = models.FileField(upload_to='thumbnails/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
