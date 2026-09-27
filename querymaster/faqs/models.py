from django.db import models
from django_extensions.db.models import TimeStampedModel

from querymaster.faqs.choices import IngestionStatus


class FAQ(TimeStampedModel):

    question = models.TextField()
    answer = models.TextField()
    content_hash = models.CharField(max_length=64, blank=True)
    content_updated_at = models.DateTimeField(null=True, blank=True)
    ingestion_status = models.CharField(
        max_length=20,
        choices=IngestionStatus.choices,
        default=IngestionStatus.PENDING,
    )

    class Meta:
        ordering = ["created"]
