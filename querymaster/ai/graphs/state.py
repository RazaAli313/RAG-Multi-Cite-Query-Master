from typing import TypedDict

from querymaster.knowledge.models import Chunk


class QueryState(TypedDict):
    question: str
    session_id: str
    chunks: list[Chunk]
    context: str
    citations: list[dict]
    history: list[dict]
    answer: str
