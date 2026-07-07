import argparse

from app.rag.retriever import retrieve_contexts


def main() -> None:
    parser = argparse.ArgumentParser(description="Search MOFA RAG chunks from PostgreSQL pgvector.")
    parser.add_argument("query", nargs="*", help="Search query.")
    parser.add_argument("--country", default="", help="Optional Korean country name for country-info search.")
    parser.add_argument("--top-k", type=int, default=4, help="Top K per document group.")
    args = parser.parse_args()

    query = " ".join(args.query).strip() or "여권을 분실했습니다"
    contexts = retrieve_contexts(query, country=args.country or None, top_k=args.top_k)

    print(f"query={query}")
    print(f"country={args.country or '-'}")
    print(f"results={len(contexts)}")

    for index, context in enumerate(contexts, start=1):
        preview = " ".join(context.content.split())[:220]
        print()
        print(f"{index}. [{context.document_group}] {context.title}")
        print(f"   chunk_id={context.chunk_id}")
        print(f"   category={context.category or '-'} country={context.country or '-'} score={context.score:.4f}")
        print(f"   source={context.source}")
        print(f"   text={preview}")


if __name__ == "__main__":
    main()
