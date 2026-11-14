"""Persistent vector store: Chroma (local, on-disk), cosine distance, metadata filters."""
from typing import Any

import chromadb

from .models import Chunk

ALLOWED_FILTERS = {"chapter", "section", "page_id"}


class ChromaStore:
    def __init__(self, path: str, dimensions: int) -> None:
        self.client = chromadb.PersistentClient(path=path)
        self.dimensions = dimensions

    def _collection(self, index: str):
        return self.client.get_or_create_collection(f"day6_{index}", metadata={"hnsw:space": "cosine"})

    def count(self, index: str) -> int:
        return self._collection(index).count()

    def upsert(self, index: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors length differ")
        if any(len(v) != self.dimensions for v in vectors):
            raise ValueError(f"vector dimension != {self.dimensions}")
        ids = [c.chunk_id for c in chunks]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate chunk ids")
        col = self._collection(index)
        # Remove obsolete chunks of the documents being (re)ingested, then upsert stable IDs.
        for doc_id in {c.document_id for c in chunks}:
            old = set(col.get(where={"document_id": doc_id}, include=[])["ids"])
            stale = list(old - set(ids))
            if stale:
                col.delete(ids=stale)
        for i in range(0, len(chunks), 500):
            part = chunks[i:i + 500]
            col.upsert(
                ids=[c.chunk_id for c in part],
                embeddings=vectors[i:i + 500],
                documents=[c.text for c in part],
                metadatas=[{"document_id": c.document_id, "source": c.source, "page": c.page, **c.metadata}
                           for c in part],
            )

    def search(self, index: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        where = None
        if filters:
            bad = set(filters) - ALLOWED_FILTERS
            if bad:
                raise ValueError(f"filter fields not allowed: {bad}")
            where = filters if len(filters) == 1 else {"$and": [{k: v} for k, v in filters.items()]}
        r = self._collection(index).query(query_embeddings=[query_vector], n_results=top_k, where=where,
                                          include=["documents", "metadatas", "distances"])
        return [
            {"rank": i + 1, "chunk_id": cid, "score": round(1 - dist, 4), "text": doc, "metadata": meta}
            for i, (cid, doc, dist, meta) in enumerate(zip(r["ids"][0], r["documents"][0],
                                                          r["distances"][0], r["metadatas"][0]))
        ]
