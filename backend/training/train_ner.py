"""
Fine-tunes spaCy's NER component to recognize MODEL/DATASET/METRIC/METHOD/
TECHNOLOGY, starting from en_core_web_sm and continuing training on the
weak-labeled data from generate_weak_labels.py.

Usage:
    cd backend
    python training/generate_weak_labels.py
    python training/train_ner.py --epochs 20
"""
import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spacy  # noqa: E402
from spacy.tokens import DocBin  # noqa: E402
from spacy.training import Example  # noqa: E402
from spacy.util import compounding, minibatch  # noqa: E402

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MODEL_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model")

NEW_LABELS = ["MODEL", "DATASET", "METRIC", "METHOD", "TECHNOLOGY"]


def load_examples(path: str, nlp) -> list[Example]:
    doc_bin = DocBin().from_disk(path)
    docs = list(doc_bin.get_docs(nlp.vocab))
    examples = []
    for doc in docs:
        entities = [(e.start_char, e.end_char, e.label_) for e in doc.ents]
        examples.append(Example.from_dict(nlp.make_doc(doc.text), {"entities": entities}))
    return examples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument("--base-model", default="en_core_web_sm")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    train_path = os.path.join(DATA_DIR, "train.spacy")
    dev_path = os.path.join(DATA_DIR, "dev.spacy")
    if not os.path.exists(train_path):
        print(f"No training data found at {train_path}. Run generate_weak_labels.py first.")
        sys.exit(1)

    nlp = spacy.load(args.base_model)
    ner = nlp.get_pipe("ner")
    for label in NEW_LABELS:
        ner.add_label(label)

    train_examples = load_examples(train_path, nlp)
    dev_examples = load_examples(dev_path, nlp) if os.path.exists(dev_path) else []

    print(f"Training on {len(train_examples)} examples for {args.epochs} epochs (new labels: {NEW_LABELS})...")

    other_pipes = [p for p in nlp.pipe_names if p != "ner"]
    with nlp.disable_pipes(*other_pipes):
        optimizer = nlp.resume_training()
        for epoch in range(args.epochs):
            random.shuffle(train_examples)
            losses = {}
            batches = minibatch(train_examples, size=compounding(4.0, 32.0, 1.001))
            for batch in batches:
                nlp.update(batch, drop=args.dropout, losses=losses, sgd=optimizer)
            print(f"  epoch {epoch + 1}/{args.epochs} — loss: {losses.get('ner', 0.0):.3f}")

    os.makedirs(MODEL_OUT, exist_ok=True)
    nlp.to_disk(MODEL_OUT)
    print(f"Saved fine-tuned model to {MODEL_OUT}")

    if dev_examples:
        from spacy.scorer import Scorer

        scorer = Scorer()
        predicted_examples = []
        for ex in dev_examples:
            pred_doc = nlp(ex.reference.text)
            predicted_examples.append(Example(pred_doc, ex.reference))
        scores = scorer.score(predicted_examples)

        print("\nDev set scores — AGAINST WEAK LABELS, not a true gold set (see training/README.md):")
        print(f"  Overall NER F1: {scores.get('ents_f', 0):.3f}  P: {scores.get('ents_p', 0):.3f}  R: {scores.get('ents_r', 0):.3f}")
        for label, s in scores.get("ents_per_type", {}).items():
            print(f"  {label:<12} F1: {s['f']:.3f}  P: {s['p']:.3f}  R: {s['r']:.3f}")
        print("\nRun training/evaluate_ner.py against a hand-labeled gold set for a trustworthy comparison.")


if __name__ == "__main__":
    main()
