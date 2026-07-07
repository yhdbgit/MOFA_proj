from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from app.rag.config import RagSettings, get_settings


CREATE_TABLE_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS rag_chunks (
    id UUID PRIMARY KEY,
    chunk_key TEXT NOT NULL UNIQUE,
    content TEXT NOT NULL,
    embedding vector(384) NOT NULL,
    document_group TEXT NOT NULL,
    document_type TEXT,
    title TEXT,
    source TEXT,
    category TEXT,
    country TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_group ON rag_chunks(document_group);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_category ON rag_chunks(category);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_country ON rag_chunks(country);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_metadata ON rag_chunks USING gin(metadata);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding
    ON rag_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 16);
"""


@contextmanager
def connect(settings: RagSettings | None = None) -> Iterator[Any]:
    try:
        import psycopg
        from pgvector.psycopg import register_vector
    except ImportError as exception:
        raise RuntimeError(
            "PostgreSQL RAG dependencies are not installed. Run `python -m pip install -r requirements.txt`."
        ) from exception

    active_settings = settings or get_settings()
    with psycopg.connect(active_settings.database_url) as connection:
        register_vector(connection)
        yield connection


def ensure_schema(settings: RagSettings | None = None) -> None:
    active_settings = settings or get_settings()
    with connect(active_settings) as connection:
        with connection.cursor() as cursor:
            for statement in CREATE_TABLE_SQL.split(";"):
                if statement.strip():
                    cursor.execute(statement)
        connection.commit()
