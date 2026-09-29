from pgvector.django import CosineDistance

from querymaster.ai.providers.embedding.factory import get_embedding_provider
from querymaster.knowledge.models import Chunk


def retrieve_chunks(question: str, top_k: int = 3) -> list[Chunk]:
    question_embedding = get_embedding_provider().embed(question)

    chunks = list(
        Chunk.objects.filter(is_active=True)
        .order_by(CosineDistance("embedding", question_embedding))[:top_k]
    )
    chunks.sort(key=lambda chunk: chunk.updated_at, reverse=True)
    return chunks
