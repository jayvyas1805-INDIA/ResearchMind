"""
Fair NER evaluation: compares the rule-based PhraseMatcher extractor
against the fine-tuned model, BOTH scored against a hand-labeled GOLD test
set (training/data/gold.jsonl, built with annotate_gold.py) — never
against the weak labels used for training, which would bias the
comparison toward whichever system generated them.

Usage:
    cd backend
    python training/evaluate_ner.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spacy  # noqa: E402

from training.generate_weak_labels import LABEL_MAP, _find_weak_spans  # noqa: E402

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
GOLD_PATH = os.path.join(DATA_DIR, "gold.jsonl")
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model")

NEW_LABELS = set(LABEL_MAP.values())


def load_gold() -> list[dict]:
    if not os.path.exists(GOLD_PATH):
        print(f"No gold set found at {GOLD_PATH}. Run annotate_gold.py first.")
        sys.exit(1)
    examples = []
    with open(GOLD_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def score_system(name: str, predict_fn, gold_examples: list[dict], labels_of_interest: set) -> dict:
    tp = fp = fn = 0
    per_label = {label: {"tp": 0, "fp": 0, "fn": 0} for label in labels_of_interest}

    for ex in gold_examples:
        gold_spans = {(s, e, label) for s, e, label in ex["entities"] if label in labels_of_interest}
        pred_spans = {(s, e, label) for s, e, label in predict_fn(ex["text"]) if label in labels_of_interest}

        for span in pred_spans:
            if span in gold_spans:
                tp += 1
                per_label[span[2]]["tp"] += 1
            else:
                fp += 1
                if span[2] in per_label:
                    per_label[span[2]]["fp"] += 1
        for span in gold_spans:
            if span not in pred_spans:
                fn += 1
                per_label[span[2]]["fn"] += 1

    precision, recall, f1 = prf(tp, fp, fn)
    print(f"\n{name}")
    print(f"  Overall: P={precision:.3f} R={recall:.3f} F1={f1:.3f}  (tp={tp} fp={fp} fn={fn})")
    for label, counts in per_label.items():
        p, r, f = prf(counts["tp"], counts["fp"], counts["fn"])
        print(f"  {label:<12} P={p:.3f} R={r:.3f} F1={f:.3f}  (tp={counts['tp']} fp={counts['fp']} fn={counts['fn']})")

    return {"precision": precision, "recall": recall, "f1": f1}


def rule_based_predict(text: str):
    return _find_weak_spans(text)


def main():
    gold_examples = load_gold()
    print(f"Evaluating against {len(gold_examples)} hand-labeled gold examples.")
    if len(gold_examples) < 20:
        print("NOTE: fewer than 20 gold examples — treat these numbers as directional, "
              "not statistically reliable. Run annotate_gold.py more to get a sturdier set.")

    rule_result = score_system("Rule-based (PhraseMatcher)", rule_based_predict, gold_examples, NEW_LABELS)

    if os.path.exists(MODEL_PATH):
        fine_tuned_nlp = spacy.load(MODEL_PATH)

        def fine_tuned_predict(text):
            doc = fine_tuned_nlp(text)
            return [(e.start_char, e.end_char, e.label_) for e in doc.ents]

        ft_result = score_system("Fine-tuned model", fine_tuned_predict, gold_examples, NEW_LABELS)

        print("\n" + "=" * 50)
        print(f"Summary — F1: rule-based={rule_result['f1']:.3f}  fine-tuned={ft_result['f1']:.3f}")
    else:
        print(f"\nNo fine-tuned model found at {MODEL_PATH} — run train_ner.py first to compare.")


if __name__ == "__main__":
    main()
