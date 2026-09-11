"""
Interactive CLI to build a small, genuinely hand-labeled gold test set.

Weak labels (from generate_weak_labels.py) are biased toward the rule-based
system's own vocabulary — evaluating against them can't tell you whether
the fine-tuned model actually generalizes better, only whether it learned
to copy the rules. A human-labeled set is the only fair referee.

For each of N randomly sampled real chunk texts, type the entities you see
and their label. Saves incrementally to training/data/gold.jsonl so nothing
is lost if you stop partway through.

Usage:
    cd backend
    python training/annotate_gold.py --n 30
"""
import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal  # noqa: E402
from app.models.chunk import Chunk  # noqa: E402

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
GOLD_PATH = os.path.join(DATA_DIR, "gold.jsonl")

VALID_LABELS = ["MODEL", "DATASET", "METRIC", "METHOD", "TECHNOLOGY", "PERSON", "ORG"]


def annotate_one(text: str) -> list:
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)
    print(f"Enter entities as: <exact substring> <LABEL>   (valid labels: {', '.join(VALID_LABELS)})")
    print("Empty line when done with this text.\n")

    entities = []
    while True:
        line = input("> ").strip()
        if not line:
            break
        parts = line.rsplit(" ", 1)
        if len(parts) != 2:
            print("  Format: <text> <LABEL>")
            continue
        substring, label = parts
        label = label.upper()
        if label not in VALID_LABELS:
            print(f"  Unknown label '{label}'. Valid: {VALID_LABELS}")
            continue
        start = text.find(substring)
        if start == -1:
            print(f"  Could not find '{substring}' verbatim in the text — check spelling/casing.")
            continue
        entities.append([start, start + len(substring), label])
        print(f"  added: [{start},{start + len(substring)}) {label}")
    return entities


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=20, help="Number of chunks to annotate")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    db = SessionLocal()
    try:
        chunks = db.query(Chunk).all()
    finally:
        db.close()

    if not chunks:
        print("No chunks found. Upload/process at least one paper first.")
        sys.exit(1)

    random.Random(args.seed).shuffle(chunks)
    sample = chunks[: args.n]

    existing = []
    if os.path.exists(GOLD_PATH):
        with open(GOLD_PATH) as f:
            existing = [json.loads(line) for line in f if line.strip()]
        print(f"Found {len(existing)} existing gold examples — appending new ones.")

    results = list(existing)
    for i, chunk in enumerate(sample, start=1):
        print(f"\n[{i}/{len(sample)}]")
        entities = annotate_one(chunk.text)
        results.append({"text": chunk.text, "entities": entities})
        with open(GOLD_PATH, "w") as f:  # save incrementally
            for r in results:
                f.write(json.dumps(r) + "\n")

    print(f"\nSaved {len(results)} total gold examples to {GOLD_PATH}")


if __name__ == "__main__":
    main()
