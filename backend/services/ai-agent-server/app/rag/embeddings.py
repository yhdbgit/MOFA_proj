from functools import lru_cache
from typing import Iterable


class EmbeddingUnavailableError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _load_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exception:
        raise EmbeddingUnavailableError(
            "sentence-transformers is not installed. Run `python -m pip install -r requirements.txt`."
        ) from exception

    return SentenceTransformer(model_name)


def embed_texts(texts: Iterable[str], model_name: str) -> list[list[float]]:
    model = _load_model(model_name)
    normalized_texts = [normalize_for_e5(text) for text in texts]
    embeddings = model.encode(
        normalized_texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return [embedding.astype(float).tolist() for embedding in embeddings]


def embed_query(query: str, model_name: str) -> list[float]:
    return embed_texts([f"query: {query}"], model_name)[0]


def embed_passage(content: str, model_name: str) -> list[float]:
    return embed_texts([f"passage: {content}"], model_name)[0]


def normalize_for_e5(text: str) -> str:
    return " ".join(str(text).split())
