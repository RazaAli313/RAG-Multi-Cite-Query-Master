from django.conf import settings

from querymaster.ai.providers.llm.base import BaseLLMProvider
from querymaster.ai.providers.llm.gemini import GeminiLLMProvider


def get_llm_provider() -> BaseLLMProvider:
    provider = settings.LLM_PROVIDER
    if provider == "gemini":
        return GeminiLLMProvider()
    raise ValueError(f"Unknown LLM provider: {provider}")
