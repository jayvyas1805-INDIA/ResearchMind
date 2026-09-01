"""
Embedding service.

Wraps Sentence-Transformers (all-MiniLM-L6-v2 by default) to turn text
chunks into normalized embedding vectors, ready for cosine-similarity
search via FAISS inner product.

The model is downloaded from Hugging Face on first use and cached locally
by the sentence-transformers library — this requires internet access once.
"""

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings

settings = get_settings()


@lru_cache
def get_embedder() -> SentenceTransformer:
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a batch of texts. Returns a (N, EMBEDDING_DIM) float32 array, L2-normalized."""
    if not texts:
        return np.zeros((0, settings.EMBEDDING_DIM), dtype="float32")

    model = get_embedder()
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,  # so inner product == cosine similarity
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return embeddings.astype("float32")


def embed_query(query: str) -> np.ndarray:
    """Embed a single query string. Returns a 1D float32 array."""
    return embed_texts([query])[0]
