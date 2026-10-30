"""
Manual verification script for Phase 4 (chunking + embeddings + FAISS).

Phase 4 intentionally does not expose semantic search via an API endpoint
yet — that's Phase 5. This script exercises retrieval_service directly so
you can confirm indexing actually works before Phase 5 adds the public
search API + UI.

Usage (run from the backend/ folder, with the venv activated):

    python scripts/test_retrieval.py <paper_id> "your query here"

Get a paper_id from GET /api/papers (or the Dashboard/paper detail page).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal  # noqa: E402
from app.services import retrieval_service  # noqa: E402


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/test_retrieval.py <paper_id> <query>")
        sys.exit(1)

    paper_id = sys.argv[1]
    query = " ".join(sys.argv[2:])

    db = SessionLocal()
    try:
        results = retrieval_service.search(query=query, db=db, paper_id=paper_id, top_k=5)
        if not results:
            print("No results found. Has this paper been uploaded and indexed successfully?")
            return

        print(f"\nTop {len(results)} results for: \"{query}\"\n" + "-" * 60)
        for r in results:
            print(f"\n[score {r.similarity_score:.3f}] page {r.page_number} | section: {r.section}")
            print(r.chunk_text[:300] + ("..." if len(r.chunk_text) > 300 else ""))
    finally:
        db.close()


if __name__ == "__main__":
    main()
