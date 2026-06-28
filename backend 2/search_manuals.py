import sys

import chromadb

from local_embeddings import LocalHashEmbeddingFunction
from main import CHROMA_DB_PATH, MANUAL_COLLECTION_NAME, RETRIEVAL_TOP_K, search_collection


def main():
    query = " ".join(sys.argv[1:]).strip()

    if not query:
        query = "해외에서 여권을 분실했어요"

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(
        name=MANUAL_COLLECTION_NAME,
        embedding_function=LocalHashEmbeddingFunction(),
    )

    print(f"collection={MANUAL_COLLECTION_NAME} count={collection.count()}")
    print(f"query={query}")

    contexts = search_collection(MANUAL_COLLECTION_NAME, query, RETRIEVAL_TOP_K)

    for index, context in enumerate(contexts, start=1):
        print()
        print(
            f"{index}. {context.get('article_title') or context.get('title')} "
            f"({context.get('category')})"
        )
        print(f"   document: {context.get('title')}")
        print(f"   source: {context.get('source')}")
        print(f"   text: {context.get('content', '')[:260].replace(chr(10), ' ')}")


if __name__ == "__main__":
    main()
