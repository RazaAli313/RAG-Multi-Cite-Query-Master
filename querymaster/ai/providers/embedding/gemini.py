from django.conf import settings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from querymaster.ai.providers.embedding.base import BaseEmbeddingProvider


class GeminiEmbeddingProvider(BaseEmbeddingProvider):

    def __init__(self):
        self.client = GoogleGenerativeAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            output_dimensionality=settings.EMBEDDING_DIMENSIONS,
        )

    def embed(self, text: str) -> list[float]:
        return self.client.embed_query(text)
