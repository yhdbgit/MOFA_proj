import hashlib
import math
import re


class LocalHashEmbeddingFunction:
    """Small deterministic embedding function for local ChromaDB prototyping."""

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    def name(self) -> str:
        return "local_hash_embedding"

    def __call__(self, input):
        return [self._embed(text) for text in input]

    def embed_query(self, input):
        return self.__call__(input)

    def embed_documents(self, input):
        return self.__call__(input)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = self._tokenize(text)

        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))

        if norm == 0:
            return vector

        return [value / norm for value in vector]

    def _tokenize(self, text: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        words = re.findall(r"[0-9a-zA-Z가-힣]+", normalized)
        char_grams = []

        compact = re.sub(r"\s+", "", normalized)
        for size in (2, 3, 4):
            char_grams.extend(
                compact[index : index + size]
                for index in range(max(len(compact) - size + 1, 0))
            )

        return words + char_grams
