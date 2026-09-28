from django.conf import settings

from querymaster.knowledge.providers.embedding.base import BaseEmbeddingProvider
from querymaster.knowledge.providers.embedding.gemini import GeminiEmbeddingProvider


def get_embedding_provider() -> BaseEmbeddingProvider:
    provider = settings.EMBEDDING_PROVIDER
    if provider == "gemini":
        return GeminiEmbeddingProvider()
    raise ValueError(f"Unknown embedding provider: {provider}")
