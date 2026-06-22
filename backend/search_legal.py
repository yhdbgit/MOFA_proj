import sys

import chromadb

from local_embeddings import LocalHashEmbeddingFunction
from main import CHROMA_DB_PATH, LEGAL_COLLECTION_NAME, RETRIEVAL_TOP_K, search_collection


def main():
    query = " ".join(sys.argv[1:]).strip()

    if not query:
        query = "해외에서 범죄 피해를 입었어요 경찰 신고 방법"

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(
        name=LEGAL_COLLECTION_NAME,
        embedding_function=LocalHashEmbeddingFunction(),
    )

    print(f"collection={LEGAL_COLLECTION_NAME} count={collection.count()}")
    print(f"query={query}")

    contexts = search_collection(LEGAL_COLLECTION_NAME, query, RETRIEVAL_TOP_K)

    for index, context in enumerate(contexts, start=1):
        print()
        print(
            f"{index}. {context.get('article_no')} "
            f"{context.get('article_title')} "
            f"({context.get('category')})"
        )
        print(f"   document: {context.get('title')}")
        print(f"   source: {context.get('source')}")
        print(f"   text: {context.get('content', '')[:260].replace(chr(10), ' ')}")


if __name__ == "__main__":
    main()
