from langchain_core.messages import HumanMessage, SystemMessage

from querymaster.ai.providers.llm.factory import get_llm_provider
from querymaster.ai.system_prompt import SYSTEM_PROMPT


def generate_answer(context: str, question: str) -> str:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {question}"),
    ]
    return get_llm_provider().generate(messages)
