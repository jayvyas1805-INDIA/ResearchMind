"""
Seeds a small synthetic paper directly into the DB (bypassing PDF upload),
so the evaluation harness has something concrete to test against without
needing one of your real uploaded papers.

Run once before evaluating against 'fixture-paper-001':
    cd backend && python eval/seed_fixture_paper.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, init_db  # noqa: E402
from app.models.chunk import Chunk  # noqa: E402
from app.models.paper import Paper, ProcessingStatus  # noqa: E402
from app.services import indexing_service, nlp_service, vector_service  # noqa: E402

FIXTURE_ID = "fixture-paper-001"

# A short synthetic "paper" with clearly separable facts per page, so
# ground-truth page numbers in the QA set are unambiguous.
PAGE_TEXTS = {
    1: (
        "Title: Emotion Prediction from Text using Deep Learning\n"
        "Jane Doe, John Smith\n\n"
        "Abstract\n"
        "This paper studies emotion classification of text into six categories: "
        "sadness, joy, love, anger, fear, and surprise. We compare RNN, LSTM, "
        "GRU, and Bidirectional GRU architectures for this task."
    ),
    2: (
        "Methodology\n"
        "We preprocess text using tokenization and sequence padding. We train "
        "four deep learning models: RNN, LSTM, GRU, and Bidirectional GRU, "
        "implemented using TensorFlow and Keras. Class weights are used during "
        "training to address class imbalance in the dataset."
    ),
    3: (
        "Results\n"
        "The LSTM model achieved the highest accuracy of approximately 90 "
        "percent on the test set. GRU and Bidirectional GRU achieved "
        "comparable but slightly lower accuracy. The plain RNN performed "
        "worst among the four models evaluated."
    ),
    4: (
        "Limitations\n"
        "The model was trained only on English text and may not generalize "
        "well to sarcasm or code-mixed languages. The dataset used is "
        "relatively small and drawn from a single domain.\n\n"
        "Conclusion\n"
        "We conclude that LSTM performed best on this emotion classification "
        "task. Future work includes exploring transformer-based models such "
        "as BERT for improved accuracy."
    ),
}


def main():
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(Paper).filter(Paper.id == FIXTURE_ID).first()
        if existing:
            print(f"Fixture paper '{FIXTURE_ID}' already exists — deleting and re-seeding.")
            chunk_ids = [c.id for c in db.query(Chunk).filter(Chunk.paper_id == FIXTURE_ID).all()]
            if chunk_ids:
                vector_service.remove_ids(chunk_ids)
            db.query(Chunk).filter(Chunk.paper_id == FIXTURE_ID).delete()
            db.delete(existing)
            db.commit()

        full_text = "\n\n".join(PAGE_TEXTS[p] for p in sorted(PAGE_TEXTS))
        paper = Paper(
            id=FIXTURE_ID,
            filename="fixture_paper.pdf",
            stored_path="N/A (synthetic fixture, no real file on disk)",
            page_count=len(PAGE_TEXTS),
            file_size_bytes=len(full_text.encode()),
            extracted_text=full_text,
            processing_status=ProcessingStatus.PROCESSING,
        )

        nlp_result = nlp_service.run_nlp_pipeline(full_text)
        nlp_service.apply_nlp_result_to_paper(paper, nlp_result)
        paper.pages_json = json.dumps(
            [{"page_number": p, "text": nlp_service.clean_text(t)} for p, t in PAGE_TEXTS.items()]
        )
        paper.processing_status = ProcessingStatus.PROCESSED

        db.add(paper)
        db.commit()
        db.refresh(paper)

        chunk_count = indexing_service.index_paper(paper, db)
        print(f"Seeded fixture paper '{FIXTURE_ID}' with {chunk_count} chunks.")
        print("You can now run: python eval/run_eval.py eval/qa_sets/fixture_paper.json")
    finally:
        db.close()


if __name__ == "__main__":
    main()
