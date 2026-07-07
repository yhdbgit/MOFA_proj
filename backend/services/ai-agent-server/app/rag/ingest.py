import argparse
import json
from collections import Counter
from pathlib import Path

from app.rag.config import get_settings
from app.rag.embeddings import embed_passage
from app.rag.repository import RagChunk, upsert_chunks


def load_processed_chunks(processed_root: Path) -> list[dict]:
    files = [
        processed_root / "countries" / "country_chunks.json",
        processed_root / "legal" / "legal_chunks.json",
        processed_root / "manuals" / "manuals_chunks.json",
    ]
    chunks: list[dict] = []

    for file_path in files:
        if not file_path.exists():
            raise FileNotFoundError(f"Processed RAG file not found: {file_path}")

        payload = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"Processed RAG file must contain a list: {file_path}")

        chunks.extend(payload)

    return chunks


def build_rag_chunks(raw_chunks: list[dict], model_name: str) -> list[RagChunk]:
    rag_chunks: list[RagChunk] = []

    for raw_chunk in raw_chunks:
        chunk_key = raw_chunk.get("id")
        content = raw_chunk.get("content")
        metadata = raw_chunk.get("metadata") or {}

        if not chunk_key or not content:
            continue

        rag_chunks.append(
            RagChunk(
                chunk_key=chunk_key,
                content=content,
                metadata=metadata,
                embedding=embed_passage(content, model_name),
            )
        )

    return rag_chunks


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Ingest processed MOFA RAG chunks into PostgreSQL pgvector.")
    parser.add_argument(
        "--processed-root",
        type=Path,
        default=settings.processed_root,
        help="Directory containing countries/legal/manuals processed JSON folders.",
    )
    args = parser.parse_args()

    processed_root = args.processed_root.resolve()
    print(f"Using processed root: {processed_root}")
    raw_chunks = load_processed_chunks(processed_root)
    counts = Counter((chunk.get("metadata") or {}).get("document_group", "unknown") for chunk in raw_chunks)

    for group, count in sorted(counts.items()):
        print(f"Loaded {group}: {count} chunks")

    rag_chunks = build_rag_chunks(raw_chunks, settings.embedding_model)
    inserted_count = upsert_chunks(rag_chunks, settings)
    print(f"Upserted total: {inserted_count} chunks")
    print(f"Embedding model: {settings.embedding_model}")
    print(f"Embedding dimensions: {settings.embedding_dimensions}")


if __name__ == "__main__":
    main()
