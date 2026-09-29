from querymaster.ai.graphs.graph_compiler import compile_query_graph

_graph = compile_query_graph()


def invoke_query(question: str, session_id: str) -> dict:
    result = _graph.invoke({
        "question": question,
        "session_id": session_id,
        "chunks": [],
        "context": "",
        "citations": [],
        "history": [],
        "answer": "",
    })
    return {
        "answer": result["answer"],
        "citations": result["citations"],
    }
