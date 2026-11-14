"""Real local embedding model via sentence-transformers. No mock/random fallback."""
from typing import Protocol

from sentence_transformers import SentenceTransformer


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, question: str) -> list[float]: ...


class E5Embedder:
    """intfloat/multilingual-e5-* models expect 'passage: ' / 'query: ' prefixes."""

    def __init__(self, model_name: str = "intfloat/multilingual-e5-small", batch_size: int = 32) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.model = SentenceTransformer(model_name, device="cpu")  # raises if model can't load
        self.dimensions = self.model.get_sentence_embedding_dimension()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vecs = self.model.encode([f"passage: {t}" for t in texts], batch_size=self.batch_size,
                                 normalize_embeddings=True, show_progress_bar=False)
        return vecs.tolist()

    def embed_query(self, question: str) -> list[float]:
        return self.model.encode(f"query: {question}", normalize_embeddings=True, show_progress_bar=False).tolist()
