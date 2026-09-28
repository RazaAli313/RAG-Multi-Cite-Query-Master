from django.contrib.contenttypes.models import ContentType

from querymaster.ai.providers.embedding.factory import get_embedding_provider
from querymaster.ingestion.services.activation import activate_chunk
from querymaster.knowledge.models import Chunk


def ingest_chunk(source_instance, raw_text: str, chunk_hash: str) -> None:
    content_type = ContentType.objects.get_for_model(source_instance)

    existing_chunk = Chunk.objects.filter(
        content_type=content_type,
        object_id=source_instance.pk,
        chunk_hash=chunk_hash,
    ).first()

    if existing_chunk:
        activate_chunk(existing_chunk, source_instance)
        return

    embedding = get_embedding_provider().embed(raw_text)

    new_chunk = Chunk.objects.create(
        content_type=content_type,
        object_id=source_instance.pk,
        raw_text=raw_text,
        chunk_hash=chunk_hash,
        embedding=embedding,
        is_active=False,
    )

    activate_chunk(new_chunk, source_instance)
