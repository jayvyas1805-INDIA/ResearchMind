"""
Vector index service — wraps a FAISS index persisted to disk.

Uses IndexFlatIP (inner product) over L2-normalized vectors, which is
mathematically equivalent to cosine similarity. Wrapped in IndexIDMap2 so
each vector can be added/removed by an explicit integer id — we reuse each
Chunk row's own integer primary key as its vector id, so there is a single
source of truth instead of a separate id-mapping table.

Swappable later for ChromaDB/Qdrant per the project's stated roadmap — this
module is the only place that would need to change.
"""

import os
import threading

import faiss
import numpy as np

from app.core.config import get_settings

settings = get_settings()

_INDEX_FILENAME = "papermind.faiss"
_lock = threading.Lock()

_index = None  # module-level singleton, lazily loaded


def _index_path() -> str:
    return os.path.join(settings.INDEX_DIR, _INDEX_FILENAME)


def _create_empty_index() -> faiss.Index:
    flat = faiss.IndexFlatIP(settings.EMBEDDING_DIM)
    return faiss.IndexIDMap2(flat)


def get_index() -> faiss.Index:
    """Return the process-wide FAISS index, loading it from disk if present."""
    global _index
    if _index is not None:
        return _index

    with _lock:
        if _index is not None:  # re-check after acquiring the lock
            return _index

        path = _index_path()
        os.makedirs(settings.INDEX_DIR, exist_ok=True)

        if os.path.exists(path):
            _index = faiss.read_index(path)
        else:
            _index = _create_empty_index()
            faiss.write_index(_index, path)

        return _index


def save_index() -> None:
    faiss.write_index(get_index(), _index_path())


def add_vectors(ids: list[int], vectors: np.ndarray) -> None:
    """Add vectors to the index, keyed by the given integer ids, and persist."""
    if not ids:
        return
    if vectors.shape[0] != len(ids):
        raise ValueError("Number of ids must match number of vectors.")

    with _lock:
        index = get_index()
        index.add_with_ids(vectors, np.array(ids, dtype="int64"))
        save_index()


def remove_ids(ids: list[int]) -> None:
    """Remove vectors by id (used when re-indexing a paper), and persist."""
    if not ids:
        return
    with _lock:
        index = get_index()
        index.remove_ids(np.array(ids, dtype="int64"))
        save_index()


def search(query_vector: np.ndarray, top_k: int) -> list[tuple[int, float]]:
    """
    Search the index for the top_k nearest vectors.
    Returns a list of (vector_id, similarity_score), ordered best-first.
    """
    index = get_index()
    if index.ntotal == 0:
        return []

    query_2d = query_vector.reshape(1, -1).astype("float32")
    distances, ids = index.search(query_2d, top_k)

    results = []
    for vector_id, score in zip(ids[0], distances[0]):
        if vector_id == -1:  # FAISS pads with -1 when fewer than top_k results exist
            continue
        results.append((int(vector_id), float(score)))
    return results
