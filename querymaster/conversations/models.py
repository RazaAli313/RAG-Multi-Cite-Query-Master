import uuid

from django.db import models
from django_extensions.db.models import TimeStampedModel


class ChatSession(TimeStampedModel):

    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        ordering = ["-created"]


class QueryLog(TimeStampedModel):

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="query_logs")
    question = models.TextField()
    answer = models.TextField()

    class Meta:
        ordering = ["created"]
