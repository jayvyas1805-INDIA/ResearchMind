import numpy as np

from app.models.chunk import Chunk
from app.services import indexing_service, vector_service


def _add_chunk(db, chunk_id, text):
    db.add(
        Chunk(
            id=chunk_id,
            paper_id="paper-1",
            chunk_index=chunk_id,
            text=text,
        )
    )
    db.commit()


def test_reconcile_index_rebuilds_vectors_missing_from_faiss(db_session, monkeypatch):
    _add_chunk(db_session, 1, "first stored chunk")
    _add_chunk(db_session, 2, "second stored chunk")
    rebuilt = {}

    monkeypatch.setattr(indexing_service.vector_service, "get_vector_ids", lambda: [])
    monkeypatch.setattr(
        indexing_service.embedding_service,
        "embed_texts",
        lambda texts: np.zeros((len(texts), 384), dtype="float32"),
    )
    monkeypatch.setattr(
        indexing_service.vector_service,
        "replace_vectors",
        lambda ids, vectors: rebuilt.update(ids=ids, vectors=vectors),
    )

    assert indexing_service.reconcile_index(db_session) is True
    assert rebuilt["ids"] == [1, 2]
    assert rebuilt["vectors"].shape == (2, 384)


def test_reconcile_index_skips_rebuild_when_ids_match(db_session, monkeypatch):
    _add_chunk(db_session, 1, "stored chunk")
    monkeypatch.setattr(indexing_service.vector_service, "get_vector_ids", lambda: [1])
    monkeypatch.setattr(
        indexing_service.embedding_service,
        "embed_texts",
        lambda _texts: (_ for _ in ()).throw(AssertionError("unexpected embedding")),
    )
    monkeypatch.setattr(
        indexing_service.vector_service,
        "replace_vectors",
        lambda *_args: (_ for _ in ()).throw(AssertionError("unexpected rebuild")),
    )

    assert indexing_service.reconcile_index(db_session) is False


def test_replace_vectors_persists_ids_and_searchable_vectors(tmp_path, monkeypatch):
    monkeypatch.setattr(vector_service.settings, "INDEX_DIR", str(tmp_path))
    monkeypatch.setattr(vector_service, "_index", None)
    vectors = np.zeros((2, 384), dtype="float32")
    vectors[0, 0] = 1.0
    vectors[1, 1] = 1.0

    vector_service.replace_vectors([10, 20], vectors)

    assert vector_service.get_vector_ids() == [10, 20]
    query = np.zeros(384, dtype="float32")
    query[1] = 1.0
    assert vector_service.search(query, 1) == [(20, 1.0)]
