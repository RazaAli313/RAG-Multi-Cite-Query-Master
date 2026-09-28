from django.conf import settings
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from querymaster.ai.providers.llm.base import BaseLLMProvider


class GeminiLLMProvider(BaseLLMProvider):

    def __init__(self):
        self.client = ChatGoogleGenerativeAI(
            model=settings.GENERATION_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
        )

    def generate(self, messages: list[BaseMessage]) -> str:
        response = self.client.invoke(messages)
        return response.content
