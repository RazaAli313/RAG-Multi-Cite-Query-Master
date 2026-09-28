from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from pgvector.django import VectorField


class Chunk(models.Model):

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    source = GenericForeignKey("content_type", "object_id")

    raw_text = models.TextField()
    chunk_hash = models.CharField(max_length=64)
    embedding = VectorField(dimensions=1536)
    is_active = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
