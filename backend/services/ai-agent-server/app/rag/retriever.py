from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedContext:
    chunk_id: str
    content: str
    title: str
    source: str
    document_group: str
    category: str | None
    country: str | None
    score: float


def retrieve_contexts(
    query: str,
    *,
    country: str | None = None,
    top_k: int | None = None,
) -> list[RetrievedContext]:
    contexts: list[RetrievedContext] = []

    contexts.extend(_safe_search("manuals", query, top_k=top_k))
    contexts.extend(_safe_search("legal", query, top_k=top_k))

    if country:
        contexts.extend(_safe_search("countries", query, country=country, top_k=top_k))

    return sorted(contexts, key=lambda item: item.score, reverse=True)


def _safe_search(
    document_group: str,
    query: str,
    *,
    country: str | None = None,
    top_k: int | None = None,
) -> list[RetrievedContext]:
    try:
        from app.rag.config import get_settings
        from app.rag.embeddings import embed_query
        from app.rag.repository import search_chunks

        settings = get_settings()
        query_embedding = embed_query(query, settings.embedding_model)
        results = search_chunks(
            query_embedding,
            document_group,
            settings,
            country=country,
            limit=top_k,
        )
    except Exception:
        return []

    return [
        RetrievedContext(
            chunk_id=result.chunk_id,
            content=result.content,
            title=result.title,
            source=result.source,
            document_group=result.document_group,
            category=result.category,
            country=result.country,
            score=result.score,
        )
        for result in results
    ]
