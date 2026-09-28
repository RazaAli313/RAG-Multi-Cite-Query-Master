from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from querymaster.knowledge.models import Chunk


def activate_chunk(new_chunk: Chunk, source_instance) -> None:
    content_type = ContentType.objects.get_for_model(source_instance)
    with transaction.atomic():
        Chunk.objects.filter(
            content_type=content_type,
            object_id=source_instance.pk,
        ).update(is_active=False)
        new_chunk.is_active = True
        new_chunk.save(update_fields=["is_active"])
