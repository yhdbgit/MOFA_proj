from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid5, NAMESPACE_URL

from psycopg.types.json import Jsonb

from app.rag.config import RagSettings, get_settings
from app.rag.db import connect, ensure_schema


@dataclass(frozen=True)
class RagChunk:
    chunk_key: str
    content: str
    metadata: dict[str, Any]
    embedding: list[float]


@dataclass(frozen=True)
class RagSearchResult:
    chunk_id: str
    content: str
    title: str
    source: str
    document_group: str
    category: str | None
    country: str | None
    score: float
    metadata: dict[str, Any]


def stable_chunk_uuid(chunk_key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"mofa-rag-chunk:{chunk_key}")


def upsert_chunks(chunks: list[RagChunk], settings: RagSettings | None = None) -> int:
    active_settings = settings or get_settings()
    ensure_schema(active_settings)

    sql = """
    INSERT INTO rag_chunks (
        id,
        chunk_key,
        content,
        embedding,
        document_group,
        document_type,
        title,
        source,
        category,
        country,
        metadata,
        updated_at
    )
    VALUES (
        %(id)s,
        %(chunk_key)s,
        %(content)s,
        %(embedding)s,
        %(document_group)s,
        %(document_type)s,
        %(title)s,
        %(source)s,
        %(category)s,
        %(country)s,
        %(metadata)s,
        now()
    )
    ON CONFLICT (chunk_key) DO UPDATE SET
        content = EXCLUDED.content,
        embedding = EXCLUDED.embedding,
        document_group = EXCLUDED.document_group,
        document_type = EXCLUDED.document_type,
        title = EXCLUDED.title,
        source = EXCLUDED.source,
        category = EXCLUDED.category,
        country = EXCLUDED.country,
        metadata = EXCLUDED.metadata,
        updated_at = now()
    """

    with connect(active_settings) as connection:
        with connection.cursor() as cursor:
            for chunk in chunks:
                metadata = chunk.metadata
                cursor.execute(
                    sql,
                    {
                        "id": stable_chunk_uuid(chunk.chunk_key),
                        "chunk_key": chunk.chunk_key,
                        "content": chunk.content,
                        "embedding": chunk.embedding,
                        "document_group": metadata.get("document_group") or "unknown",
                        "document_type": metadata.get("document_type"),
                        "title": metadata.get("title"),
                        "source": metadata.get("source"),
                        "category": metadata.get("category"),
                        "country": metadata.get("country") or None,
                        "metadata": Jsonb(metadata),
                    },
                )
        connection.commit()

    return len(chunks)


def search_chunks(
    query_embedding: list[float],
    document_group: str,
    settings: RagSettings | None = None,
    *,
    country: str | None = None,
    limit: int | None = None,
) -> list[RagSearchResult]:
    active_settings = settings or get_settings()
    active_limit = limit or active_settings.top_k
    filters = ["document_group = %(document_group)s"]
    params: dict[str, Any] = {
        "query_embedding": query_embedding,
        "document_group": document_group,
        "limit": active_limit,
    }

    if country:
        filters.append("country = %(country)s")
        params["country"] = country

    sql = f"""
    SELECT
        chunk_key,
        content,
        title,
        source,
        document_group,
        category,
        country,
        metadata,
        1 - (embedding <=> %(query_embedding)s) AS score
    FROM rag_chunks
    WHERE {" AND ".join(filters)}
    ORDER BY embedding <=> %(query_embedding)s
    LIMIT %(limit)s
    """

    with connect(active_settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

    return [
        RagSearchResult(
            chunk_id=row[0],
            content=row[1],
            title=row[2] or "",
            source=row[3] or "",
            document_group=row[4] or "",
            category=row[5],
            country=row[6],
            score=float(row[8] or 0),
            metadata=dict(row[7] or {}),
        )
        for row in rows
    ]
