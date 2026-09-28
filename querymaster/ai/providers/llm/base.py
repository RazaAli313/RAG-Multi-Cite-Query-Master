from langchain_core.messages import BaseMessage


class BaseLLMProvider:

    def generate(self, messages: list[BaseMessage]) -> str:
        raise NotImplementedError
