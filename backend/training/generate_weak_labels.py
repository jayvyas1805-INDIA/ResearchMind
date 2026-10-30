"""
Generates weak-supervision training data for NER fine-tuning.

Approach: distant supervision. The app already has a rule-based entity
extractor (PhraseMatcher over curated MODEL/DATASET/METRIC/METHOD/
TECHNOLOGY term lists, see app/utils/research_terms.py) plus spaCy's
generic NER for PERSON/ORG. We scan already-indexed Chunk text for matches
and treat them as "weak" (noisy, automatically generated) labels, then
export them in spaCy's training format so a model can be fine-tuned to
recognize these categories more generally — including phrasings not in
the curated lists.

IMPORTANT LIMITATION: weak labels come from the same rule-based system
used as the baseline to compare against. A model trained purely on these
labels will tend to imitate the rules, not exceed them, and evaluating
against more weak labels would be circular. For a fair, honest comparison,
build a small GOLD test set by hand (see annotate_gold.py) and evaluate
BOTH systems against that gold set — never against weak labels alone.

Usage:
    cd backend
    python training/generate_weak_labels.py
"""
import argparse
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spacy  # noqa: E402
from spacy.tokens import DocBin  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models.chunk import Chunk  # noqa: E402
from app.services.nlp_service import get_nlp  # noqa: E402
from app.utils.research_terms import ALL_CATEGORIES  # noqa: E402

LABEL_MAP = {
    "models": "MODEL", "datasets": "DATASET", "metrics": "METRIC",
    "methods": "METHOD", "technologies": "TECHNOLOGY",
}


def _compile_patterns():
    patterns = []
    for category, terms in ALL_CATEGORIES.items():
        label = LABEL_MAP[category]
        # Longest terms first so e.g. "Bidirectional GRU" wins over "GRU".
        for term in sorted(terms, key=len, reverse=True):
            pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", re.IGNORECASE)
            patterns.append((pattern, label))
    return patterns


_PATTERNS = _compile_patterns()


def _find_weak_spans(text: str) -> list[tuple[int, int, str]]:
    """Rule-based extraction — same logic as the app's PhraseMatcher, but
    regex-based here to avoid needing a live spaCy Doc for this step."""
    spans = []
    occupied = [False] * len(text)
    for pattern, label in _PATTERNS:
        for m in pattern.finditer(text):
            start, end = m.start(), m.end()
            if any(occupied[start:end]):
                continue
            spans.append((start, end, label))
            for i in range(start, end):
                occupied[i] = True
    return spans


def _add_generic_ner_spans(nlp, text: str, existing_spans: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    """Adds PERSON/ORG spans from spaCy's built-in NER, without overlapping
    the rule-based spans already found — keeps the model exposed to its
    original label types during fine-tuning, reducing catastrophic forgetting."""
    doc = nlp(text)
    occupied = [False] * len(text)
    for s, e, _ in existing_spans:
        for i in range(s, e):
            occupied[i] = True

    spans = list(existing_spans)
    for ent in doc.ents:
        if ent.label_ not in ("PERSON", "ORG"):
            continue
        if any(occupied[ent.start_char:ent.end_char]):
            continue
        spans.append((ent.start_char, ent.end_char, ent.label_))
    return spans


def build_docbin(chunks, nlp, blank_nlp) -> DocBin:
    doc_bin = DocBin()
    for chunk in chunks:
        text = chunk.text
        spans = _find_weak_spans(text)
        spans = _add_generic_ner_spans(nlp, text, spans)

        doc = blank_nlp.make_doc(text)
        ent_spans = []
        for start, end, label in spans:
            span = doc.char_span(start, end, label=label, alignment_mode="contract")
            if span is not None:
                ent_spans.append(span)
        doc.ents = spacy.util.filter_spans(ent_spans)  # spaCy requires non-overlapping entities
        doc_bin.add(doc)
    return doc_bin


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev-fraction", type=float, default=0.2)
    parser.add_argument("--out-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    db = SessionLocal()
    try:
        chunks = db.query(Chunk).all()
    finally:
        db.close()

    if not chunks:
        print("No chunks found. Upload/process at least one paper (or run eval/seed_fixture_paper.py) first.")
        sys.exit(1)

    # Split by paper_id, not by chunk, so train/dev never share a source
    # document — reduces (but doesn't eliminate) leakage from near-duplicate
    # phrasing within the same paper.
    paper_ids = sorted({c.paper_id for c in chunks})
    random.Random(args.seed).shuffle(paper_ids)
    n_dev_papers = max(1, int(len(paper_ids) * args.dev_fraction))
    dev_paper_ids = set(paper_ids[:n_dev_papers])
    train_paper_ids = set(paper_ids) - dev_paper_ids

    if len(paper_ids) < 2:
        print("WARNING: only one paper indexed — train and dev will share the same source "
              "document, so dev scores will be optimistic. Process more papers for a "
              "meaningful split.")
        train_paper_ids = set(paper_ids)
        dev_paper_ids = set(paper_ids)

    train_chunks = [c for c in chunks if c.paper_id in train_paper_ids]
    dev_chunks = [c for c in chunks if c.paper_id in dev_paper_ids]

    nlp = get_nlp()
    blank_nlp = spacy.blank("en")

    train_db = build_docbin(train_chunks, nlp, blank_nlp)
    dev_db = build_docbin(dev_chunks, nlp, blank_nlp)

    train_db.to_disk(os.path.join(args.out_dir, "train.spacy"))
    dev_db.to_disk(os.path.join(args.out_dir, "dev.spacy"))

    print(
        f"Wrote {len(train_chunks)} train examples ({len(train_paper_ids)} papers) and "
        f"{len(dev_chunks)} dev examples ({len(dev_paper_ids)} papers) to {args.out_dir}"
    )
    print("These are WEAK (auto-generated) labels — see training/README.md before trusting "
          "any evaluation numbers based on them alone.")


if __name__ == "__main__":
    main()
