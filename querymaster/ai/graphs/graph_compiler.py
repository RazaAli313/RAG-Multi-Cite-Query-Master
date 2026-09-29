from langgraph.graph import END, StateGraph

from querymaster.ai.graphs.nodes import (
    assemble_node,
    generate_node,
    load_history_node,
    log_query_node,
    retrieve_node,
)
from querymaster.ai.graphs.state import QueryState


def compile_query_graph():
    graph = StateGraph(QueryState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("assemble", assemble_node)
    graph.add_node("load_history", load_history_node)
    graph.add_node("generate", generate_node)
    graph.add_node("log_query", log_query_node)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "assemble")
    graph.add_edge("assemble", "load_history")
    graph.add_edge("load_history", "generate")
    graph.add_edge("generate", "log_query")
    graph.add_edge("log_query", END)

    return graph.compile()
