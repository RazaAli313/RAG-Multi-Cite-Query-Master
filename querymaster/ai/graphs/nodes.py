from querymaster.ai.graphs.state import QueryState
from querymaster.ai.services.generation import generate_answer
from querymaster.conversations.models import ChatSession, QueryLog
from querymaster.retrieval.services.context import assemble_context
from querymaster.retrieval.services.retrieval import retrieve_chunks


def retrieve_node(state: QueryState) -> dict:
    return {"chunks": retrieve_chunks(state["question"])}


def assemble_node(state: QueryState) -> dict:
    result = assemble_context(state["chunks"])
    return {"context": result["context"], "citations": result["citations"]}


def load_history_node(state: QueryState) -> dict:
    try:
        session = ChatSession.objects.get(session_id=state["session_id"])
        history = list(QueryLog.objects.filter(session=session).values("question", "answer"))
    except ChatSession.DoesNotExist:
        history = []
    return {"history": history}


def generate_node(state: QueryState) -> dict:
    answer = generate_answer(
        context=state["context"],
        question=state["question"],
        history=state["history"],
    )
    return {"answer": answer}


def log_query_node(state: QueryState) -> dict:
    session, _ = ChatSession.objects.get_or_create(session_id=state["session_id"])
    QueryLog.objects.create(
        session=session,
        question=state["question"],
        answer=state["answer"],
    )
    return {}
