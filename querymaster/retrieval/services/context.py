from querymaster.knowledge.models import Chunk


def assemble_context(chunks: list[Chunk]) -> dict:
    context_parts = []
    citations = []

    for index, chunk in enumerate(chunks, start=1):
        source = chunk.source
        citation = source.question if hasattr(source, "question") else str(source)
        context_parts.append(f"[{index}] {chunk.raw_text}")
        citations.append({"index": index, "citation": citation})

    return {
        "context": "\n\n".join(context_parts),
        "citations": citations,
    }
