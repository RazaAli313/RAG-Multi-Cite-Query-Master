from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from querymaster.ai.providers.llm.factory import get_llm_provider
from querymaster.ai.system_prompt import SYSTEM_PROMPT


def generate_answer(context: str, question: str, history: list[dict]) -> str:
    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    for turn in history:
        messages.append(HumanMessage(content=turn["question"]))
        messages.append(AIMessage(content=turn["answer"]))

    messages.append(HumanMessage(content=f"Context:\n{context}\n\nQuestion: {question}"))

    return get_llm_provider().generate(messages)
