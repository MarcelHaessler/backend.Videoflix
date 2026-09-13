"""Connects the upload in the admin with the conversion in the background."""
import django_rq
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Video
from .tasks import convert_video


@receiver(post_save, sender=Video)
def enqueue_conversion(sender, instance, created, **kwargs):
    """Only a fresh upload starts a job; editing a title must not re-encode anything."""

    if not created:
        return

    django_rq.get_queue('default').enqueue(convert_video, instance.id)
